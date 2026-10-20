# Checkpoint B — Data Collection Log

**Checked on:** 2026-10-19  
**Status:** Complete for the declared English app-store scope  
**Target window:** 2026-04-19 00:00:00 through 2026-10-20 00:00:00, Hong Kong time (UTC+08:00); the end is exclusive and corresponds to the 2026-10-19 as-of date.

## Scope completed

This checkpoint collected public customer reviews for both named banking apps on both app-store platforms:

| App | Google Play package | Apple App Store ID | Storefront / country | Collection scope |
|---|---|---|---|---|
| SC Mobile Hong Kong | `com.scb.breezebanking.hk` | `445795688` | Google `HK`; Apple Hong Kong `hk` | All records returned by the final crawl, with an English subset derived after collection |
| HSBC HK Mobile Banking | `hk.com.hsbc.hsbchkmobilebanking` | `1164066737` | Google `HK`; Apple Hong Kong `hk` | All records returned by the final crawl, with an English subset derived after collection |

The current analysis scope is **English-language app-store reviews only**. Social-media records and non-English reviews were not silently substituted into this sample. Non-English, mixed-language, and uncertain records remain in the all-language files for a later, separately documented scope.

## Public sources and collection methods

| Platform | Public listing / endpoint | Method used | Final collection boundary |
|---|---|---|---|
| Google Play | [SC Mobile listing](https://play.google.com/store/apps/details?hl=en-US&id=com.scb.breezebanking.hk); [HSBC listing](https://play.google.com/store/apps/details?hl=en&id=hk.com.hsbc.hsbchkmobilebanking) | Public review RPC requests with Hong Kong country parameter and the listing language parameter (`en-US` for SC; `en` for HSBC). Pagination, response bytes, decoded payloads, timestamps and request metadata were saved. | SC: 6 pages to endpoint exhaustion, 1,051 unique records. HSBC: 17 pages to endpoint exhaustion, 3,227 unique records. This is the returned public endpoint sample, not a claim of every review visible to every user/device. |
| Apple App Store RSS | [SC Mobile Hong Kong](https://apps.apple.com/hk/app/sc-mobile-hong-kong/id445795688?l=en-GB); [HSBC HK Mobile Banking](https://apps.apple.com/hk/app/hsbc-hk-mobile-banking/id1164066737?l=en-GB) | Hong Kong public customer-review RSS, pages 1–10, with JSON/XML and language/header variants checked. Each non-empty page was parsed, original response bytes were preserved, and page 11 was tested as an empty-feed boundary. | 500 records per app (10 pages × 50). This public RSS boundary is not complete all-time history. SC reaches 2023-09-12; HSBC reaches 2026-03-14. |

The collectors used public, unauthenticated endpoints. No private account details, login credentials, or identity inference were collected. The scripts and original captures remain in `scripts/`, `data/google_play_2026-10-19/run_03_full_history/`, and `data/apple_2026-10-19/run_03/`.

## Final collection counts

“All fetched” means unique records returned by the final crawl. “English fetched” means the final post-collection language subset, including older records returned on boundary pages. “Six-month all” and “six-month English” use the Hong Kong timestamp window above.

| Platform | App | All fetched | English fetched | Six-month all languages | Six-month English | Latest fetched (HK) | Earliest fetched (HK) |
|---|---|---:|---:|---:|---:|---|---|
| Google Play | SC Mobile Hong Kong | 1,051 | 882 | 53 | 48 | 2026-10-16 09:25:03 | 2013-09-06 20:50:05 |
| Google Play | HSBC HK Mobile Banking | 3,227 | 2,720 | 99 | 92 | 2026-10-15 02:39:51 | 2016-10-26 17:30:49 |
| Apple App Store RSS | SC Mobile Hong Kong | 500 | 261 | 108 | 50 | 2026-10-15 22:48:31 | 2023-09-12 12:58:37 |
| Apple App Store RSS | HSBC HK Mobile Banking | 500 | 208 | 268 | 121 | 2026-10-17 14:33:05 | 2026-03-14 20:07:02 |
| **Total** | **Two apps / two platforms** | **5,278** | **4,071** | **528** | **311** | **2026-10-17 14:33:05** | **2013-09-06 20:50:05** |

The final English six-month analysis sample is therefore **311 reviews**:

- SC Mobile: 48 Google Play + 50 Apple = **98**;
- HSBC HK Mobile Banking: 92 Google Play + 121 Apple = **213**.

## Fields and preservation

Each final row keeps the source app, app ID, review ID, Hong Kong and UTC timestamps, numeric timestamp, rating, original text, public display name where exposed, app version, source URL, collection timestamp, language result and raw-evidence pointers. Apple titles are kept separately; Google has no title and receives no invented title. Google `thumbs_up` and Apple `vote_sum`/`vote_count` remain separate source fields. Apple RSS does not expose developer replies, so its `developer_reply` is null with an explicit `reply_availability` explanation.

The merged master table adds a platform/app key and an unambiguous workspace-relative path to each raw response. It does not rewrite source text, translate comments, alter ratings, or merge identical text across platforms.

## Language handling

Language was determined after downloading the source records, not from the request UI language. The final source exports preserve the detected language, method and probability fields. Recent short-text errors were manually corrected in the final source datasets (18 Google records and 15 Apple records); the correction changes only the derived label, never the comment text. Older labels remain primarily automatic and can be wrong. The English subset should therefore be treated as a documented, reproducible classification sample rather than a platform-provided author-language fact.

## Coverage limitations and decision

- Apple’s public Hong Kong RSS returned 500 records per app and stopped at the tested page-11 empty boundary; it is not a complete historical review database.
- Google collection reached the final endpoint boundary for the requested Hong Kong listing parameters, but the returned sample is not a guarantee of every store review, locale, device view, or hidden ranking state.
- A review timestamp can reflect an edit/update time rather than the first time the review was posted.
- The latest fetched record across all languages is 2026-10-17. The 311-row English six-month analysis sample has a latest record of 2026-10-16. Neither date is 2026-10-19; the as-of date is an upper bound, not a claim that a review was observed on that exact date.
- Social discussion found during Checkpoint A is not combined with app-store records here because no comparable exhaustive social collection method was established.
- Counts are review records, not distinct customers.

## Checkpoint B evidence

- [Merged master workbook](data/merged_2026-10-19/reviews_master.xlsx)
- [311-review English six-month CSV](data/merged_2026-10-19/master_english_six_months.csv)
- [Merged report with input hashes and coverage caveats](data/merged_2026-10-19/merge_report.json)
- [Google final collection report](data/google_play_2026-10-19/run_03_full_history/collection_report.json)
- [Apple final collection report](data/apple_2026-10-19/run_03/collection_report.json)

**Checkpoint B decision:** the declared English app-store collection is complete enough to proceed to Checkpoint C, provided that source coverage, actual sample sizes and the limitations above remain documented. Under the user's later reporting instructions, platform/app strata are retained in the collection and QA evidence only; the final report compares overall SC and HSBC results without platform-split metrics. See [Checkpoint F](checkpoint_F_final_review.md) for final acceptance of that scope.
