# Stage 3 — AI matching (manual, cost-controlled)

The SQLite database is migrated automatically on application startup. Existing jobs and statuses are retained.

## Setup (Windows CMD)

From the repository folder:

```bat
git pull
python -m pip install -r requirements.txt
copy .env.example .env
notepad .env
python -m scripts.assess_jobs --limit 3
python -m uvicorn app.main:app --reload
```

Paste your API key into the local `.env` file, save it, and close Notepad. The application loads this file automatically using python-dotenv. `.env` is gitignored; never commit or share it.

The assessment command sends up to 3 previously unassessed jobs to OpenAI. Each job is assessed once and results are cached in SQLite; no API calls happen when loading the dashboard. Increase `--limit` to at most 10 after verifying cost and output. API charges depend on the selected model and input length. Job descriptions are truncated to 10,000 characters during ingestion.

AI fit scores are opinions, not hiring probabilities. A worldwide feed label does not establish Pakistan eligibility. Check the original employer posting before applying. Applications are never submitted automatically.

## Next

Add more permitted job sources, improve employer eligibility checks, and create a verified editable candidate profile.
