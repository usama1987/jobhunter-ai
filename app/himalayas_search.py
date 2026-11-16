"""Free Himalayas discovery: explicit network fetch, offline review, no database writes."""
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.discovery import TARGET_TERMS

SEARCH_URL = "https://himalayas.app/jobs/api/search"
QUERIES = ("python", "fastapi", "backend", "full stack", "saas", "automation", "shopify")
CACHE = Path("himalayas_cache") / "search_results.json"


def fetch(query, page=1, opener=urlopen):
    """One public read-only API request; never triggers Apify or OpenAI."""
    if query not in QUERIES or not 1 <= page <= 5:
        raise ValueError("Unsupported query or page")
    url = SEARCH_URL + "?" + urlencode({"q": query, "country": "PK", "sort": "recent", "page": page})
    with opener(Request(url, headers={"User-Agent": "JobHunterAI/1.0 (personal research)"}), timeout=20) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
        raise ValueError("Unexpected Himalayas response")
    return payload["jobs"]


def _country_code(value):
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, dict):
        return str(value.get("alpha2") or value.get("code") or value.get("name") or "").strip().lower()
    return ""


def _salary(job):
    """Only compare USD compensation when period is known."""
    if str(job.get("currency") or "").upper() != "USD":
        return None
    amount = job.get("minSalary")
    if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount < 0:
        return None
    period = str(job.get("salaryPeriod") or "annual").lower()
    factor = {"annual": 1 / 12, "monthly": 1, "weekly": 52 / 12,
              "fortnightly": 26 / 12, "hourly": 40 * 52 / 12}.get(period)
    return round(amount * factor) if factor is not None else None


def review(jobs):
    """Conservative triage: advertised country access is not verified employer eligibility."""
    groups = {"priority": [], "verify": [], "excluded": []}
    seen = set()
    for job in jobs:
        if not isinstance(job, dict):
            continue
        title = str(job.get("title") or "")
        company = str(job.get("companyName") or "")
        url = str(job.get("applicationLink") or "")
        guid = str(job.get("guid") or url)
        if not title or not company or not url.startswith("https://") or guid in seen:
            continue
        seen.add(guid)
        if not any(term in title.lower() for term in TARGET_TERMS + ("automation", "shopify", "wordpress", "technical lead")):
            continue
        countries = job.get("locationRestrictions")
        timezones = job.get("timezoneRestrictions")
        if not isinstance(countries, list) or not isinstance(timezones, list):
            coverage, eligibility, bucket = "unknown", "unknown", "verify"
        else:
            codes = {_country_code(c) for c in countries}
            coverage = "worldwide" if not countries and not timezones else "restricted"
            if countries and not codes.intersection({"pk", "pakistan"}):
                eligibility, bucket = "restricted", "excluded"
            elif timezones and not any(str(t).upper().replace(" ", "") in
                                       {"UTC+5", "UTC+05", "UTC+05:00", "+5", "+05:00", "5"} for t in timezones):
                eligibility, bucket = "restricted", "excluded"
            else:
                eligibility, bucket = "advertised_open", "priority"
        salary = _salary(job)
        if salary is not None and salary < 2000:
            bucket = "excluded"
        groups[bucket].append({
            "title": title[:300], "company": company[:300], "url": url[:2000],
            "coverage": coverage, "arrangement": "Remote (platform-listed)",
            "pakistan_eligibility": eligibility, "salary_monthly_usd": salary,
            "source": "Himalayas", "guid": guid[:200],
        })
    return groups


def read_cache(path=CACHE):
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Cache must contain a list")
    return payload


def save_cache(jobs, path=CACHE):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
