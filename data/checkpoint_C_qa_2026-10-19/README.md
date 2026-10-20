# Checkpoint C QA package

This directory contains derived quality-assurance outputs for the 311-row English six-month analysis sample. The source merge and raw captures are not modified.

- `english_six_months_qa.csv` / `.json`: the 311 input rows plus QA fields.
- `qa_summary.json`: machine-readable checks, coverage, input hashes and artifact hashes.
- `coverage_by_app_platform.csv`: four source/app strata with counts, mean ratings and date ranges.
- `coverage_by_month.csv`: Hong Kong calendar-month coverage; April and October are partial observed months.
- `coverage_by_rating.csv`: rating distribution.
- `coverage_long_platform_month_language_rating.csv`: source/app/month/language/rating counts.

QA fields:

- `is_duplicate`: duplicate `platform:app_id:review_id` key. All 311 values are false.
- `normalized_text_sha256`, `normalized_text_duplicate_count`, `is_normalized_text_duplicate`: repeated wording flags after Unicode normalization, case-folding and whitespace collapsing. These are not deletion rules.
- `word_count`, `is_short_text_for_theme_review`: four-or-fewer English words, retained for volume/rating analysis but flagged for cautious theme interpretation.
- `analysis_eligible`: passes required-field, date, rating, app identity, English label, evidence existence and unique-key checks. All 311 values are true.

Regenerate the package from the immutable merged JSON:

```powershell
.\\.venv\\Scripts\\python.exe scripts\\checkpoint_C_qa.py
```
