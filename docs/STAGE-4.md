# Stage 4 — Multiple public sources

JobHunter AI now fetches **Remotive** and **Himalayas**. Himalayas offers a public JSON API and requires visible source attribution and the original applicationLink. This integration preserves both. See https://himalayas.app/docs/remote-jobs-api

From Windows CMD in the project directory:

```bat
git pull
python -m pytest -q
python -m scripts.discover_jobs --himalayas-pages 3
python -m uvicorn app.main:app --reload
```

The first source fetches up to 250 Remotive jobs. The second fetches up to 20 Himalayas jobs per page (default 3 pages). Increase pages up to 10 for a larger sample. Discovery does not use OpenAI or incur OpenAI charges.

Conservative filtering: USD salary floors below $2,000/month are excluded when known. Missing salary stays unknown. Explicit country restrictions excluding Pakistan are excluded; missing country restrictions remain unknown. Expired Himalayas listings are not imported, and imported listings with expiry dates are hidden after expiry. A worldwide label is not proof of Pakistan eligibility.

Jobs are deduplicated by application URL, and existing jobs and application statuses are preserved. Jobs with different URLs across providers may still represent the same position; cross-provider deduplication remains future work. An API error is reported for that source and other sources are still attempted. API rates and terms can change. Do not run high-frequency polling.
