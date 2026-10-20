# Checkpoint D — Overall customer-feedback analysis

This directory contains the first descriptive analysis of 311 English reviews in the six-month window. The reporting grain is overall app-level: Google Play and Apple App Store are not split in reported metrics. Platform fields remain in each row for traceability.

## Files

- comment_labels.csv / .json: every input comment plus deterministic rating, text and theme labels.
- overall_benchmark.csv / .json: SC Mobile versus HSBC benchmark metrics.
- monthly_overall_feedback.csv: overall monthly volume, app counts and 1–2-star rates.
- themes_overall.csv: overall keyword theme mentions.
- themes_by_app.csv: SC and HSBC theme comparison.
- top_themes_by_app.csv: compact top-five theme table per app.
- representative_quotes.csv: anonymized low-rated evidence examples with source URLs.
- validation_sample.csv: one newest-first review per app/rating stratum for manual rule validation.
- analysis_summary.json: methods, counts, caveats and artifact hashes.

The main narrative is [checkpoint_D_customer_feedback_analysis.md](../../checkpoint_D_customer_feedback_analysis.md).

## Regenerate

    .\\.venv\\Scripts\\python.exe scripts\\analyze_feedback_overall.py

The script reads only data/merged_2026-10-19/master_english_six_months.json. It does not collect network data and does not modify source or merged files.
