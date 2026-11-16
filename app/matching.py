"""Optional OpenAI assessment; never invent salary or geographic eligibility."""
import json
import os
from urllib.request import Request, urlopen
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
API_URL = "https://api.openai.com/v1/chat/completions"

def candidate_profile():
    return {
        "target_roles": ["Python Developer", "FastAPI Developer", "Backend Developer", "Full Stack Developer", "SaaS Developer", "AI Application Developer"],
        "skills": ["Python", "FastAPI", "SQLite", "API integration", "SaaS product development", "web development"],
        "python_experience_years": 4,
        "web_development_experience_years": 21,
        "minimum_monthly_usd": 2000,
        "location": "Pakistan",
        "work_preference": "remote",
    }

def assess(job, opener=urlopen):
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Add OPENAI_API_KEY to the .env file in your project root before AI assessment")
    profile = candidate_profile()
    prompt = {
        "candidate": profile,
        "job": {k: job.get(k) for k in ("title", "company", "description", "salary_monthly", "remote_region", "url")},
    }
    instructions = (
        "You evaluate job compatibility using ONLY supplied evidence. "
        "Return JSON with keys score (integer 0-100), verdict (strong|possible|weak), "
        "summary (string), strengths (array of strings), gaps (array of strings), "
        "eligibility (confirmed|unknown|restricted), salary_fit (confirmed|unknown|below_target). "
        "The score is a subjective fit rating, NOT a probability of getting hired. "
        "Unknown region is never confirmed. Worldwide labels are not proof that Pakistan is accepted; "
        "unless the job text explicitly confirms Pakistan eligibility, use unknown. "
        "Unknown salary is never confirmed. Never invent qualifications, eligibility or salary."
    )
    payload = {
        "model": MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": json.dumps(prompt)},
        ],
    }
    req = Request(API_URL, data=json.dumps(payload).encode("utf-8"),
                  headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                  method="POST")
    with opener(req, timeout=35) as response:
        result = json.load(response)
    data = json.loads(result["choices"][0]["message"]["content"])
    score = data.get("score")
    if type(score) is not int or not 0 <= score <= 100:
        raise ValueError("Invalid AI score")
    if data.get("verdict") not in ("strong", "possible", "weak"):
        raise ValueError("Invalid AI verdict")
    if data.get("eligibility") not in ("confirmed", "unknown", "restricted"):
        raise ValueError("Invalid eligibility")
    if data.get("salary_fit") not in ("confirmed", "unknown", "below_target"):
        raise ValueError("Invalid salary fit")
    if job.get("salary_monthly") is None:
        data["salary_fit"] = "unknown"
    elif job["salary_monthly"] < 2000:
        data["salary_fit"] = "below_target"
    if job.get("remote_region") not in ("pakistan",):
        # A worldwide/unknown feed label alone does not prove Pakistan eligibility.
        data["eligibility"] = "unknown" if data["eligibility"] == "confirmed" else data["eligibility"]
    data["strengths"] = [str(x)[:240] for x in data.get("strengths", []) if isinstance(x, str)][:6]
    data["gaps"] = [str(x)[:240] for x in data.get("gaps", []) if isinstance(x, str)][:6]
    data["summary"] = str(data.get("summary", ""))[:1200]
    return data
