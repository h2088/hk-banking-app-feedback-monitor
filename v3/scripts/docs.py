"""English documentation for the combined English/Chinese feedback population."""


def pct(value):
    return "N/A" if value is None else f"{100*value:.1f}%"


def write_docs(root, data):
    s = data["summary"]

    def write(name, text):
        (root / name).write_text(text.strip() + "\n", encoding="utf-8")

    table = "| Store | Bank | Reviews | Mean rating | 1–2 star share |\n|---|---|---:|---:|---:|\n"
    for g in data["groups"]:
        table += f"| {g['platform']} | {g['app']} | {g['review_count']} | {g['mean_rating']:.2f} | {pct(g['negative_rate_rating_1_2'])} |\n"
    gaps = [f"- {d['platform']}, SC vs {d['benchmark']}: **{d['low_star_rate_difference_percentage_points']:+.1f} percentage points** in low-star share; {d['mean_rating_difference_sc_minus_benchmark']:+.2f} stars in sample mean." for d in data["deltas"]]
    tops = []
    for store in ("Google Play", "Apple App Store"):
        topics = sorted((t for t in data["themes"] if t["platform"] == store and t["app_key"] == "sc_mobile"), key=lambda t: (-t["theme_negative_count"], -t["theme_mentions"]))[:3]
        tops.append(f"- {store}: " + "; ".join(f"{data['theme_names'][t['theme']]} — {t['theme_mentions']} mentions, {t['theme_negative_count']} low-star" for t in topics) + ".")

    write("executive_summary.md", f"""
# Hong Kong Banking App Feedback Monitor — V3

SC Mobile is compared with HSBC HK and BOCHK using **one combined English/Chinese customer-review sample for each bank within each app store**. Google Play and Apple App Store remain separate. Management reporting is English; original comments are unchanged. The review window is **19 April–19 October 2026 inclusive, Hong Kong time**.

The analysis contains **{s['included_records']:,} reviews**. Review language is an inclusion/quality-control attribute, not a reporting dimension. There is no language selector or language-specific performance comparison.

{table}
SC has a higher low-star share and lower sample mean rating than both benchmarks within each store.

{chr(10).join(gaps)}

SC topics with the most low-star mentions:

{chr(10).join(tops)}

Investigate login/identity and stability journeys first, then transfer/payment journeys, using source comments and separate store results. Confirm candidate issues with release/device information, telemetry and support cases. Topic mentions overlap and include praise; they do not establish defects, causes or complaint rates.

The V1 monthly chart is retained: horizontal blue bars show total captured reviews across three banks in the selected store; adjacent figures show each bank's review count and its own 1–2 star share. April and October are partial months. Volumes reflect saved samples, not all feedback generated that month.

This correction reuses the same 1,682 V3 records and labels. Original SC/HSBC captures are dated 19 October; BOCHK and additional Google Chinese-locale captures are dated 22 October. Apple uses bounded saved HK feeds. Capture timing and endpoint limits prevent a complete historical census. See methodology.md.
""")
    write("README.md", f"""
# Hong Kong Banking App Feedback Monitor — V3

Open **report_customer_feedback_v3.html** locally. This standalone English report needs no server, login or network. English and Chinese comments contribute to the same metrics, topics, monthly chart and benchmark comparisons. Original English/Chinese bodies and Apple titles appear together, newest first.

Select **App store** to switch all results between Google Play and Apple App Store. Bank, rating, sentiment, topic and search controls affect the comment browser only. There is no review-language filter. The V1 horizontal monthly feedback chart is restored and includes BOCHK.

Included: **{s['included_records']:,} reviews**, 2026-04-19 through 2026-10-19 inclusive HKT. Latest included observation: {max(r['review_time_hk'] for r in data['rows'])}. There are {s['window_all_languages'] - s['included_records']} other window records excluded for uncertain/unsupported language; evidence remains saved.

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
.\\.venv\\Scripts\\python.exe -B v3/scripts/pipeline.py prepare
.\\.venv\\Scripts\\python.exe -B v3/scripts/pipeline.py build
.\\.venv\\Scripts\\python.exe -B v3/scripts/pipeline.py verify
.\\.venv\\Scripts\\python.exe -B v3/scripts/browser_check.py
# Inspect actual new screenshots; update validation/visual_inspection.json.
.\\.venv\\Scripts\\python.exe -B v3/scripts/pipeline.py finalize
```

Source-bound reading judgments remain valid only while sample and fingerprints match. Changed input/selection/rules require actually reading the new sample and updating manual_review.json before build. Visual approval must match the newly built report and actual screenshots. `import` and `collect_chinese.py` reject existing input; future live updates need new capture directories. Offline reproduction does not create a fresh coverage claim. Browser checks require installed Edge.

V3 adapts the app-review-feedback Skill's English/two-app engine with bilingual eligibility/topic rules, three banks and separate stores. Use V3 scripts for this scope; the installed Skill itself has not been upgraded.
""")
    write("methodology.md", f"""
# V3 methodology and limits

## Population and sources

Monitor SC Mobile Hong Kong customer comments against HSBC HK and BOCHK. The interval is `[2026-04-19T00:00:00+08:00, 2026-10-20T00:00:00+08:00)`. Include English, Traditional/Simplified Chinese, Cantonese writing and mixed comments in **one population**. Report by bank and store; language is not a reporting dimension. Management prose is English; customer wording is preserved.

V2 supplied 6,378 unique records across dates/languages and raw HTTP evidence. V3 added {s['new_locale_observations']:,} Google Play observations from six zh-HK/zh-CN requests for three banks, newest first, 200/page, at most two concurrent jobs. Stop after two wholly older pages, exhaustion or the bounded page/error policy. These additions are dated 22 October. Apple HK RSS already contains Chinese, so saved feeds are reused. Original SC/HSBC captures are from 19 October; BOCHK from 22 October. BOCHK Apple pages 1–10 returned 500 records; page 11 returned HTTP 400.

Locale is a retrieval parameter, not author language/location proof. Public endpoints are bounded and may omit records. Later captures cannot reconstruct edits/deletions or prove availability on the cutoff date. Saved unique records: {s['unique_fetched_records']:,}; in-window across languages: {s['window_all_languages']:,}. This correction uses saved evidence without new network collection.

## Identity, original text and QA

Identity is platform + app ID + review ID. V2 wins on overlap; new IDs use the first zh-HK observation, then zh-CN. All observations remain saved; differing fingerprints go to capture_variants. This batch has {s['duplicate_observations']} duplicate observations and {s['capture_variant_count']} differing variants. Different IDs with repeated wording remain separate ({s['repeated_text_group_count']} repeated-text groups). Counts are records, not unique customers.

`text` is the original body; Apple `title` remains separate and supplements matching/search. No translation, spelling correction or script conversion is stored. Developer replies are excluded from analysis. HTML omits display names/replies; full evidence may contain them. Historical empty bodies remain excluded evidence. All included titles/bodies/ratings/times are checked against exact raw responses. Sort by descending source timestamp, then stable key. CSV uses UTF-8 BOM; Excel uses typed, formula-safe cells.

## Eligibility metadata

Original language_status is preserved. analysis_language is separate: Han without kana/Hangul is Chinese; at least three distinct Latin words excluding documented acronyms triggers mixed. Repeated Apple-title words do not add English evidence. Non-Han records use prior detector decisions plus 15 exact-body English phrase decisions actually read by the Codex agent. Shared 'ok', emoji, gibberish and uncertain fragments are not forced into English. All 418 V2 English fingerprints match.

This HK-context heuristic can confuse Han-only Japanese; device/version identifiers may trigger mixed; short English inserts can stay Chinese. Kana/Hangul is excluded conservatively. No exclusive Traditional/Simplified identity is inferred. These metadata determine eligibility and audit only: English, Chinese and mixed enter the same denominator, without language-specific performance tables or controls.

## Sentiment and topics

Uniform star sentiment: 1–2 negative, 3 neutral, 4–5 positive. It can disagree with the text. English lexicon fields are supplementary metadata only. Chinese/mixed text polarity is not evaluated by that lexicon and its numeric fields are null. The lexicon does not determine report sentiment or benchmark ranking.

Eleven overlapping topics use English regex and explicit Traditional/Simplified/Cantonese terms in bilingual_rules.py. An NFKC matching copy inserts Han/Latin boundaries so '一直loading' and 'password之後' match without changing originals. Additions cover '彈app', '轉款', login/identity and waiting/loading. Standalone '服務' does not establish support feedback; standalone '功能/增加' does not establish a feature request.

Rules miss context/irony/negation and can overmatch broad security, feature or notification terms. '不應該出現' may trigger a suggestion; 'wait long long time' may miss performance; marketing complaints may remain unclassified. Positive usability mentions are not complaints. Short/unclassified comments remain included ({s['short_text_count']} short; {s['unclassified_count']} unclassified). These labels screen comments, without confirming causes, incidents or severity.

## Combined metrics and monthly chart

Outputs contain six bank/store groups, 66 topic rows, 42 bank/store/month rows and four SC-minus-benchmark comparisons. Mean = stars / reviews; low-star share = 1–2 star reviews / reviews. Topic mention share = hits / bank-store reviews; topic low-star share = low-star hits / topic hits. All denominators include eligible English/Chinese/mixed comments in that store. Stores are never pooled for benchmark metrics.

The V1-style horizontal chart shows seven months for the selected store. Blue bar length is total captured volume across three banks, scaled to that store's busiest observed month. Adjacent figures show each bank's own review count and 1–2 star share with its own monthly denominator. monthly_feedback_monitoring contains 14 rows (two stores × seven months). April starts on the 19th and October ends on the 19th, so both are partial. Empty rates are null/N/A. No observed records does not establish zero feedback. A collapsed table provides exact monthly figures and means.

## Validation and interpretation

The same {s['sample_count']} comments were previously selected across bank, store, eligibility category and available 1/3/5-star levels and actually read by the Codex agent. Individual judgments are source-fingerprint and sample-hash bound. This correction keeps source rows, labels and sample byte-for-byte unchanged, so those judgments still apply. It does not claim a new reading study. The deliberate triage sample is not random or independent human accuracy evaluation.

Static checks independently recompute combined totals, topics, monthly figures and benchmark differences, verify all included raw source values and protect prior evidence. Real-browser checks cover all 1,682 original bodies/titles, newest-first pagination, both stores, filters, chart values/bar scaling, empty states, literal markup, offline behavior and narrow layout. Actual new screenshots must be viewed and signed for this exact HTML hash before finalization.

No population satisfaction, statistical significance, complete coverage, unique-customer counts, causality, verified incidents or losses follow from these samples. Investigate journeys using source evidence, telemetry, release/device data and support cases. Production scheduling, live alerts and validated incident severity are outside this delivery.
""")
    write("data_dictionary.md", """
# V3 data dictionary

| Field / file | Meaning |
|---|---|
| record_key, review_id, app_id, platform | Original source identity; record_key is unique. |
| text, title | Verbatim body and optional Apple title, without translation. |
| rating | Source integer 1–5. |
| review_timestamp_seconds | Unix seconds; descending sort key. |
| review_time_hk, review_time_utc | Same instant with explicit timezone. |
| collected_at_utc | Capture time, distinct from review date. |
| request_language, request_country | Retrieval locale/storefront; not author language/location proof. |
| language_status, language_method | Preserved original detector decision. |
| analysis_language, analysis_language_method | Eligibility/QA metadata, not aggregate grouping. |
| within_six_month_window | HKT half-open review-window decision. |
| source_url | Public review/listing link; Apple usually has no review permalink. |
| raw_response_workspace_path, raw_item_index, raw_entry_index | Saved raw file and exact position, relative to v3/. |
| source_observations | Capture references retained through deduplication. |
| rating_sentiment | Uniform star proxy: negative / neutral / positive. |
| text_sentiment_rule | Supplementary English-only lexicon; Chinese/mixed = not_evaluated_chinese. |
| text_sentiment_evaluated_count | Supplementary lexicon denominator; not report sentiment. |
| themes, theme_labels | Overlapping keyword mentions, including praise. |
| short_text_for_theme_review | At most 4 Latin words and 8 Han characters. |
| review_count, mean_rating | Combined bank/store denominator and mean stars. |
| negative_count_rating_1_2, negative_rate_rating_1_2 | Low-star count and count / combined group reviews. |
| theme_mentions, theme_mention_rate | Topic hits and hits / combined bank-store reviews. |
| theme_negative_count, theme_negative_rate | Low-star topic hits and hits / topic mentions. |
| month_hk, partial_calendar_month | HKT month; April/October are partial. |
| monthly_feedback_monitoring.review_count | Chart bar value: total monthly records across three banks in one store. |
| monthly_feedback_monitoring.<bank>_review_count | Bank's combined monthly review count. |
| monthly_feedback_monitoring.<bank>_low_star_count/rate | Bank's low-star count and count / its monthly reviews. |
| benchmark_deltas | SC minus HSBC/BOCHK in the same store, combined population. |
| data/qa/coverage, qa_summary | Source/inclusion QA; language composition retained for audit only. |
| data/qa/exclusions, capture_variants | Excluded evidence and differing capture fingerprints. |

Aggregate metrics have no language_scope field. CSV/JSON share row order; objects/arrays become JSON strings in CSV/Excel. Faithful CSV may contain formula-looking source comments; Excel is typed and non-executable. Empty means/rates are null in JSON and N/A in the report.
""")
    write("checkpoint_A_source_feasibility.md", """
# Checkpoint A — source feasibility and corrected scope

One combined English/Chinese result, English management delivery, HSBC HK and BOCHK benchmarks, separate app stores and the existing HKT date window. This correction reuses V3 evidence without new collection.

Saved app IDs: SC Google com.scb.breezebanking.hk / Apple 445795688; HSBC hk.com.hsbc.hsbchkmobilebanking / 1164066737; BOCHK com.bochk.app.aos / 1534534188. Prior V3 zh-HK/zh-CN captures cover all three Google apps; saved Apple HK feeds already contain Chinese. Bounded samples support monitoring without proving complete history.
""")
    write("checkpoint_B_data_collection_and_quality.md", f"""
# Checkpoint B — saved collection and quality

V3 imported 6,378 unique V2 records plus raw evidence and added {s['new_locale_observations']:,} observations from six bounded Google locale jobs. Apple snapshots were reused. Raw responses, parameters, timestamps and stop reasons remain saved. No new collection is performed for this correction.

Unique records: {s['unique_fetched_records']:,}; window across languages: {s['window_all_languages']:,}; included combined population: {s['included_records']:,}; uncertain/unsupported window exclusions: {s['window_all_languages'] - s['included_records']}. Duplicate observations: {s['duplicate_observations']}; capture variants: {s['capture_variant_count']}. V1/V2 are protected by 2,020 hashes. Original V3 inputs, raw evidence, rows, labels and sample have a separate revision-preservation record. The old delivery is archived as recorded in revision.json.

{table}
""")
    write("checkpoint_C_data_preparation.md", f"""
# Checkpoint C — combined preparation

Original bodies/titles and metadata are unchanged. Existing eligibility, HKT date filtering, source-ID deduplication and newest-first order retain the same {s['included_records']:,} records. English, Chinese and mixed enter the same bank/store population. Language metadata is audit-only. All 418 V2 English fingerprints match.

Merged/store/row-label exports remain hash-identical. Aggregate outputs are regenerated without language_scope. New monthly_feedback_monitoring CSV/JSON drives the restored V1 chart. Empty historical bodies and unsupported language remain excluded evidence. No translation or source rewriting is performed.
""")
    write("checkpoint_D_feedback_analysis.md", f"""
# Checkpoint D — combined analysis

Uniform star sentiment and eleven bilingual multi-label topic rules are retained. Regenerated outputs contain six bank/store groups, 66 topic rows, 42 bank/store/month rows, 14 chart rows and four benchmark differences. Results are not divided into language views. Empty monthly rates remain null.

The previously read {s['sample_count']}-comment agent sample, individual notes and all row labels remain unchanged and source-bound. This correction validates aggregation/presentation, without claiming independent human accuracy evaluation. Supplementary English lexicon fields do not define report sentiment. See executive_summary.md and methodology.md.
""")
    write("checkpoint_E_report_and_validation.md", """
# Checkpoint E — combined report and validation

The standalone English report has one app-store selector and one combined English/Chinese population. Language controls, language badges and language-specific performance tables are removed. Bank/rating/sentiment/topic/search controls operate on the unified newest-first comment browser.

The V1 horizontal monthly volume chart is restored, adding BOCHK. Each selected-store row shows total volume and three banks' counts/low-star shares, with partial months marked and exact figures available. Workbook aggregates use the same population; its two store review sheets preserve original text.

Static checks independently recompute source-backed numbers and protect prior evidence. Browser checks cover both stores, every included original, monthly values/scaling, filters, literal markup, empty states and narrow layout. No remote assets, display names or developer replies are embedded. Results and actual screenshot inspection must match the delivered HTML hash before Checkpoint F and manifest.json are finalized.
""")
