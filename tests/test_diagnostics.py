import sqlite3
from app.diagnostics import summarize
from app.discovery import evaluate as remotive_evaluate
from app.himalayas import evaluate as himalayas_evaluate

def test_remotive_reasons():
    base = {"title": "Python Developer", "company_name": "Example",
            "url": "https://example.com/job", "description": ""}
    assert remotive_evaluate({**base, "title": "Nurse"})[0] == "unrelated_title"
    assert remotive_evaluate({**base, "candidate_required_location": "USA only"})[0] == "restricted_region"
    assert remotive_evaluate({**base, "salary": "$1,500/month"})[0] == "below_salary_target"
    assert remotive_evaluate(base)[0] == "eligible"

def test_himalayas_reasons():
    base = {"title": "Python Developer", "companyName": "Example",
            "applicationLink": "https://example.com/apply",
            "guid": "https://himalayas.app/jobs/example",
            "locationRestrictions": [], "description": ""}
    assert himalayas_evaluate({**base, "title": "Nurse"})[0] == "unrelated_title"
    assert himalayas_evaluate({**base, "locationRestrictions": ["US"]})[0] == "restricted_region"
    assert himalayas_evaluate({**base, "expiryDate": 1})[0] == "expired"
    assert himalayas_evaluate(base)[0] == "eligible"

def test_diagnostic_counts_and_duplicate(tmp_path):
    db = tmp_path / "test.db"
    def connect():
        con = sqlite3.connect(db)
        con.execute("""CREATE TABLE IF NOT EXISTS jobs
            (id INTEGER PRIMARY KEY, title TEXT, company TEXT, url TEXT UNIQUE,
             description TEXT, salary_monthly INTEGER, remote_region TEXT,
             score INTEGER, source TEXT, source_url TEXT)""")
        return con
    base = {"title": "Python Developer", "company_name": "Example",
            "url": "https://example.com/job", "description": ""}
    result = summarize([base, base, {**base, "title": "Nurse"}], remotive_evaluate, connect)
    assert result["counts"]["added"] == 1
    assert result["counts"]["duplicate"] == 1
    assert result["counts"]["unrelated_title"] == 1
