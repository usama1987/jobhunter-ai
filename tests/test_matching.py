import io
import json
from unittest.mock import patch
import pytest
from app.matching import assess, candidate_profile

class FakeResponse:
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, *args): return self.payload
    def __init__(self, data): self.payload = json.dumps(data).encode()

def fake_opener(req, timeout):
    content = {"score": 82, "verdict": "strong", "summary": "Good skill fit",
               "strengths": ["Python"], "gaps": ["Cloud"], "eligibility": "confirmed",
               "salary_fit": "confirmed"}
    return FakeResponse({"choices": [{"message": {"content": json.dumps(content)}}]})

def test_no_api_key():
    with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
        with pytest.raises(RuntimeError):
            assess({})

def test_unknown_salary_and_worldwide_not_confirmed():
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        result = assess({"title": "Python", "remote_region": "worldwide", "salary_monthly": None}, opener=fake_opener)
    assert result["eligibility"] == "unknown"
    assert result["salary_fit"] == "unknown"
    assert result["score"] == 82

def test_profile_has_salary_target():
    assert candidate_profile()["minimum_monthly_usd"] == 2000
