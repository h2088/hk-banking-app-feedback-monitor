# V2 data dictionary

JSON is the authoritative typed representation. CSV files use UTF-8 with BOM, preserve original source strings and serialize nested lists/objects as JSON. Empty cells represent nulls. The typed Excel workbook stores comment strings and IDs as text; it contains no formula cells.

| Field | Meaning |
|---|---|
| platform | Google Play or Apple App Store; the comparison boundary |
| bank, app, app_key | Bank name, configured app name and stable internal key |
| app_id | Google package or Apple numeric app ID, stored as a string |
| review_id | Source review ID, stored as a string |
| record_key | Platform namespace, app ID and review ID; the unique record identifier |
| text | Original customer comment body, without developer replies or translation |
| title | Original Apple review title; null on Google Play |
| rating | Source integer star rating, 1–5 |
| review_time_hk | Source timestamp converted to Hong Kong time, with +08:00 offset |
| review_time_utc | The same instant in UTC |
| review_timestamp_seconds | Unix seconds used for date filtering and sorting |
| source_updated_time | Apple's original updated timestamp, when exposed |
| source_url | Google app listing with reviewId, or Apple app review listing |
| collected_at_utc | Original response capture time; import does not change it |
| snapshot_mode | Reused V1 October 19 snapshot, or new BOCHK October 22 capture |
| detected_language, language_status | Language result and english/non_english/mixed/uncertain inclusion status |
| language_method, language_probabilities | Detector or exact-text review method and detector scores; scores are not calibrated accuracy |
| origin_language_status | Automatic status before a documented BOCHK correction, if corrected |
| within_six_month_window | Whether the source timestamp falls in the agreed inclusive-date window |
| on_or_before_cutoff | Whether the timestamp precedes 20 October 00:00 HKT |
| raw_response_workspace_path | Path relative to the V2 directory, pointing to the actual saved HTTP body |
| raw_items_workspace_path | Optional saved decoded Google RPC evidence |
| raw_item_index, raw_entry_index | Zero-based location within the captured source page |
| origin_raw_response_workspace_path, origin_raw_items_workspace_path | Evidence location in V1 before copying into V2 |
| origin_input_row | Row index in the imported V1 master |
| user_display_name, developer_reply | Optional source metadata retained in full evidence/export; omitted from the report payload |
| review_app_version, thumbs_up, vote_sum, vote_count | Source-specific optional metadata; not equally available on both stores |
| comment_text_for_analysis | Apple title plus body, or Google body, used for rule matching |
| rating_sentiment | negative for 1–2 stars, neutral for 3, positive for 4–5 |
| text_sentiment_rule | Supplemental keyword signal, not the primary sentiment measure |
| themes, theme_labels | Multi-label rule matches and English display labels |
| primary_theme | First matching rule in the configured order; not a severity estimate |
| short_text_for_theme_review | At most four English words in title plus body |

Other imported V1 fields remain as origin metadata. Older source_dataset, source_json_file and raw_response_file values describe the original V1 locations; use the remapped raw_response_workspace_path to locate the portable V2 evidence.

The full input has 6,378 records across all captured dates and languages. The agreed date window contains 865 records across languages. The analysis contains 418 English records. Exclusions retain one deterministic reason per record: outside_date_window takes precedence, otherwise the language status explains exclusion. Distinct review IDs with identical text remain separate.

Metrics are in data/analysis. Store review CSVs contain the three banks together within each store, and six additional CSVs provide individual bank/store slices. Theme-negative counts count low-star review records that mention a theme, not confirmed complaints about that theme. Monthly rows include seven calendar buckets with April and October explicitly marked partial.
