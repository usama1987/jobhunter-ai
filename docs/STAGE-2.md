# Stage 2 — Job discovery

Run the FastAPI dashboard as described in README.md. To import current vacancies:

```powershell
python -m scripts.discover_jobs
```

This fetches up to 250 software-development listings from Remotive's public API and stores qualifying roles locally. Check the feed provider's current usage terms and rate limits before scheduling repeated requests. No automated schedule is enabled yet.

## Conservative eligibility
- Title must match a target developer role.
- Clearly region-restricted listings are excluded.
- Listings with unknown geography are retained for manual verification.
- Explicit USD salary below $2,000/month is excluded.
- Unknown salary is retained for review.
- Keyword scores are heuristics, **not** AI match probabilities.
- Listings are deduplicated by URL.
- Applications are never submitted automatically.

## Next
Add source provenance, salary verification, better country-eligibility parsing, and an opt-in daily scheduler. Validate with a live feed and integration tests before enabling recurring ingestion.
