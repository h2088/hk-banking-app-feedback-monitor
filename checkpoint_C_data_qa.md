# Checkpoint C — Data QA Log

**Checked on:** 2026-10-19  
**Status:** Complete for the 311-row English app-store analysis sample  
**QA input:** [`master_english_six_months.json`](data/merged_2026-10-19/master_english_six_months.json)  
**QA output package:** [`data/checkpoint_C_qa_2026-10-19`](data/checkpoint_C_qa_2026-10-19/)

## QA scope and definitions

This checkpoint checks the current intended analysis file: the English reviews returned for SC Mobile Hong Kong and HSBC HK Mobile Banking on Google Play and the Hong Kong Apple App Store during the six-month window. The window is **2026-04-19 00:00:00 inclusive through 2026-10-20 00:00:00 exclusive, Hong Kong time (UTC+08:00)**.

The source merge remains immutable. QA outputs are derived files. A source record is considered analysis-eligible when its required metadata and text are present, its timestamp and rating are valid, its platform/app identity is one of the four verified mappings, its language status is `english`, its raw evidence file exists, and its platform/app/review key is unique. This is a data-quality decision only; it is not a sentiment or theme label.

## Result summary

| Check | Result | Interpretation |
|---|---:|---|
| Rows checked | **311** | Exact input to the current English six-month analysis |
| Analysis-eligible rows | **311 / 311** | No row was removed by QA |
| Outside date window | **0** | All rows satisfy the Hong Kong boundary |
| Missing required fields | **0** | No missing app, ID, date, rating, text, language, URL, collection time or raw-evidence path |
| Invalid ratings | **0** | All values are integer 1–5 |
| Non-English labels in English sample | **0** | All rows carry the final `english` label |
| Invalid app/platform/ID mapping | **0** | Four expected mappings only |
| Duplicate platform/app/review keys | **0** | No source record was dropped |
| Missing raw response evidence | **0** | Every row points to an existing saved response |
| Newest-first sort violation | **0** | Sorted by numeric source timestamp descending; unique key breaks ties |

The same unique-key check over the full 5,278-row merged table also found **0 duplicate keys**. Input hashes and output checks are recorded in [`qa_summary.json`](data/checkpoint_C_qa_2026-10-19/qa_summary.json).

## Coverage by verified platform and app

| Platform | App | Reviews | Mean rating | Date range (HK) | 1★ | 2★ | 3★ | 4★ | 5★ |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| Apple App Store | HSBC HK Mobile Banking | 121 | 3.1736 | 2026-04-21 – 2026-10-10 | 46 | 7 | 6 | 4 | 58 |
| Apple App Store | SC Mobile Hong Kong | 50 | 2.3200 | 2026-04-22 – 2026-10-12 | 26 | 5 | 4 | 7 | 8 |
| Google Play | HSBC HK Mobile Banking | 92 | 3.4239 | 2026-04-22 – 2026-10-15 | 31 | 2 | 4 | 7 | 48 |
| Google Play | SC Mobile Hong Kong | 48 | 2.1875 | 2026-04-20 – 2026-10-16 | 32 | 2 | 0 | 1 | 13 |
| **Total** | **Both apps / both platforms** | **311** | **2.8537** | **2026-04-20 – 2026-10-16** | **135** | **16** | **14** | **19** | **127** |

The complete machine-readable version is [`coverage_by_app_platform.csv`](data/checkpoint_C_qa_2026-10-19/coverage_by_app_platform.csv). These four source/app strata remain QA evidence, not final-report dimensions. The user's later instructions require overall app-level comparisons without Google/Apple splits. Platform samples are not balanced, especially for Apple HSBC (121) versus Apple SC (50), and the final report must disclose this composition limitation beside its overall comparisons.

## Coverage by month

| Hong Kong month | Reviews | Mean rating | Short-text flags |
|---|---:|---:|---:|
| 2026-04 | 18 | 1.9444 | 2 |
| 2026-05 | 50 | 3.1800 | 20 |
| 2026-06 | 66 | 2.5606 | 20 |
| 2026-07 | 42 | 3.3333 | 17 |
| 2026-08 | 63 | 3.0476 | 18 |
| 2026-09 | 46 | 3.0435 | 18 |
| 2026-10 | 26 | 3.2692 | 10 |
| **Total** | **311** | **2.8537** | **105** |

