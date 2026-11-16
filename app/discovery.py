"""Public job-feed ingestion. No LinkedIn scraping or automated applications."""
import json
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen

from app.main import connect, score_job

REMOTIVE_URL = "https://remotive.com/api/remote-jobs?category=software-dev"
TARGET_TERMS = ("python", "fastapi", "backend", "back-end", "back end", "full stack", "full-stack", "fullstack", "software engineer", "software developer", "web developer", "api developer", "saas", "ai engineer", "ai developer", "machine learning engineer")
ALLOWED_REGIONS = ("worldwide", "anywhere", "global", "pakistan")
BLOCKED_REGIONS = ("us only", "usa only", "united states only", "canada only", "europe only", "eu only", "uk only")
MAX_ITEMS = 250


def parse_monthly_usd(salary):
    """Conservative USD parsing. Unknown currency/period returns None."""
    if not salary or not isinstance(salary, str):
        return None
    s = salary.lower().replace(",", "")
    if not ("$" in s or "usd" in s):
        return None
    m = re.search(r"(\d{2,6})(?:\.\d+)?\s*(?:-|–|to)\s*(\d{2,6})", s)
    if m:
        amount = int(m.group(1))
    else:
        m = re.search(r"(?:\$|usd\s*)(\d{2,6})", s)
        if not m:
            return None
        amount = int(m.group(1))
    if re.search(r"(/\s*(?:year|yr)|per\s*(?:year|annum)|annual|yearly|p\.a\.)", s):
        return round(amount / 12)
    if re.search(r"(/\s*(?:month|mo)|per\s*month|monthly)", s):
        return amount
    if re.search(r"(/\s*(?:hour|hr)|per\s*hour|hourly)", s):
        return None
    return None


def classify_region(candidate):
    s = (candidate or "").strip().lower()
    if any(block in s for block in BLOCKED_REGIONS):
        return "restricted"
    if any(region in s for region in ALLOWED_REGIONS):
        return "worldwide" if "pakistan" not in s else "pakistan"
    return "unknown"


def evaluate(job):
    if not isinstance(job, dict):
        return "missing_fields", None
    result = _normalize_with_reason(job)
    return result


def _normalize_with_reason(job):
    title = str(job.get("title") or "").strip()
    company = str(job.get("company_name") or "").strip()
    url = str(job.get("url") or "").strip()
    if not title or not company or not url.startswith("https://"):
        return "missing_fields", None
    if not any(term in title.lower() for term in TARGET_TERMS):
        return "unrelated_title", None
    salary = parse_monthly_usd(job.get("salary"))
    region = classify_region(job.get("candidate_required_location"))
    if region == "restricted":
        return "restricted_region", None
    if salary is not None and salary < 2000:
        return "below_salary_target", None
    description = re.sub(r"<[^>]+>", " ", str(job.get("description") or ""))
    return "eligible", {
        "title": title[:300], "company": company[:300], "url": url[:2000],
        "description": description[:10000], "salary_monthly": salary,
        "remote_region": region,
        "score": score_job(title, description, salary, region),
        "source": "Remotive", "source_url": url[:2000],
    }


def normalize(job):
    return evaluate(job)[1]


def fetch_remotive(opener=urlopen):
    request = Request(REMOTIVE_URL, headers={"User-Agent": "JobHunterAI/0.2 (personal job research)"})
    with opener(request, timeout=20) as response:
        payload = json.load(response)
    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        raise ValueError("Unexpected jobs response")
    return jobs[:MAX_ITEMS]


def ingest(jobs):
    added = 0
    skipped = 0
    with connect() as con:
        for raw in jobs:
            job = normalize(raw) if isinstance(raw, dict) else None
            if job is None:
                skipped += 1
                continue
            result = con.execute(
                """INSERT OR IGNORE INTO jobs
                (title, company, url, description, salary_monthly, remote_region, score, source, source_url)
                VALUES (:title, :company, :url, :description, :salary_monthly, :remote_region, :score, :source, :source_url)""",
                job,
            )
            added += result.rowcount
    return {"added": added, "skipped": skipped, "checked_at": datetime.now(timezone.utc).isoformat()}


def run():
    from app.diagnostics import summarize
    return summarize(fetch_remotive(), evaluate, connect)
