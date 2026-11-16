"""Budget-conscious, manual-only LinkedIn discovery via Apify.

Preview: python -m scripts.discover_linkedin
Paid pilot: python -m scripts.discover_linkedin --run --limit 10 --max-searches 2
"""
import argparse
import json
import os
import re
from pathlib import Path
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from app.linkedin import SEARCH_TERMS, run
from app.main import initialize
from app.diagnostics import summarize
from app.linkedin import evaluate, classify
from app.matching import assess
from app.main import connect

RUN_IDS = ("SDx6ujyjMPFsVVjhc", "qJSc4KLbOwv83jQfB")
CACHE_DIR = Path(__file__).resolve().parents[1] / "apify_cache"


def recover_run(run_id, opener=urlopen):
    """Read an existing run and dataset only; never start an actor."""
    if not re.fullmatch(r"[A-Za-z0-9]{10,40}", run_id):
        raise ValueError("Invalid run ID")
    load_dotenv()
    token = os.getenv("APIFY_API_TOKEN", "").strip()
    if not token:
        raise ValueError("Set APIFY_API_TOKEN in .env")
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "JobHunterAI/0.6"}
    def get_json(url):
        with opener(Request(url, headers=headers), timeout=60) as response:
            return json.load(response)
    run_data = get_json(f"https://api.apify.com/v2/actor-runs/{run_id}")
    details = run_data.get("data", {})
    if details.get("status") != "SUCCEEDED":
        raise ValueError(f"Run {run_id} status is {details.get('status')}; expected SUCCEEDED")
    dataset_id = details.get("defaultDatasetId")
    if not dataset_id or not re.fullmatch(r"[A-Za-z0-9]{10,40}", dataset_id):
        raise ValueError("Run has no valid dataset ID")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{run_id}.json"
    if cache_path.exists():
        items = json.loads(cache_path.read_text(encoding="utf-8"))
        print(f"Using local cache: {cache_path}")
    else:
        items = get_json(f"https://api.apify.com/v2/datasets/{dataset_id}/items?format=json&clean=true")
        if not isinstance(items, list):
            raise ValueError("Dataset response was not a list")
        cache_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Cached {len(items)} jobs at {cache_path}")
    initialize()
    return summarize(items, evaluate, connect)




def review_cache(ai_limit=0):
    """Offline triage of cached listings; optional explicitly bounded AI calls."""
    if not CACHE_DIR.exists():
        raise ValueError("No cached datasets. Recover existing runs first.")
    records = {}
    for path in sorted(CACHE_DIR.glob("*.json")):
        # Only recovered Apify run files are source datasets; the generated
        # review_report.json must never be ingested as jobs on later reviews.
        if not re.fullmatch(r"[A-Za-z0-9]{17}\.json", path.name):
            continue
        items = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                key = item.get("url") or (item.get("title"), item.get("companyName"))
                if key:
                    records[str(key)] = item
    report = []
    ai_used = 0
    for raw in records.values():
        reason, normalized = evaluate(raw)
        entry = {"title": raw.get("title"), "company": raw.get("companyName"),
                 "url": raw.get("url"), "location": raw.get("location"),
                 "workType": raw.get("workType"), "classification": reason, "remote_detail": classify(raw)}
        if normalized:
            entry["remote_region"] = normalized["remote_region"]
        if reason == "unconfirmed_remote" and ai_used < ai_limit:
            # This is a paid OpenAI assessment, never a new Apify run.
            job = {"title": raw.get("title"), "company": raw.get("companyName"),
                   "description": raw.get("description") or "",
                   "salary_monthly": None, "remote_region": "unknown",
                   "url": raw.get("url")}
            try:
                entry["ai_review"] = assess(job)
            except Exception as exc:
                entry["ai_error"] = f"{type(exc).__name__}: {exc}"
                report.append(entry)
                print("AI review stopped:", entry["ai_error"])
                break
            ai_used += 1
        report.append(entry)
    output = CACHE_DIR / "review_report.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print("Unique cached jobs:", len(records))
    print("Classification:", dict(Counter(item["classification"] for item in report)))
    print("OpenAI assessments:", ai_used)
    print("Review report:", output)
    print("Note: Unknown remote or geographic eligibility is NOT confirmed by AI.")


def main():
    parser = argparse.ArgumentParser(description="Preview or manually trigger paid LinkedIn job searches")
    parser.add_argument("--review-cache", action="store_true", help="Review cached jobs offline; no Apify runs")
    parser.add_argument("--ai-limit", type=int, default=0, help="Optional paid OpenAI reviews (0-10), only with --review-cache")
    parser.add_argument("--recover", nargs="+", metavar="RUN_ID", help="Import existing Apify runs; no actor runs started")
    parser.add_argument("--run", action="store_true", help="Enable paid Apify runs after confirmation")
    parser.add_argument("--limit", type=int, default=10, help="Results per keyword (1-100)")
    parser.add_argument("--max-searches", type=int, default=2, help="Number of searches this invocation (1-26)")
    parser.add_argument("--start", type=int, default=0, help="Starting keyword index (0-25)")
    args = parser.parse_args()
    if not 0 <= args.ai_limit <= 10:
        parser.error("--ai-limit must be 0-10")
    if args.review_cache:
        if args.run or args.recover:
            parser.error("--review-cache cannot be combined with --run or --recover")
        if args.ai_limit:
            print(f"This will make up to {args.ai_limit} paid OpenAI API calls, and zero Apify actor runs.")
            if input("Type YES to authorize AI reviews: ") != "YES":
                print("Cancelled")
                return
        review_cache(args.ai_limit)
        return
    if args.ai_limit:
        parser.error("--ai-limit requires --review-cache")
    if args.recover:
        if args.run:
            parser.error("--recover and --run cannot be combined")
        for run_id in args.recover:
            try:
                print(run_id, recover_run(run_id))
            except Exception as exc:
                print(f"Recovery failed for {run_id}: {type(exc).__name__}: {exc}")
                break
        return
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be 1-100")
    if not 1 <= args.max_searches <= len(SEARCH_TERMS):
        parser.error("--max-searches must be 1-26")
    if not 0 <= args.start < len(SEARCH_TERMS) or args.start + args.max_searches > len(SEARCH_TERMS):
        parser.error("Invalid --start / --max-searches range")
    terms = SEARCH_TERMS[args.start:args.start + args.max_searches]
    print("Search plan (each keyword is a separate Apify run):")
    for term in terms:
        print(" -", term)
    print(f"Maximum returned items requested: {args.limit * len(terms)}")
    print("This is NOT a dollar cost cap; Apify may bill per run and/or usage.")
    if not args.run:
        print("Preview only. Add --run to request paid runs.")
        return
    print("Check Apify account spending controls before proceeding.")
    if input(f"Authorize {len(terms)} potentially billable runs? Type YES: ") != "YES":
        print("Cancelled. No paid requests sent.")
        return
    initialize()
    for term in terms:
        try:
            print(term, run(limit=args.limit, keyword=term))
        except Exception as exc:
            print(f"{term} failed: {type(exc).__name__}: {exc}")
            print("Stopping to avoid unexpected repeated charges.")
            break


if __name__ == "__main__":
    main()
