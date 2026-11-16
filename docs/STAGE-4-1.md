# Stage 4.1 — Discovery diagnostics

Run from Windows CMD:

```bat
git pull
python -m pytest -q
python -m scripts.discover_jobs --himalayas-pages 10
```

The command now reports per-source counts for checked, added, duplicate, missing_fields, unrelated_title, restricted_region, below_salary_target, and expired, plus up to three example titles per rejected category. This lets us see whether the main issue is poor feed coverage, title matching, geography, salary, or duplicates.

The initial title vocabulary has been broadened to include software engineers and web developers. Missing salary and region remain eligible for import but marked unknown; explicit region restrictions excluding Pakistan, known sub-$2,000 salaries, and expired jobs are still excluded. Existing records, AI assessments, and statuses are preserved.

Do not assume a large number of jobs will be found; the feed may contain few relevant listings. Avoid frequent repeated polling. No OpenAI API calls occur during discovery.
