# Google Play review collection / 评论抓取结果

Cutoff: 2026-10-19 23:59:59.999999, Hong Kong (UTC+08:00).
Requested window: 2026-04-19 through 2026-10-19 inclusive.

Unique fetched records: 4278; English in requested window: 140; English including fetched older page overflow: 3602.

## Files

- `review_browser.html`: offline searchable English review viewer, newest first.
- `english_six_months.csv` / `.json`: English subset in the requested six-month window.
- `english_as_of_2026-10-19.csv` / `.json`: English including any older records returned on boundary pages; this is NOT all-time history.
- `all_languages_fetched.csv` / `.json`: every unique returned record, including non-English, uncertain and boundary overflow.
- `other_languages_or_uncertain.csv` / `.json`: records excluded from the English subset, retained for manual language review.
- Each app's `raw/*.body`: original HTTP response bytes; `.http.json`: request, timestamp, headers, SHA-256.
- `raw/page_*.decoded.json`: decoded RPC payload, preserving every original review array and pagination token.
- `collection_report.json`, `verification.json`: counts, stopping reason, coverage and evidence checks.

## Interpretation / 核查方式

All CSV/JSON exports are sorted by the returned review timestamp, descending. CSV is UTF-8 with BOM for Excel.
Open a source link, select newest reviews, and compare the exact text, public display name, star rating and date. Review-specific links are best effort: Google may show the app page instead of focusing a review.
`hl` selects request language, not verified author language or residence. Both apps use `gl=HK`; English detection is a separate, fallible step.
English selection uses deterministic langdetect (confidence >=0.80), a documented short-English word list, and script checks. Ambiguous and mixed-language records remain in the other/all files.
Recent excluded records were manually reviewed; 18 clear English short-text misclassifications are corrected via scripts/language_overrides.json. Every correction checks the exact app ID and unchanged text. Applied corrections and reasons are saved in manual_language_review.json. Historical labels outside the six-month window remain primarily automatic.
Per-page English counts in crawl_summary.json and language labels in reviews_fetched.jsonl are preliminary automatic labels captured during downloading. Final corrected counts and labels are in collection_report.json and the exported CSV/JSON files.
Text is preserved exactly as returned by Google; this script does not translate, summarize or invent comments. Google's own localization behavior cannot be ruled out from text alone.
Review time is Google's returned review timestamp and may reflect an edited review; original first-post time is not independently established. Developer replies have separate timestamps.
2026-10-19 is an upper bound, not a claimed newest observed review date. Missing dates/months are not assumed to have zero feedback.
This collection records what this public endpoint returned for this locale and sort, not a guarantee of every Google Play review. Listing aggregate rating counts are not collected text-review counts.
The final partial boundary pages are preserved. Default crawling stops after two pages entirely older than the requested window. With --all-history it continues until endpoint exhaustion, a repeated token, an error, or the recorded safety limit. See each crawl's scope and stop_reason.
Raw responses include public display names/avatar URLs returned by Google. No private account data or identity inference is requested.
