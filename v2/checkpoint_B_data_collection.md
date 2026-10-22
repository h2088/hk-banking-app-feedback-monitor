# Checkpoint B - data collection

Observation window: 19 April to 19 October 2026 inclusive, Hong Kong time. SC and HSBC retain the 19 October V1 capture; BOCHK was captured on 22 October and filtered to the same review dates. A later BOCHK capture cannot reconstruct deleted or edited reviews as they appeared on 19 October. Public endpoints provide a bounded, request-specific sample, not every customer or all historical reviews.

BOCHK Google Play: 600 unique records from three 200-record pages; collection stopped after two pages entirely before the window. Apple: 500 unique records from ten 50-record pages. The page-11 boundary request returned HTTP 400; that failed response and metadata are retained. The ten accepted pages are usable; there is no claim of exhaustive Apple history. Per-group earliest dates and whether the capture reaches before the window are in coverage.csv.

Saved 6378 all-date/all-language records, including the original 5,278 and 1,100 BOCHK records. Rows are newest first, with record_key as a deterministic tie-breaker. Original HTTP bodies, request parameters, timestamps and hashes are retained. Imported evidence files are copied by content hash with origin paths in an import manifest.
