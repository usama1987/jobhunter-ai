"""Assess a small batch of jobs; run manually to control API costs."""
import argparse
import json
from app.main import initialize, connect
from app.matching import assess

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--min-heuristic", type=int, default=0)
    args = parser.parse_args()
    if not 1 <= args.limit <= 10:
        parser.error("--limit must be 1-10")
    initialize()
    with connect() as con:
        jobs = [dict(r) for r in con.execute(
            """SELECT * FROM jobs WHERE ai_score IS NULL AND score >= ?
               AND remote_region != 'restricted'
               ORDER BY score DESC, created_at DESC LIMIT ?""",
            (args.min_heuristic, args.limit))]
    print(f"Assessing {len(jobs)} jobs; each assessment makes a paid API call.")
    for job in jobs:
        try:
            result = assess(job)
            with connect() as con:
                con.execute("""UPDATE jobs SET ai_score=?, ai_verdict=?, ai_summary=?,
                    ai_eligibility=?, ai_salary_fit=?, ai_details=?
                    WHERE id=?""", (result["score"], result["verdict"], result["summary"],
                    result["eligibility"], result["salary_fit"], json.dumps(result), job["id"]))
            print(f'{job["company"]}: {result["score"]}/100 ({result["verdict"]})')
        except Exception as exc:
            print(f'Assessment failed for job {job["id"]}: {type(exc).__name__}: {exc}')
            break

if __name__ == "__main__":
    main()
