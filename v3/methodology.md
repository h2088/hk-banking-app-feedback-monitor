# V3 methodology and limits

## Population and sources

Monitor SC Mobile Hong Kong customer comments against HSBC HK and BOCHK. The interval is `[2026-04-19T00:00:00+08:00, 2026-10-20T00:00:00+08:00)`. Include English, Traditional/Simplified Chinese, Cantonese writing and mixed comments in **one population**. Report by bank and store; language is not a reporting dimension. Management prose is English; customer wording is preserved.

V2 supplied 6,378 unique records across dates/languages and raw HTTP evidence. V3 added 3,585 Google Play observations from six zh-HK/zh-CN requests for three banks, newest first, 200/page, at most two concurrent jobs. Stop after two wholly older pages, exhaustion or the bounded page/error policy. These additions are dated 22 October. Apple HK RSS already contains Chinese, so saved feeds are reused. Original SC/HSBC captures are from 19 October; BOCHK from 22 October. BOCHK Apple pages 1–10 returned 500 records; page 11 returned HTTP 400.

Locale is a retrieval parameter, not author language/location proof. Public endpoints are bounded and may omit records. Later captures cannot reconstruct edits/deletions or prove availability on the cutoff date. Saved unique records: 9,963; in-window across languages: 1,707. This correction uses saved evidence without new network collection.

## Identity, original text and QA

Identity is platform + app ID + review ID. V2 wins on overlap; new IDs use the first zh-HK observation, then zh-CN. All observations remain saved; differing fingerprints go to capture_variants. This batch has 0 duplicate observations and 0 differing variants. Different IDs with repeated wording remain separate (49 repeated-text groups). Counts are records, not unique customers.

`text` is the original body; Apple `title` remains separate and supplements matching/search. No translation, spelling correction or script conversion is stored. Developer replies are excluded from analysis. HTML omits display names/replies; full evidence may contain them. Historical empty bodies remain excluded evidence. All included titles/bodies/ratings/times are checked against exact raw responses. Sort by descending source timestamp, then stable key. CSV uses UTF-8 BOM; Excel uses typed, formula-safe cells.

## Eligibility metadata

Original language_status is preserved. analysis_language is separate: Han without kana/Hangul is Chinese; at least three distinct Latin words excluding documented acronyms triggers mixed. Repeated Apple-title words do not add English evidence. Non-Han records use prior detector decisions plus 15 exact-body English phrase decisions actually read by the Codex agent. Shared 'ok', emoji, gibberish and uncertain fragments are not forced into English. All 418 V2 English fingerprints match.

This HK-context heuristic can confuse Han-only Japanese; device/version identifiers may trigger mixed; short English inserts can stay Chinese. Kana/Hangul is excluded conservatively. No exclusive Traditional/Simplified identity is inferred. These metadata determine eligibility and audit only: English, Chinese and mixed enter the same denominator, without language-specific performance tables or controls.

## Sentiment and topics

Uniform star sentiment: 1–2 negative, 3 neutral, 4–5 positive. It can disagree with the text. English lexicon fields are supplementary metadata only. Chinese/mixed text polarity is not evaluated by that lexicon and its numeric fields are null. The lexicon does not determine report sentiment or benchmark ranking.

Eleven overlapping topics use English regex and explicit Traditional/Simplified/Cantonese terms in bilingual_rules.py. An NFKC matching copy inserts Han/Latin boundaries so '一直loading' and 'password之後' match without changing originals. Additions cover '彈app', '轉款', login/identity and waiting/loading. Standalone '服務' does not establish support feedback; standalone '功能/增加' does not establish a feature request.

Rules miss context/irony/negation and can overmatch broad security, feature or notification terms. '不應該出現' may trigger a suggestion; 'wait long long time' may miss performance; marketing complaints may remain unclassified. Positive usability mentions are not complaints. Short/unclassified comments remain included (615 short; 502 unclassified). These labels screen comments, without confirming causes, incidents or severity.

## Combined metrics and monthly chart

Outputs contain six bank/store groups, 66 topic rows, 42 bank/store/month rows and four SC-minus-benchmark comparisons. Mean = stars / reviews; low-star share = 1–2 star reviews / reviews. Topic mention share = hits / bank-store reviews; topic low-star share = low-star hits / topic hits. All denominators include eligible English/Chinese/mixed comments in that store. Stores are never pooled for benchmark metrics.

The V1-style horizontal chart shows seven months for the selected store. Blue bar length is total captured volume across three banks, scaled to that store's busiest observed month. Adjacent figures show each bank's own review count and 1–2 star share with its own monthly denominator. monthly_feedback_monitoring contains 14 rows (two stores × seven months). April starts on the 19th and October ends on the 19th, so both are partial. Empty rates are null/N/A. No observed records does not establish zero feedback. A collapsed table provides exact monthly figures and means.

## Validation and interpretation

The same 47 comments were previously selected across bank, store, eligibility category and available 1/3/5-star levels and actually read by the Codex agent. Individual judgments are source-fingerprint and sample-hash bound. This correction keeps source rows, labels and sample byte-for-byte unchanged, so those judgments still apply. It does not claim a new reading study. The deliberate triage sample is not random or independent human accuracy evaluation.

Static checks independently recompute combined totals, topics, monthly figures and benchmark differences, verify all included raw source values and protect prior evidence. Real-browser checks cover all 1,682 original bodies/titles, newest-first pagination, both stores, filters, chart values/bar scaling, empty states, literal markup, offline behavior and narrow layout. Actual new screenshots must be viewed and signed for this exact HTML hash before finalization.

No population satisfaction, statistical significance, complete coverage, unique-customer counts, causality, verified incidents or losses follow from these samples. Investigate journeys using source evidence, telemetry, release/device data and support cases. Production scheduling, live alerts and validated incident severity are outside this delivery.
