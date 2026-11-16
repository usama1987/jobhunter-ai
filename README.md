# JobHunter AI

Private-first job discovery and application tracker built with FastAPI, SQLite, and Jinja2.

## Run locally

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit http://127.0.0.1:8000

## Tests
`pytest -q`

## Roadmap
- Integrate permitted job feeds and alerts
- Verify salary and geographic eligibility
- Prepare truthful AI-assisted application materials
- Review and submit applications manually

**Privacy:** Keep the repository private before adding personal information. Never commit resumes, contact details, credentials, or the local database. No unauthorized LinkedIn scraping or automated Easy Apply submissions.
