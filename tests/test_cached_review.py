import json
from app import main


def test_cached_review_groups(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "BASE", tmp_path)
    cache = tmp_path / "apify_cache"
    cache.mkdir()
    rows = [
        {"title": "Remote Python", "company": "A", "url": "https://example.com/a",
         "remote_detail": {"status": "remote_confirmed", "eligibility": "unknown", "evidence": "remote work"}},
        {"title": "Unknown", "company": "B", "url": "https://example.com/b",
         "remote_detail": {"status": "remote_unverified", "eligibility": "unknown"}},
        {"title": "Old", "company": "C", "url": "https://example.com/c",
         "remote_detail": {"status": "expired", "eligibility": "unknown"}},
    ]
    (cache / "review_report.json").write_text(json.dumps(rows), encoding="utf-8")
    result = main.cached_linkedin_review()
    assert [len(result[k]) for k in ("priority", "verify", "rejected")] == [1, 1, 1]
    assert result["priority"][0]["eligibility"] == "unknown"


def test_cached_review_missing_or_bad_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "BASE", tmp_path)
    assert main.cached_linkedin_review() == {"priority": [], "verify": [], "rejected": []}
    cache = tmp_path / "apify_cache"
    cache.mkdir()
    (cache / "review_report.json").write_text("{invalid", encoding="utf-8")
    assert main.cached_linkedin_review() == {"priority": [], "verify": [], "rejected": []}
