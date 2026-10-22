# Hong Kong Banking App Feedback Monitor — V3

Open **report_customer_feedback_v3.html** locally. This standalone English report needs no server, login or network. English and Chinese comments contribute to the same metrics, topics, monthly chart and benchmark comparisons. Original English/Chinese bodies and Apple titles appear together, newest first.

Select **App store** to switch all results between Google Play and Apple App Store. Bank, rating, sentiment, topic and search controls affect the comment browser only. There is no review-language filter. The V1 horizontal monthly feedback chart is restored and includes BOCHK.

Included: **1,682 reviews**, 2026-04-19 through 2026-10-19 inclusive HKT. Latest included observation: 2026-10-19T22:24:46+08:00. There are 25 other window records excluded for uncertain/unsupported language; evidence remains saved.

| Deliverable | Location |
|---|---|
| English management brief | executive_summary.md |
| Offline report | report_customer_feedback_v3.html |
| Workbook | data/reviews_v3.xlsx |
| Combined original reviews, newest first | data/merged/master_bilingual_six_months.csv and .json |
| Reviews with labels | data/analysis/comment_labels.csv and .json |
| Combined metrics, topics and differences | data/analysis/store_benchmarks.*, themes_by_store_bank.*, benchmark_deltas.* |
| Monthly chart data | data/analysis/monthly_feedback_monitoring.csv and .json |
| Exact monthly bank/store data | data/analysis/monthly_by_store_bank.* |
| Store/bank review exports | data/stores/ |
| Source evidence | data/raw/imported/ and data/chinese_collection/ |
| Scope, methods and verification | config.json, methodology.md, data_dictionary.md, checkpoints A–F, validation/, screenshots/, manifest.json |

The workbook has eight sheets: two store review sheets, bank/store metrics, benchmark differences, topics, monthly bank/store figures, monthly feedback monitoring and coverage. Aggregate sheets use one combined population. Row-level language metadata remains for audit only.

V1/V2 are unchanged. The previous V3 delivery is preserved at the ZIP path in revision.json. This correction changes aggregation/presentation; inputs, raw evidence, original comments, labels and the previously read sample remain hash-identical. No new collection was performed.

## Reproduce from saved input

Use the project Python environment (google-play-scraper 1.2.7, langdetect 1.0.9). From the project root:

```powershell
.\.venv\Scripts\python.exe -B v3/scripts/pipeline.py prepare
.\.venv\Scripts\python.exe -B v3/scripts/pipeline.py build
.\.venv\Scripts\python.exe -B v3/scripts/pipeline.py verify
.\.venv\Scripts\python.exe -B v3/scripts/browser_check.py
# Inspect actual new screenshots; update validation/visual_inspection.json.
.\.venv\Scripts\python.exe -B v3/scripts/pipeline.py finalize
```

Source-bound reading judgments remain valid only while sample and fingerprints match. Changed input/selection/rules require actually reading the new sample and updating manual_review.json before build. Visual approval must match the newly built report and actual screenshots. `import` and `collect_chinese.py` reject existing input; future live updates need new capture directories. Offline reproduction does not create a fresh coverage claim. Browser checks require installed Edge.

V3 adapts the app-review-feedback Skill's English/two-app engine with bilingual eligibility/topic rules, three banks and separate stores. Use V3 scripts for this scope; the installed Skill itself has not been upgraded.
