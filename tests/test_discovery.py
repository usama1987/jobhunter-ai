from app.discovery import classify_region, normalize, parse_monthly_usd


def test_salary_annual_to_monthly():
    assert parse_monthly_usd("$36,000 - $60,000 per year") == 3000


def test_salary_unknown():
    assert parse_monthly_usd("Competitive") is None
    assert parse_monthly_usd("€50,000/year") is None
    assert parse_monthly_usd("$40/hour") is None


def test_region_conservative():
    assert classify_region("USA only") == "restricted"
    assert classify_region("Worldwide") == "worldwide"
    assert classify_region("Remote") == "unknown"


def test_normalize_relevant_job():
    job = normalize({"title": "Senior Python Backend Developer", "company_name": "Example",
                     "url": "https://example.com/job", "salary": "$48,000 per year",
                     "candidate_required_location": "Worldwide", "description": "FastAPI SaaS"})
    assert job is not None
    assert job["salary_monthly"] == 4000


def test_reject_restricted_and_underpaid():
    base = {"title": "Python Developer", "company_name": "Example",
            "url": "https://example.com/job", "description": ""}
    assert normalize({**base, "candidate_required_location": "USA only"}) is None
    assert normalize({**base, "salary": "$1,500/month"}) is None
