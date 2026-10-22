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
