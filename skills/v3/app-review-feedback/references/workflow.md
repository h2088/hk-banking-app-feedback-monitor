# A–F workflow: combined bilingual feedback, separate app stores

## A — Scope and identities

Read config and current user requirements. Default primary is SC Mobile; HSBC HK and BOCHK are benchmarks. The delivery language is English. English, Traditional/Simplified Chinese, Cantonese writing and mixed comments contribute to one bank/store result. Never introduce language performance tabs, language filters or comment language badges unless the user explicitly changes the brief.

Verify listing name, publisher, package/Apple ID and HK storefront when collecting. Saved import establishes source traceability, not current endpoint availability. A request locale is neither reviewer language nor location. Initialize a new batch; init alone completes no checkpoint.

## B — Bounded capture or explicit import

Choose collect OR import. Google public oCPfdb RPC requests newest-first, 200 per page, for en, zh-HK and zh-CN separately. Preserve each locale's captures. Stop on exhausted/repeated tokens, no new IDs within that crawl, two pages entirely before the window, or configured limits. all_history removes only the old-page stopping rule.

Apple HK RSS is multilingual. Request mostRecent pages 1–10; try locale JSON, plain JSON and Atom when empty. Save empty pages and continue. If page 10 is nonempty, observe page 11 separately; HTTP 400 there is a recorded boundary, not a failed ten-page crawl. Other failures remain errors. Never claim complete history.

HTTP bodies, request metadata, timestamps and SHA-256 are saved. Timeout 35 seconds, at most three attempts; HTTP 400/401/403/404/429 are not retried. Preserve failed status and partial rows. Retry a failed capture in a new batch. Source failures cannot silently become successful full-scope delivery.

Import accepts normalized JSON with referenced raw evidence. Copy raw/decoded files under content hashes and retain original paths, capture times and input digest. Existing analysis-language decisions are explicitly imported and bound to unchanged fingerprints, not presented as newly read decisions. Prefer all-date/all-language input for auditable selection.

## C — Source-preserving preparation and QA

Deduplicate platform + app ID + review ID; first supplied observation wins. Retain cross-locale observations and changed-source variants. Equal wording with distinct IDs remains separate. Preserve bodies/titles exactly. Select the inclusive HKT window using timestamps, then apply combined English/Chinese eligibility. Empty bodies or uncertain/unsupported languages stay in exclusions. The filename six_months is legacy; config defines the actual window.

Overrides require exact body/title and actual reviewer/date/reason; no global phrase whitelist. Freeze config, sources and merged artifacts with hashes. QA has bank/store capture boundaries and QA-only language counts. Language counts are not a comparison dimension. Source existence is checked now; verify later matches exact raw items.

## D — Combined analysis and actual reading

Read methods.md. Uniform rating sentiment: 1–2 negative, 3 neutral, 4–5 positive; this is a star proxy, not validated text sentiment. Eleven overlapping topics use bilingual patterns. Compare the primary separately to every configured benchmark within each store. Derive calendar buckets from config, including zero and partial months.

Select the latest example in each populated bank × store × eligibility-language × 1/3/5-star stratum for reading coverage only. manual_review.json starts pending. Actually read every selected title/body and record individual source-bound notes, including rule limitations. Do not mark every row plausible with an automated loop. For an exact offline reproduction only, previously recorded actual notes may be reused if sample hash, IDs, fingerprints, ratings and topic labels all match; retain original reviewer/time and source-review file digest, identify reuse explicitly, and never call it a fresh reading or independent human assessment. New/changed samples require actual reading.

## E — English report and verification

Build standalone report_customer_feedback.html, dynamic English summaries, eight-sheet formula-safe workbook and build manifest. App store switches all groups, topics, examples and monthly results. English/Chinese source comments share one newest-first browser, 25 per page. Bank/rating/sentiment/topic/search filters affect comments only.

Keep V1 horizontal blue monthly volume bars, selected-store total volume, each bank's count and low-star share. Scale to the selected store's maximum. Mark partial calendar months; empty rates are N/A. Never substitute fixed historical months, counts or conclusions.

verify independently recomputes counts, means, topic denominators, months and benchmark differences; checks every included raw source item, originals, CSV, workbook and hashes. It does not independently validate topic semantics or current store availability.

browser-test runs an installed Chromium-family browser against temporary report copies. It checks all source comments and pagination, combined filters/Unicode, denominators, signs, bars, empty states, literal markup and no external assets, then saves seven desktop/narrow screenshots. Actually inspect them and write validation/visual_inspection.json bound to the report and screenshot digests. Missing browser access is a concrete unverified step, never a fabricated pass.

## F — Bound delivery

finalize requires source-bound reading, passing static/browser checks and actual screenshot inspection with matching hashes. It writes checkpoint F and manifest.json. Completion covers the stated public-comment reporting scope; it does not imply full historical coverage, independent semantic accuracy, live alerts, root-cause confirmation, production scheduling or business acceptance.

Continue missing phases of unchanged batches. Input/rule/window changes use a new batch. Preserve historical outputs and old Skill releases. A finalized verify is read-only and checks the final file hashes; new browser evidence requires a new audit batch. Display-only revisions may be archived and explicitly rebuilt when authorized, with all affected checks rerun.
