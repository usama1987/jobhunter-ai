"""Explain why feed records were imported, rejected, or already stored."""
from collections import Counter
from urllib.parse import urlsplit, urlunsplit

def canonical_url(url):
    """Remove tracking query and fragment; retain host/path identity."""
    try:
        parts = urlsplit(url)
        if parts.scheme not in ("https", "http") or not parts.netloc:
            return url
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/") or "/", "", ""))
    except ValueError:
        return url

def summarize(raw_jobs, evaluate, connect):
    counts = Counter()
    examples = {}
    with connect() as con:
        for raw in raw_jobs:
            counts["checked"] += 1
            reason, job = evaluate(raw)
            if reason != "eligible":
                counts[reason] += 1
                if len(examples.get(reason, [])) < 3:
                    title = raw.get("title", "") if isinstance(raw, dict) else ""
                    examples.setdefault(reason, []).append(str(title)[:100])
                continue
            # Only the URL is used for existing-job deduplication; no status changes.
            existing = con.execute("SELECT id FROM jobs WHERE url=?", (job["url"],)).fetchone()
            if existing:
                counts["duplicate"] += 1
                continue
            cols = list(job)
            sql = "INSERT OR IGNORE INTO jobs (" + ", ".join(cols) + ") VALUES (" + ", ".join("?" for _ in cols) + ")"
            result = con.execute(sql, tuple(job[c] for c in cols))
            counts["added" if result.rowcount else "duplicate"] += 1
    for key in ("checked", "added", "duplicate", "missing_fields", "unrelated_title",
                "restricted_region", "below_salary_target", "expired"):
        counts.setdefault(key, 0)
    return {"counts": dict(counts), "examples": examples}
