# Checkpoint A - source feasibility

V2 changes the comparison unit from bank-only to bank within store, and adds one benchmark. Observation window: 19 April to 19 October 2026 inclusive, Hong Kong time. SC and HSBC retain the 19 October V1 capture; BOCHK was captured on 22 October and filtered to the same review dates. A later BOCHK capture cannot reconstruct deleted or edited reviews as they appeared on 19 October. Public endpoints provide a bounded, request-specific sample, not every customer or all historical reviews.

BOCHK Google Play: 600 unique records from three 200-record pages; collection stopped after two pages entirely before the window. Apple: 500 unique records from ten 50-record pages. The page-11 boundary request returned HTTP 400; that failed response and metadata are retained. The ten accepted pages are usable; there is no claim of exhaustive Apple history. Per-group earliest dates and whether the capture reaches before the window are in coverage.csv.

Verified retail IDs are recorded in config.json. Identity evidence is under data/bochk_collection/identity and per-store listing responses. The Apple page-11 HTTP error is preserved; it does not invalidate pages 1-10 or prove complete history.
