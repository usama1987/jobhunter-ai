"""Manual-only Apify LinkedIn jobs ingestion. Third-party scraper, not LinkedIn API."""
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from app.diagnostics import summarize
from app.discovery import TARGET_TERMS, parse_monthly_usd
from app.main import connect, score_job

ACTOR = "valig/linkedin-jobs-scraper"
API_ROOT = "https://api.apify.com/v2/acts"
SEARCH_TERMS = (
    "Python Developer", "Python Engineer", "Backend Developer", "Backend Engineer",
    "FastAPI Developer", "API Developer", "REST API Developer", "Full Stack Developer",
    "Full Stack Engineer", "Python Full Stack Developer", "SaaS Developer", "SaaS Engineer",
    "SaaS Backend Developer", "AI Developer", "AI Engineer", "AI Integration Engineer",
    "Automation Developer", "Web Developer", "Web Application Developer", "WordPress Developer",
    "Shopify Developer", "Shopify App Developer", "E-commerce Developer", "Lead Developer",
    "Technical Lead", "Software Architect",
)
DEFAULT_INPUT = {"easyApply": False, "keywords": "Python Developer", "location": "remote", "under10Applicants": False, "limit": 20}
TITLE_TERMS = ("python", "fastapi", "backend", "back-end", "back end", "full stack", "full-stack",
               "fullstack", "software engineer", "software architect", "software developer",
               "api developer", "saas", "ai engineer", "ai developer", "automation developer",
               "web developer", "wordpress", "shopify", "e-commerce", "ecommerce", "technical lead",
               "lead developer", "machine learning engineer")
ONSITE = ("on-site", "onsite", "on site", "in-person", "in person", "office-based",
          "office based", "work from office", "must relocate", "relocation required",
          "not remote", "no remote", "offline interview", "work from an office")
REGIONAL_REMOTE = ("remote from anywhere in", "remotely from anywhere in", "remote within",
                   "remote only within", "must live in", "must be located in", "based in the",
                   "eligible to work in", "authorized to work in")
RESTRICTED = ("united states only", "us only", "usa only", "uk only", "europe only", "eu only", "canada only", "must be based in", "must reside in", "residents only", "work authorization required")
GLOBAL = ("worldwide", "work from anywhere", "anywhere in the world", "globally", "global remote", "remote worldwide")


def evaluate(raw):
    if not isinstance(raw, dict):
        return "missing_fields", None
    title = str(raw.get("title") or "").strip()
    company = str(raw.get("companyName") or "").strip()
    url = str(raw.get("url") or "").strip()
    if not title or not company or not url.startswith("https://"):
        return "missing_fields", None
    if not any(term in title.lower() for term in TITLE_TERMS):
        return "unrelated_title", None
    work_type = str(raw.get("workType") or "").lower().strip()
    location = str(raw.get("location") or "").lower().strip()
    description = str(raw.get("description") or "")
    lower = (location + " " + description).lower()
    # Apify's workType can be an employment type (e.g. "Full-time"), not
    # a workplace arrangement. Do not treat it as proof of on-site work.
    if any(term in work_type for term in ("hybrid", "on-site", "onsite", "on site")) or "hybrid" in location:
        return "not_remote", None
    remote_evidence = (
        "remote" in work_type
        or "remote" in location
        or bool(re.search(r"\bremote (?:work|working|position|role|job)\b", title.lower()))
        or any(term in description.lower() for term in (
            "fully remote", "100% remote", "remote-first", "remote position",
            "remote role", "work remotely", "work from home", "remote work",
            "work from anywhere", "anywhere in the world"))
    )
    if not remote_evidence:
        return "unconfirmed_remote", None
    if any(term in description.lower() for term in ONSITE):
        return "not_remote", None
    if any(term in lower for term in REGIONAL_REMOTE):
        return "restricted_region", None
    if any(term in lower for term in RESTRICTED):
        return "restricted_region", None
    salary = parse_monthly_usd(str(raw.get("salary") or ""))
    if salary is not None and salary < 2000:
        return "below_salary_target", None
    posted = str(raw.get("postedDate") or "").strip()
    if posted:
        try:
            dt = datetime.fromisoformat(posted.replace(" UTC", "+00:00").replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - dt).days > 30:
                return "expired", None
        except ValueError:
            pass
    region = "worldwide" if any(s in location or s in description.lower() for s in GLOBAL) else "unknown"
    description = re.sub(r"<[^>]+>", " ", description).strip()
    return "eligible", {
        "title": title[:300], "company": company[:300], "url": url[:2000],
        "description": description[:10000], "salary_monthly": salary,
        "remote_region": region, "score": score_job(title, description, salary, region),
        "source": "LinkedIn (Apify)", "source_url": url[:2000],
    }


def fetch_jobs(limit=20, keyword="Python Developer", opener=urlopen):
    """Triggers a billable run only when explicitly invoked by the user."""
    if not 1 <= limit <= 100:
        raise ValueError("limit must be 1-100")
    load_dotenv()
    token = os.getenv("APIFY_API_TOKEN", "").strip()
    if not token:
        raise ValueError("Set APIFY_API_TOKEN in your local .env file")
    actor = os.getenv("APIFY_ACTOR_ID", ACTOR).strip().replace("/", "~")
    payload = dict(DEFAULT_INPUT, limit=limit, keywords=keyword)
    url = f"{API_ROOT}/{quote(actor, safe='~')}/run-sync-get-dataset-items"
    request = Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                               "User-Agent": "JobHunterAI/0.5"})
    with opener(request, timeout=180) as response:
        data = json.load(response)
    if not isinstance(data, list):
        raise ValueError("Unexpected Apify dataset response")
    return data


def run(limit=20, jobs=None, keyword="Python Developer"):
    """Use jobs=... for free offline testing; otherwise invokes paid Apify actor."""
    return summarize(fetch_jobs(limit, keyword=keyword) if jobs is None else jobs, evaluate, connect)
