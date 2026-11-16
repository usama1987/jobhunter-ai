from app.himalayas import normalize, eligibility, salary_monthly, fetch_pages

BASE = {"title": "Python Backend Developer", "companyName": "Example",
        "applicationLink": "https://himalayas.app/apply/example",
        "guid": "https://himalayas.app/companies/example/jobs/python",
        "currency": "USD", "minSalary": 48000, "salaryPeriod": "annual",
        "locationRestrictions": ["PK"], "description": "FastAPI", "expiryDate": 4102444800}

def test_salary_periods():
    assert salary_monthly(BASE) == 4000
    assert salary_monthly({**BASE, "minSalary": 3000, "salaryPeriod": "monthly"}) == 3000
    assert salary_monthly({**BASE, "currency": "EUR"}) is None
    assert salary_monthly({**BASE, "salaryPeriod": "hourly"}) is None

def test_eligibility():
    assert eligibility(BASE) == "pakistan"
    assert eligibility({**BASE, "locationRestrictions": ["US"]}) == "restricted"
    assert eligibility({**BASE, "locationRestrictions": []}) == "unknown"

def test_rejections():
    assert normalize(BASE) is not None
    assert normalize({**BASE, "locationRestrictions": ["US"]}) is None
    assert normalize({**BASE, "expiryDate": 1}) is None
    assert normalize({**BASE, "minSalary": 10000}) is None

def test_source_attribution():
    result = normalize(BASE)
    assert result["source"] == "Himalayas"
    assert result["source_url"] == BASE["guid"]
