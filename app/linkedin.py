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


def classify(raw):
    """Classify remote evidence separately from Pakistan hiring eligibility."""
    if not isinstance(raw, dict):
        return {"status": "missing_fields", "eligibility": "unknown", "evidence": ""}
    title = str(raw.get("title") or "").strip()
    company = str(raw.get("companyName") or "").strip()
    url = str(raw.get("url") or "").strip()
    if not title or not company or not url.startswith("https://"):
        return {"status": "missing_fields", "eligibility": "unknown", "evidence": ""}
    posted = str(raw.get("postedDate") or "").strip()
    if posted:
        try:
            dt = datetime.fromisoformat(posted.replace(" UTC", "+00:00").replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - dt).days > 30:
                return {"status": "expired", "eligibility": "unknown", "evidence": posted}
        except ValueError:
            pass
    if not any(term in title.lower() for term in TITLE_TERMS):
        return {"status": "unrelated_title", "eligibility": "unknown", "evidence": title}
    description = re.sub(r"<[^>]+>", " ", str(raw.get("description") or "")).lower()
    location = str(raw.get("location") or "").lower()
    # This actor's workType is frequently an INDUSTRY, not a remote-work flag.
    work_type = str(raw.get("workType") or "").lower()
    text = title.lower() + " " + description
    def found(pattern):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        return match.group(0) if match else None
    # Explicit vacancy-specific hybrid/on-site language takes priority over
    # company boilerplate describing other available work arrangements.
    hybrid = found(r"\bhybrid\b|télétravail possible \(hybride\)|hybrid model|\b\d+\s*j\s*de\s*tt\s*/\s*semaine\b")
    onsite = found(r"\b(?:on[- ]site|in[- ]person only|office[- ]based|must relocate|work from office|offline interview|interview offline)\b")
    onsite_interview = found(r"interview (?:at|in) (?:our|the) office|échange dans nos bureaux")
    if "hybrid" in location or "hybrid" in work_type or hybrid:
        return {"status": "hybrid", "eligibility": "restricted", "evidence": hybrid or location}
    if "onsite" in work_type or "on-site" in work_type or onsite or onsite_interview:
        return {"status": "onsite", "eligibility": "restricted", "evidence": onsite or onsite_interview or work_type}
    restricted = found(r"\b(?:united states|usa|uk|canada|europe|eu) only\b|remote(?:ly)? (?:from anywhere )?in [A-Z][a-z]+|must (?:reside|live|be located|be based) in|work authorization required")
    if restricted:
        return {"status": "region_restricted", "eligibility": "restricted", "evidence": restricted}
    remote = found(r"100% remote|fully remote|remote[- ]first|remote (?:work|working|position|role|job)|work remotely|work from home|work from anywhere|anywhere in the world|formato de trabalho:\s*remoto|\btrabalho remoto\b|\bteletrabalho\b|\btélétravail complet\b")
    if not remote and ("remote" in location or "remoto" in location or work_type.strip() == "remote"):
        remote = location or work_type
    if not remote:
        return {"status": "remote_unverified", "eligibility": "unknown", "evidence": ""}
    # Explicit Pakistan inclusion is stronger than a generic 'worldwide' slogan.
    pakistan = found(r"\b(?:hiring|applicants|candidates|work from|based in|located in)\s+(?:from\s+)?pakistan\b|\bpakistan\s+(?:eligible|accepted|welcome)\b")
    anywhere = found(r"100% remote work \(from anywhere\)|remote worldwide|work from anywhere|anywhere in the world")
    eligibility = "pakistan" if pakistan else "unknown"
    coverage = "worldwide" if anywhere or "worldwide" in location else "unknown"
    return {"status": "remote_confirmed", "eligibility": eligibility,
            "coverage": coverage, "evidence": remote, "global_claim": bool(anywhere)}


def evaluate(raw):
    detail = classify(raw)
    status = detail["status"]
    if status != "remote_confirmed":
        reasons = {"hybrid": "not_remote", "onsite": "not_remote",
                   "region_restricted": "restricted_region",
                   "remote_unverified": "unconfirmed_remote"}
        return reasons.get(status, status), None
    title = str(raw["title"]).strip()
    company = str(raw["companyName"]).strip()
    url = str(raw["url"]).strip()
    description = re.sub(r"<[^>]+>", " ", str(raw.get("description") or "")).strip()
    salary = parse_monthly_usd(str(raw.get("salary") or ""))
    if salary is not None and salary < 2000:
        return "below_salary_target", None
    region = detail.get("coverage", "unknown")
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