April and October are partial observed months (the requested window starts on April 19 and the latest observed record is October 16). The month table is therefore a coverage description, not evidence that missing days had zero reviews. The source table is [`coverage_by_month.csv`](data/checkpoint_C_qa_2026-10-19/coverage_by_month.csv).

## Duplicate and text-information checks

Duplicate checks use two different concepts:

1. **Record identity:** `platform:app_id:review_id`. This is the deduplication key. There are zero duplicates in the 311-row analysis sample and zero in the full 5,278-row merge.
2. **Normalized text:** Unicode NFKC, case-folding and whitespace collapsing, used only to flag repeated wording. The 311-row sample has five repeated-text groups covering 20 rows:

| Normalized text | Rows | Treatment |
|---|---:|---|
| `good` | 12 | Retain; distinct review IDs and a generic positive statement |
| `excellent` | 2 | Retain; distinct review IDs |
| `nice` | 2 | Retain; distinct review IDs |
| `easy to use` | 2 | Retain; distinct review IDs |
| `great apps` | 2 | Retain; distinct review IDs |

Repeated wording is not treated as duplicate collection and is not deleted. The QA row-level file stores a normalized-text SHA-256 and group count so later sentiment/theme work can avoid over-interpreting generic text. A deterministic “short text for theme review” flag marks English texts with **four or fewer English words**; it affects no row’s eligibility for volume or rating analysis. There are 105 such flags.

## Required-field, identity and evidence checks

- Every row has app, platform, app key, source app ID, review ID, Hong Kong/UTC timestamp, rating, original text, language status, source URL, collection timestamp and an existing raw-response path.
- Verified mappings are: Google SC `com.scb.breezebanking.hk`; Google HSBC `hk.com.hsbc.hsbchkmobilebanking`; Apple SC `445795688`; Apple HSBC `1164066737`.
- Timestamp consistency was checked against the numeric Unix timestamp and UTC offset. The date flags in the source rows agree with the QA window.
- The original 45 normalized fields are preserved. QA adds only derived flags; it does not rewrite the original text or rating.
- Language labels are inherited from the final source exports, including the documented recent manual corrections (Google 18; Apple 15). No new language detection was run during this QA checkpoint.

## QA artifacts

- [Row-level QA CSV](data/checkpoint_C_qa_2026-10-19/english_six_months_qa.csv) — 311 original rows plus duplicate/text-length/eligibility flags.
- [Row-level QA JSON](data/checkpoint_C_qa_2026-10-19/english_six_months_qa.json) — preserves JSON numbers, booleans, objects and nulls.
- [QA summary and hashes](data/checkpoint_C_qa_2026-10-19/qa_summary.json).
- [Coverage by platform/app](data/checkpoint_C_qa_2026-10-19/coverage_by_app_platform.csv), [month](data/checkpoint_C_qa_2026-10-19/coverage_by_month.csv), [rating](data/checkpoint_C_qa_2026-10-19/coverage_by_rating.csv) and [long platform/month/language/rating table](data/checkpoint_C_qa_2026-10-19/coverage_long_platform_month_language_rating.csv).
- [Reproducible QA script](scripts/checkpoint_C_qa.py).

## Interpretation and handoff

The 311 rows pass Checkpoint C’s data-integrity requirements and are ready for descriptive analysis. The sample is not a balanced panel: collection limits, platform differences, and partial boundary months must appear beside every comparison. The 105 short-text flags and 20 repeated-text rows should not be silently treated as detailed evidence. No sentiment or theme labels have been created here; those belong to Checkpoint D and require a documented method plus a manually reviewed validation sample.

**Checkpoint C decision:** complete. Proceed to **Checkpoint D — Analysis**, keeping source strata and raw evidence in the QA package and row-level files, and keeping app-level denominators and coverage limitations in the report. Final reporting follows the user's later overall-app, no-platform-split scope; see [Checkpoint F](checkpoint_F_final_review.md).
