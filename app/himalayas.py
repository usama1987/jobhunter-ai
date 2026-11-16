"""Himalayas public remote-jobs feed. Preserve source attribution and application links."""
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from app.discovery import TARGET_TERMS
from app.main import connect, score_job

API = "https://himalayas.app/jobs/api"
PERIODS = {"annual": 1 / 12, "monthly": 1, "weekly": 52 / 12, "fortnightly": 26 / 12}
USER_AGENT = "JobHunterAI/0.4 (personal job discovery)"

def salary_monthly(job):
    if job.get("currency") != "USD":
        return None
    amount = job.get("minSalary")
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
        return None
    period = job.get("salaryPeriod") or "annual"
    factor = PERIODS.get(period)
    return round(amount * factor) if factor else None

def eligibility(job):
    restrictions = job.get("locationRestrictions")
    if isinstance(restrictions, list) and restrictions:
        normalized = {str(x).strip().lower() for x in restrictions}
        if "pk" in normalized or "pakistan" in normalized:
            return "pakistan"
        # Country allowlist excludes Pakistan; don't import.
        return "restricted"
    # No country restrictions is not confirmation of Pakistan eligibility.
    return "unknown"

def normalize(job, now=None):
    if not isinstance(job, dict):
        return None
    title = str(job.get("title") or "").strip()
    company = str(job.get("companyName") or "").strip()
    url = str(job.get("applicationLink") or "").strip()
    guid = str(job.get("guid") or "").strip()
    if not title or not company or not url.startswith("https://") or not guid.startswith("https://himalayas.app/"):
        return None
    if not any(term in title.lower() for term in TARGET_TERMS):
        return None
    region = eligibility(job)
    if region == "restricted":
        return None
    now = now or datetime.now(timezone.utc).timestamp()
    expiry = job.get("expiryDate")
    if isinstance(expiry, (int, float)) and expiry <= now:
        return None
    salary = salary_monthly(job)
    if salary is not None and salary < 2000:
        return None
    description = re.sub(r"<[^>]+>", " ", str(job.get("description") or ""))
    return {"title": title[:300], "company": company[:300], "url": url[:2000],
            "description": description[:10000], "salary_monthly": salary,
            "remote_region": region, "score": score_job(title, description, salary, region),
            "source": "Himalayas", "source_url": guid[:2000],
            "expires_at": datetime.fromtimestamp(expiry, timezone.utc).isoformat() if isinstance(expiry, (int, float)) else None}

def fetch_pages(pages=3, opener=urlopen):
    if not 1 <= pages <= 10:
        raise ValueError("pages must be 1-10")
    cursor = None
    results = []
    for _ in range(pages):
        params = {"limit": 20}
        if cursor:
            params["cursor"] = cursor
        request = Request(API + "?" + urlencode(params), headers={"User-Agent": USER_AGENT})
        with opener(request, timeout=20) as response:
            payload = json.load(response)
        jobs = payload.get("jobs", [])
        if not isinstance(jobs, list):
            raise ValueError("Unexpected Himalayas response")
        results.extend(jobs)
        next_cursor = payload.get("nextCursor")
        if not next_cursor or next_cursor == cursor or not jobs:
            break
        cursor = next_cursor
    return results

def ingest(jobs):
    added = 0
    skipped = 0
    with connect() as con:
        for raw in jobs:
            job = normalize(raw)
            if job is None:
                skipped += 1
                continue
            result = con.execute("""INSERT OR IGNORE INTO jobs
              (title, company, url, description, salary_monthly, remote_region, score, source, source_url, expires_at)
              VALUES (:title, :company, :url, :description, :salary_monthly, :remote_region, :score, :source, :source_url, :expires_at)""", job)
            added += result.rowcount
    return {"added": added, "skipped": skipped, "source": "Himalayas"}

def run(pages=3):
    return ingest(fetch_pages(pages=pages))
