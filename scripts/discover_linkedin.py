"""Budget-conscious, manual-only LinkedIn discovery via Apify.

Preview: python -m scripts.discover_linkedin
Paid pilot: python -m scripts.discover_linkedin --run --limit 10 --max-searches 2
"""
import argparse

from app.linkedin import SEARCH_TERMS, run
from app.main import initialize


def main():
    parser = argparse.ArgumentParser(description="Preview or manually trigger paid LinkedIn job searches")
    parser.add_argument("--run", action="store_true", help="Enable paid Apify runs after confirmation")
    parser.add_argument("--limit", type=int, default=10, help="Results per keyword (1-100)")
    parser.add_argument("--max-searches", type=int, default=2, help="Number of searches this invocation (1-26)")
    parser.add_argument("--start", type=int, default=0, help="Starting keyword index (0-25)")
    args = parser.parse_args()
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
