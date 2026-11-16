from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3

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


@app.get("/")
def dashboard(request: Request):
    with connect() as con:
        jobs = con.execute("SELECT * FROM jobs ORDER BY score DESC, created_at DESC").fetchall()
        counts = {r["status"]: r["n"] for r in con.execute("SELECT status, COUNT(*) n FROM jobs GROUP BY status")}
    return templates.TemplateResponse(request, "index.html", {"jobs": jobs, "counts": counts})


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
        return [dict(r) for r in con.execute("SELECT * FROM jobs ORDER BY score DESC")]
