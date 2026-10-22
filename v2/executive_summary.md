# Executive brief - V2

Observation window: 19 April to 19 October 2026 inclusive, Hong Kong time. SC and HSBC retain the 19 October V1 capture; BOCHK was captured on 22 October and filtered to the same review dates. A later BOCHK capture cannot reconstruct deleted or edited reviews as they appeared on 19 October. Public endpoints provide a bounded, request-specific sample, not every customer or all historical reviews.

## Google Play

| Bank | English reviews | Sample mean / 5 | 1-2 star reviews | 1-2 star share |
|---|---|---|---|---|
| SC Mobile | 48 | 2.19 | 34 | 70.8% |
| HSBC HK | 92 | 3.42 | 33 | 35.9% |
| BOCHK | 47 | 2.89 | 22 | 46.8% |

SC minus HSBC HK: -1.24 stars; +35.0 percentage points in the low-star share.

SC minus BOCHK: -0.71 stars; +24.0 percentage points in the low-star share.

Most frequent SC topics among low-star records: App stability / performance (15 low-star records; 15 total mentions); Transfers / payments / cards (11 low-star records; 13 total mentions); Login / authentication / access (11 low-star records; 12 total mentions). Topics overlap; they are screening priorities, not confirmed defects.

## Apple App Store

| Bank | English reviews | Sample mean / 5 | 1-2 star reviews | 1-2 star share |
|---|---|---|---|---|
| SC Mobile | 50 | 2.32 | 31 | 62.0% |
| HSBC HK | 121 | 3.17 | 53 | 43.8% |
| BOCHK | 60 | 2.82 | 30 | 50.0% |

SC minus HSBC HK: -0.85 stars; +18.2 percentage points in the low-star share.

SC minus BOCHK: -0.50 stars; +12.0 percentage points in the low-star share.

Most frequent SC topics among low-star records: Login / authentication / access (13 low-star records; 15 total mentions); App stability / performance (11 low-star records; 13 total mentions); Transfers / payments / cards (10 low-star records; 18 total mentions). Topics overlap; they are screening priorities, not confirmed defects.

## Recommended follow-up

Prioritise SC low-star stability, access and navigation examples in the relevant store. Validate the reported journey against support tickets, device/OS details and telemetry before treating it as a confirmed incident. Compare the same journey and store with each benchmark; retain both positive and negative examples. Review the exact comments through the report filters and source links. Small bank/store samples and collection differences limit rankings.

BOCHK Google Play: 600 unique records from three 200-record pages; collection stopped after two pages entirely before the window. Apple: 500 unique records from ten 50-record pages. The page-11 boundary request returned HTTP 400; that failed response and metadata are retained. The ten accepted pages are usable; there is no claim of exhaustive Apple history. Per-group earliest dates and whether the capture reaches before the window are in coverage.csv.
