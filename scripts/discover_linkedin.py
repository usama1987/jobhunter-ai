"""Manual paid LinkedIn discovery: python -m scripts.discover_linkedin --limit 100"""
import argparse
from app.main import initialize
from app.linkedin import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger one paid Apify LinkedIn scraper run")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    initialize()
    print("This triggers a billable Apify actor run. Review your Apify spending limits first.")
    answer = input("Run paid LinkedIn discovery now? Type YES: ")
    if answer != "YES":
        print("Cancelled; no paid request sent.")
    else:
        print(run(limit=args.limit))
