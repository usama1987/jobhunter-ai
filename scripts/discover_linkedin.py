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
from app.linkedin import evaluate
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



def main():
    parser = argparse.ArgumentParser(description="Preview or manually trigger paid LinkedIn job searches")
    parser.add_argument("--recover", nargs="+", metavar="RUN_ID", help="Import existing Apify runs; no actor runs started")
    parser.add_argument("--run", action="store_true", help="Enable paid Apify runs after confirmation")
    parser.add_argument("--limit", type=int, default=10, help="Results per keyword (1-100)")
    parser.add_argument("--max-searches", type=int, default=2, help="Number of searches this invocation (1-26)")
    parser.add_argument("--start", type=int, default=0, help="Starting keyword index (0-25)")
    args = parser.parse_args()
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
