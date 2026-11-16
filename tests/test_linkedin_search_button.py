from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from app import main
from app import linkedin


def test_apify_charge_cap_in_request(monkeypatch):
    monkeypatch.setenv("APIFY_API_TOKEN", "dummy")
    seen = {}

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, *args):
            return b"[]"

    def opener(request, timeout):
        seen["url"] = request.full_url
        return Response()

    assert linkedin.fetch_jobs(limit=10, keyword="Python Developer", opener=opener) == []
    params = parse_qs(urlsplit(seen["url"]).query)
    assert params["maxTotalChargeUsd"] == ["0.50"]
    assert params["maxItems"] == ["10"]
    assert params["restartOnError"] == ["false"]


def test_cannot_raise_budget():
    with pytest.raises(ValueError):
        linkedin.fetch_jobs(max_charge_usd=0.51)


def test_search_requires_valid_confirmation(monkeypatch):
    def must_not_run(*args, **kwargs):
        raise AssertionError("Actor must not run")
    monkeypatch.setattr(linkedin, "fetch_jobs", must_not_run)
    with TestClient(main.app) as client:
        response = client.post("/linkedin/run", data={"token": "wrong", "keyword": "Python Developer"}, follow_redirects=False)
        assert response.status_code == 303
        response = client.post("/linkedin/run", data={"token": main.SEARCH_TOKEN, "keyword": "Invalid"}, follow_redirects=False)
        assert response.status_code == 303
