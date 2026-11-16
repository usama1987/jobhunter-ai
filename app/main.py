from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3
import json

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "jobs.db"
templates = Jinja2Templates(directory=str(BASE / "app" / "templates"))
KEYWORDS = ("python", "fastapi", "backend", "full stack", "fullstack", "saas", "ai developer", "api")
STATUSES = ("discovered", "shortlisted", "applied", "interview", "rejected", "offer")


def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def initialize():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, company TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE, description TEXT NOT NULL DEFAULT '',
            salary_monthly INTEGER, remote_region TEXT NOT NULL DEFAULT 'unknown',
            status TEXT NOT NULL DEFAULT 'discovered',
            score INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        existing = {r[1] for r in con.execute("PRAGMA table_info(jobs)")}
        for name, sql_type in (("ai_score", "INTEGER"), ("ai_verdict", "TEXT"),
                               ("ai_summary", "TEXT"), ("ai_eligibility", "TEXT"),
                               ("ai_salary_fit", "TEXT"), ("ai_details", "TEXT"),
                               ("source", "TEXT"), ("source_url", "TEXT"),
                               ("expires_at", "TEXT")):
            if name not in existing:
                con.execute(f"ALTER TABLE jobs ADD COLUMN {name} {sql_type}")


def score_job(title: str, description: str, salary_monthly: int | None, remote_region: str) -> int:
    text = (title + " " + description).lower()
    hits = sum(term in text for term in KEYWORDS)
    score = min(65, hits * 13)
    if salary_monthly is not None and salary_monthly >= 2000:
        score += 20
    if remote_region.lower() in ("worldwide", "global", "pakistan"):
        score += 15
    return min(score, 100)


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize()
    yield


app = FastAPI(title="JobHunter AI", lifespan=lifespan)


def cached_linkedin_review():
    """Read cached classifications without mutating SQLite or running APIs."""
    groups = {"priority": [], "verify": [], "rejected": []}
    path = BASE / "apify_cache" / "review_report.json"
    if not path.is_file():
        return groups
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return groups
    if not isinstance(items, list):
        return groups
    for item in items:
        if not isinstance(item, dict):
            continue
        detail = item.get("remote_detail") or {}
        if not isinstance(detail, dict):
            detail = {}
        status = detail.get("status") or item.get("classification", "remote_unverified")
        status = {"eligible": "remote_confirmed",
                  "unconfirmed_remote": "remote_unverified",
                  "not_remote": "onsite",
                  "restricted_region": "region_restricted"}.get(status, status)
        url = str(item.get("url") or "")
        if not url.startswith("https://"):
            continue
        record = {
            "title": str(item.get("title") or "Untitled")[:300],
            "company": str(item.get("company") or "")[:300],
            "url": url,
            "status": status,
            "eligibility": detail.get("eligibility", "unknown"),
            "evidence": str(detail.get("evidence") or "")[:250],
        }
        bucket = ("priority" if status == "remote_confirmed" else
                  "verify" if status == "remote_unverified" else "rejected")
        groups[bucket].append(record)
    return groups


@app.get("/")
def dashboard(request: Request, region: str = "all", source: str = "all"):
    with connect() as con:
        jobs = con.execute("SELECT * FROM jobs WHERE expires_at IS NULL OR expires_at > strftime('%Y-%m-%dT%H:%M:%S', 'now') ORDER BY score DESC, created_at DESC").fetchall()
        counts = {r["status"]: r["n"] for r in con.execute("SELECT status, COUNT(*) n FROM jobs WHERE expires_at IS NULL OR expires_at > strftime('%Y-%m-%dT%H:%M:%S', 'now') GROUP BY status")}
    if region in ("worldwide", "unknown"):
        jobs = [j for j in jobs if j["remote_region"] == region]
    if source == "linkedin":
        jobs = [j for j in jobs if (j["source"] or "").startswith("LinkedIn")]
    return templates.TemplateResponse(request, "index.html", {"jobs": jobs, "counts": counts, "region": region, "source_filter": source, "linkedin_review": cached_linkedin_review()})


@app.post("/jobs")
def add_job(title: str = Form(...), company: str = Form(...), url: str = Form(...),
            description: str = Form(""), salary_monthly: int | None = Form(None),
            remote_region: str = Form("unknown")):
    if not url.startswith(("https://", "http://")):
        return RedirectResponse("/?error=invalid-url", status_code=303)
    score = score_job(title, description, salary_monthly, remote_region)
    with connect() as con:
        con.execute("""INSERT OR IGNORE INTO jobs
            (title, company, url, description, salary_monthly, remote_region, score)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, company, url, description, salary_monthly, remote_region, score))
    return RedirectResponse("/", status_code=303)


@app.post("/jobs/{job_id}/status")
def update_status(job_id: int, status: str = Form(...)):
    if status not in STATUSES:
        return RedirectResponse("/", status_code=303)
    with connect() as con:
        con.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
    return RedirectResponse("/", status_code=303)


@app.get("/api/jobs")
def list_jobs():
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM jobs WHERE expires_at IS NULL OR expires_at > strftime('%Y-%m-%dT%H:%M:%S', 'now') ORDER BY score DESC")]
