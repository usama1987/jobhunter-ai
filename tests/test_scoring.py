from app.main import score_job

def test_relevant_worldwide_job():
    assert score_job("Python FastAPI Backend Developer", "SaaS APIs", 3000, "worldwide") >= 75

def test_unrelated_restricted_job():
    assert score_job("Accountant", "Bookkeeping", 1000, "restricted") < 75
