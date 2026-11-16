from app.linkedin import evaluate, DEFAULT_INPUT

def sample(**updates):
    job = {"title": "Python Backend Developer", "companyName": "Example",
           "url": "https://www.linkedin.com/jobs/view/123",
           "description": "Python FastAPI APIs", "workType": "Remote",
           "location": "Worldwide", "salary": "$36000/yr"}
    job.update(updates)
    return job

def test_actor_input_contract():
    assert DEFAULT_INPUT == {"easyApply": False, "keywords": "python developer", "location": "remote", "under10Applicants": False, "limit": 100}

def test_worldwide_remote():
    reason, job = evaluate(sample())
    assert reason == "eligible"
    assert job["remote_region"] == "worldwide"
    assert job["salary_monthly"] == 3000

def test_remote_unknown_region():
    reason, job = evaluate(sample(location="Remote", description="Python API"))
    assert reason == "eligible"
    assert job["remote_region"] == "unknown"

def test_reject_hybrid():
    assert evaluate(sample(workType="Hybrid"))[0] == "not_remote"

def test_reject_onsite():
    assert evaluate(sample(workType="On-site"))[0] == "not_remote"

def test_reject_restricted():
    assert evaluate(sample(description="Remote, United States only"))[0] == "restricted_region"

def test_reject_no_remote_evidence():
    assert evaluate(sample(workType="", location="London, UK", description="Python API"))[0] == "unconfirmed_remote"

def test_reject_low_salary():
    assert evaluate(sample(salary="$1200/month"))[0] == "below_salary_target"
