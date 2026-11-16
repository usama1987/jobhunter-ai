from app.linkedin import evaluate, classify, DEFAULT_INPUT, SEARCH_TERMS

def sample(**updates):
    job = {"title": "Python Backend Developer", "companyName": "Example",
           "url": "https://www.linkedin.com/jobs/view/123",
           "description": "Python FastAPI APIs", "workType": "Remote",
           "location": "Worldwide", "salary": "$36000/yr"}
    job.update(updates)
    return job

def test_actor_input_contract():
    assert DEFAULT_INPUT == {"easyApply": False, "keywords": "Python Developer", "location": "remote", "under10Applicants": False, "limit": 20}

def test_worldwide_remote():
    reason, job = evaluate(sample())
    assert reason == "eligible"
    assert job["remote_region"] == "unknown"  # Worldwide claim does not verify Pakistan eligibility
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

def test_all_search_categories_present():
    assert len(SEARCH_TERMS) == 26
    assert {"FastAPI Developer", "Shopify Developer", "WordPress Developer",
            "AI Engineer", "Software Architect"} <= set(SEARCH_TERMS)

def test_description_rejects_onsite_even_when_remote_tagged():
    assert evaluate(sample(description="Interview offline. Job Location: Indore (Onsite)"))[0] == "not_remote"

def test_description_rejects_in_person_only():
    assert evaluate(sample(description="In-person only. Must relocate."))[0] == "not_remote"

def test_description_rejects_region_limited_remote():
    assert evaluate(sample(description="You can work remotely from anywhere in Bulgaria."))[0] == "restricted_region"

def test_shopify_title_supported():
    assert evaluate(sample(title="Shopify Developer"))[0] == "eligible"

def test_full_time_is_not_onsite():
    assert evaluate(sample(workType="Full-time", location="Remote"))[0] == "eligible"

def test_remote_in_title_with_full_time_employment():
    assert evaluate(sample(title="Software Engineer (Django) - Remote Work", workType="Full-time", location="Brazil"))[0] == "eligible"

def test_full_time_without_remote_evidence_is_unconfirmed():
    assert evaluate(sample(workType="Full-time", location="Paris, France", description="Build APIs"))[0] == "unconfirmed_remote"

def test_full_time_onsite_description_rejected():
    assert evaluate(sample(workType="Full-time", location="Remote", description="This is an on-site role"))[0] == "not_remote"

def test_expired_checked_before_remote():
    assert classify(sample(postedDate="2025-01-01T00:00:00.000Z", location="Paris", workType="Software Development"))["status"] == "expired"

def test_portuguese_remote():
    assert classify(sample(location="São Paulo", workType="IT Services and IT Consulting", description="Formato de trabalho: Remoto."))["status"] == "remote_confirmed"

def test_french_hybrid():
    assert classify(sample(location="Rennes", workType="IT Services and IT Consulting", description="Télétravail possible (hybride)"))["status"] == "hybrid"

def test_hybrid_overrides_generic_remote_company_text():
    assert classify(sample(location="Lisbon", description="Type of position: Hybrid model in Lisbon. We also have Full Remote projects."))["status"] == "hybrid"

def test_global_company_claim_not_pakistan_eligibility():
    detail = classify(sample(location="Brazil", workType="IT Services and IT Consulting", description="We work remotely worldwide. 100% remote work (from anywhere)."))
    assert detail["status"] == "remote_confirmed"
    assert detail["eligibility"] == "unknown"
    assert evaluate(sample(location="Brazil", description="100% remote work (from anywhere)."))[1]["remote_region"] == "unknown"

def test_pakistan_explicit():
    assert classify(sample(description="Remote position. Hiring candidates from Pakistan."))["eligibility"] == "pakistan"
