import json

from app.himalayas_search import review, _salary, read_cache, save_cache


def job(**overrides):
    result = {"guid": "1", "title": "Python Backend Developer", "companyName": "Example",
              "applicationLink": "https://himalayas.app/jobs/example",
              "locationRestrictions": [], "timezoneRestrictions": [],
              "currency": "USD", "minSalary": 36000, "salaryPeriod": "annual"}
    result.update(overrides)
    return result


def test_worldwide_is_distinct_from_employer_confirmation():
    groups = review([job()])
    assert len(groups["priority"]) == 1
    item = groups["priority"][0]
    assert item["coverage"] == "worldwide"
    assert item["pakistan_eligibility"] == "advertised_open"
    assert item["salary_monthly_usd"] == 3000


def test_country_restriction_excludes_pakistan():
    assert len(review([job(locationRestrictions=[{"alpha2": "US"}])])["excluded"]) == 1


def test_pakistan_country_restriction_is_candidate():
    item = review([job(locationRestrictions=[{"alpha2": "PK"}])])["priority"][0]
    assert item["coverage"] == "restricted"
    assert item["pakistan_eligibility"] == "advertised_open"


def test_missing_restriction_data_needs_verification():
    assert len(review([job(locationRestrictions=None)])["verify"]) == 1


def test_salary_under_target_and_unknown_currency():
    assert len(review([job(minSalary=12000)])["excluded"]) == 1
    assert _salary(job(currency="EUR")) is None


def test_deduplicate_and_cache(tmp_path):
    assert len(review([job(), job()])["priority"]) == 1
    path = tmp_path / "cache.json"
    save_cache([job()], path)
    assert read_cache(path) == [job()]
