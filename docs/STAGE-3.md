# Stage 3 — AI matching (manual, cost-controlled)

The SQLite database is migrated automatically on application startup. Existing jobs and statuses are retained.

## Setup (Windows CMD)

From the repository folder:

```bat
git pull
python -m pip install -r requirements.txt
set OPENAI_API_KEY=YOUR_KEY_HERE
python -m scripts.assess_jobs --limit 3
python -m uvicorn app.main:app --reload
```

Prefer storing your key in a secure local environment rather than command history. `.env` is ignored, but this version does **not** automatically load it.

The assessment command sends up to 3 previously unassessed jobs to OpenAI. Each job is assessed once and results are cached in SQLite; no API calls happen when loading the dashboard. Increase `--limit` to at most 10 after verifying cost and output. API charges depend on the selected model and input length. Job descriptions are truncated to 10,000 characters during ingestion.

AI fit scores are opinions, not hiring probabilities. A worldwide feed label does not establish Pakistan eligibility. Check the original employer posting before applying. Applications are never submitted automatically.

## Next

Add more permitted job sources, improve employer eligibility checks, and create a verified editable candidate profile.
