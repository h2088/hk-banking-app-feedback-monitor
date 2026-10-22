# Analysis methods and limits

## Source fields and identity

`text` is the verbatim customer body; Apple `title` stays separate and supplements matching/search. Preserve ID, stars, wording, source date, capture date, source URL and raw position. Developer replies do not enter customer feedback. HTML omits usernames/replies; full raw exports may contain them. UTF-8 BOM CSV preserves text; typed Excel stores formula-looking comments as text. An empty body stays in source evidence and is excluded from analysis.

`record_key` is `google_play:<package>:<review_id>` or `apple:<numeric_app_id>:<review_id>`. Repeated keys count once; the first supplied observation wins. Live jobs supply English then zh-HK then zh-CN for each bank; imports preserve supplied observation order. All observations remain in source_records.json and raw files. Different title/body/rating/time fingerprints are exported to capture_variants; the selected row records source references. Different IDs with repeated wording remain separate, so counts are review records, not unique customers.

Source columns include platform, app_key/app_id, review_id, record_key, text/title, integer rating 1–5, review_timestamp_seconds, explicit-offset review_time_hk/utc, collected_at_utc, source_url, raw_response_workspace_path and raw_item_index/raw_entry_index. Google decoded-file references may also be present. Imported evidence is copied with content hashes; source timestamps are never replaced by import time. Raw body/title/stars/time for every included row are independently parsed and compared during verify.

## Eligibility and dates

Use Hong Kong `[since 00:00, as_of next-day 00:00)`. Sort by descending Unix seconds, then stable record key. Cutoff and capture dates differ; the cutoff does not assert a review exists that day. Dynamic monthly buckets include empty months. A month is partial only when its calendar interval extends outside the requested review window.

Original language_status/method are retained. A separate analysis_language determines English/Chinese/mixed/excluded eligibility, without becoming a report grouping. Han without kana/Hangul is routed as Chinese; at least three distinct Latin words excluding documented acronyms yields mixed. This HK-context heuristic can confuse Han-only Japanese and device/version strings, and short English inserts may stay Chinese. No exclusive Traditional/Simplified identity is inferred. Kana/Hangul and uncertain fragments are excluded conservatively. Non-Han records use the saved English decision or a reviewed exact-source override. Retrieval locale is not author language/location proof.

An imported analysis_language with a documented analysis_language_method is retained as an explicitly imported decision, bound to source fingerprint and input hash. It is not a fresh reading judgment. Any new correction belongs in config.language_overrides before prepare:

```json
{
  "record_key": "apple:445795688:EXAMPLE",
  "expected_title": "Exact original title or null",
  "expected_text": "Exact original body",
  "language": "english",
  "reason": "Actual reading rationale",
  "reviewer": "Codex agent or actual reviewer",
  "reviewed_at": "Actual ISO date/time"
}
```

Allowed language values: english/chinese/mixed/excluded. Unknown IDs, changed body/title, duplicate overrides and missing provenance fail. Historical short phrases are not global language overrides. Empty bodies remain excluded even with an imported/override decision.

## Sentiment and topics

The common report sentiment proxy is 1–2 stars negative, 3 neutral, 4–5 positive. Stars can disagree with body meaning. Supplementary English lexicon fields are kept in English row exports only; Chinese/mixed polarity is marked not evaluated with null numeric fields. Aggregate sentiment metrics do not use the English lexicon.

Eleven overlapping banking topics use English regex (including V2 identity-verification and suggestion additions) plus Traditional/Simplified/Cantonese terms in bilingual_rules.py. Matching uses an NFKC copy and Han/Latin boundaries; originals are unchanged. Topics cover stability/performance, login/authentication/access, transfers/payments/cards, usability/design, support, account/registration, balances/statements, security/trust, language/localization, fees/rates, and suggestions. A review may match several; primary_theme is the first matched rule, not verified severity.

Rules can overmatch broad security/notification/suggestion terms, miss unusual wording, and fail on irony/negation/ownership. A positive mention is not a complaint. Standalone Chinese '服務' does not establish support feedback; '功能/增加' alone does not establish a request. Short/unclassified comments stay included. The short-analysis flag means at most four Latin words and eight Han characters. There is no independent semantic accuracy estimate.

## Combined denominators and monthly chart

All eligible English/Chinese/mixed comments form one population per bank/store. No language filter, performance split or language badge is provided. Google Play and Apple App Store have separate denominators. One primary bank is compared with each configured benchmark within the same store; difference is primary minus benchmark, in stars or percentage points. Empty means/rates are null and display N/A. The historical mean_rating_difference_sc_minus_benchmark column name is retained for compatibility; it means configured primary minus benchmark even if renamed.

Mean rating = star sum / review count. Low-star share = 1–2 star count / bank-store reviews. Topic mention share = hits / bank-store reviews; topic low-star share = low-star hits / topic hits. Overlapping topic shares need not sum to 100%.

Retain the V1 horizontal blue monthly volume chart. Bar value = total captured reviews across configured banks in the selected store; bar scaling uses that store's largest observed month. Adjacent figures show each bank's review count and its own monthly low-star share. Empty bank-month rates show N/A; all-zero volumes have zero-width bars. Partial months are marked; exact monthly tables also retain means. Observed volume does not establish all feedback generated that month or complete endpoint coverage.

## Reading and presentation checks

Select the newest available 1/3/5-star record for each bank × store × eligibility category (English/Chinese/mixed). This deliberate triage sample is not random. Actually read every selected title/body and labels, and fill individual manual_review.json judgments and notes. Agent reading is not independent human labeling. Build is blocked while judgments are pending; fingerprints/sample hashes prevent applying them to changed text.

Verification independently recomputes combined metrics/topics/months/deltas and matches original sources/CSV/Excel. Browser tests cover every included original, all pagination, both stores, filters, chart counts/scaling, zero denominators, literal untrusted markup, offline resources and narrow layout. Actually view screenshots and sign the exact HTML/screenshot hashes before finalize. Code validates bindings; it cannot prove reading or human acceptance.

These are bounded public samples. Do not infer total customers, population satisfaction, statistical significance, causes, verified defects, losses or complete six-month coverage. Investigate recurring journeys using raw comments, support cases, release/device information and telemetry. Live alerts, social-media monitoring, per-topic monthly trends and incident-severity validation are outside this engine.
