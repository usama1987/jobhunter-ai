"""Manual free job discovery. Never writes to jobs.db or invokes paid APIs."""
import argparse
from app.himalayas_search import QUERIES, fetch, read_cache, review, save_cache


def main():
    parser = argparse.ArgumentParser(description="Himalayas job discovery (free API, manual only)")
    parser.add_argument("--fetch", action="store_true", help="Explicitly request public API and cache results")
    parser.add_argument("--query", choices=QUERIES, default="python")
    parser.add_argument("--pages", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.pages <= 5:
        parser.error("--pages must be 1-5")
    if args.fetch:
        jobs = []
        for page in range(1, args.pages + 1):
            batch = fetch(args.query, page)
            jobs.extend(batch)
            if not batch:
                break
        save_cache(jobs)
        print(f"Fetched {len(jobs)} jobs from public Himalayas API; cached locally.")
    else:
        jobs = read_cache()
        print("Offline review: no network calls.")
    groups = review(jobs)
    print(f"Reviewed {len(jobs)} cached entries.")
    print("Classification:", {key: len(value) for key, value in groups.items()})
    for job in groups["priority"][:20]:
        print(f"  {job['title']} | {job['company']} | {job['coverage']} | Pakistan: {job['pakistan_eligibility']}")
        print(f"  {job['url']}")
    print("No jobs imported, no applications submitted, no paid APIs used.")
    print("Source: Himalayas (https://himalayas.app). Verify eligibility with employer.")


if __name__ == "__main__":
    main()
