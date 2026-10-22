# Commands and direct invocation

Python 3.10+. Offline analysis, exports and verification use the standard library. Fresh collection requires assets/requirements-collection.txt; browser checks require installed Edge/Chrome/Chromium. No API key or LLM API is needed. The executing agent supplies actual comment reading and screenshot inspection.

Use task-specific paths. The example below preserves the current project window. For a future refresh omit --since/--as-of to use current HK date minus six calendar months, or set both explicitly. Custom apps: init --apps <apps.json>, one primary and one to five benchmarks; identifiers must be strings. Schema 2 requires HK, combined English/Chinese, separate stores and Google locales en/zh-HK/zh-CN.

~~~powershell
$reviewSkill = 'C:\Users\1\.codex\skills\app-review-feedback'
$reviewPython = 'D:\7-HK Banking App Feedback Monitor\.venv\Scripts\python.exe'
$reviewBatch = 'D:\7-HK Banking App Feedback Monitor\runs\feedback_new_batch'
& $reviewPython -B "$reviewSkill\scripts\run_feedback.py" init --root $reviewBatch --since 2026-04-19 --as-of 2026-10-19
~~~

Choose fresh collection or saved import; never both for the same batch. Install pinned dependencies only if missing. Do not bypass environment network/write/browser permissions.

~~~powershell
& $reviewPython -B "$reviewSkill\scripts\run_feedback.py" collect --root $reviewBatch
~~~

For offline reproduction instead:

~~~powershell
& $reviewPython -B "$reviewSkill\scripts\run_feedback.py" import --root $reviewBatch --input 'D:\7-HK Banking App Feedback Monitor\v3\data\merged\master_all_reviews.json' --evidence-root 'D:\7-HK Banking App Feedback Monitor\v3' --coverage-note 'Saved public snapshots with original capture dates; this run performs no new live collection.'
~~~

Input is a normalized JSON array, not arbitrary CSV. evidence-root resolves all referenced relative raw paths. Prefer all-date/all-language records. Existing source-bound language decisions can be imported explicitly. Edit exact language overrides before prepare; after prepare config is frozen.

~~~powershell
& $reviewPython -B "$reviewSkill\scripts\run_feedback.py" prepare --root $reviewBatch
& $reviewPython -B "$reviewSkill\scripts\run_feedback.py" qa --root $reviewBatch
& $reviewPython -B "$reviewSkill\scripts\run_feedback.py" analyze --root $reviewBatch
Get-Content -Raw -Encoding UTF8 "$reviewBatch\data\analysis\validation_sample.json"
~~~

Read the full sample and fill manual_review.json. Preserve its sample_sha256, IDs and fingerprints. Each judgement needs rating_assessment (plausible or disagreement_noted), theme_assessment (plausible, insufficient_text or limitation_noted), and concrete notes. Set status=reviewed, reviewer and reviewed_at only after actual review. Exact replay may reuse original documented notes only under workflow.md's hash/label constraints, with explicit provenance.

~~~powershell
& $reviewPython -B "$reviewSkill\scripts\run_feedback.py" review-status --root $reviewBatch
& $reviewPython -B "$reviewSkill\scripts\run_feedback.py" build --root $reviewBatch
& $reviewPython -B "$reviewSkill\scripts\run_feedback.py" verify --root $reviewBatch
& $reviewPython -B "$reviewSkill\scripts\run_feedback.py" browser-test --root $reviewBatch
~~~

Specify --browser <executable> if required. Inspect validation/browser_results.json and actually open all seven screenshots. Then create validation/visual_inspection.json:

~~~json
{
  "status": "reviewed",
  "reviewer": "Executing agent or actual reviewer",
  "reviewed_at_utc": "ACTUAL_ISO_UTC_TIME",
  "report_sha256": "EXACT_REPORT_DIGEST",
  "screenshots": {"screenshots/ACTUAL_FILE.png": "EXACT_FILE_DIGEST"},
  "judgments": ["Actual observations about the inspected layouts, chart and combined comment browser"]
}
~~~

screenshots must contain every path/digest from browser_results, not just the illustrative single entry above. A generated screenshot or passing layout assertion does not establish actual inspection.

~~~powershell
& $reviewPython -B "$reviewSkill\scripts\run_feedback.py" finalize --root $reviewBatch
~~~

Entry report_customer_feedback.html; workbook data/reviews_master.xlsx; combined originals data/merged/master_bilingual_six_months.*; labels/tables data/analysis/; sources data/raw/; English plan/checkpoints/methods/summary/handover at batch root; checks validation/; screenshot files screenshots/; final integrity manifest manifest.json.

Example user invocation:

> 使用 $app-review-feedback，采集 SC Mobile、HSBC HK、BOCHK 的香港中英文评论，SC 为主要对象，另外两家作为 benchmark。输出英文报告，Google Play 和 Apple 分开展示，中英文评论合并分析，保留 V1 横向蓝色月度反馈监测图。日期为 2026-04-19 至 2026-10-19，保存到新的批次目录。

> 使用 $app-review-feedback，基于已存 V3 快照离线复跑，不重新联网；核对指标与原文，保存到新目录。

A Skill is an agent-executed workflow, not a scheduled Windows service. If a session still shows an old catalog description, reopen the session or explicitly read this installed SKILL.md. Do not overwrite historical results or publish them without authorization.
