# Checkpoint C - data quality

The original 311 English SC/HSBC IDs and content fingerprints are preserved exactly. V2 contains 418 English in-window records, 107 from BOCHK. Observation window: 19 April to 19 October 2026 inclusive, Hong Kong time. SC and HSBC retain the 19 October V1 capture; BOCHK was captured on 22 October and filtered to the same review dates. A later BOCHK capture cannot reconstruct deleted or edited reviews as they appeared on 19 October. Public endpoints provide a bounded, request-specific sample, not every customer or all historical reviews.

There are 9 repeated-text groups covering 39 records; distinct IDs are retained. There are 116 short analysis texts and 147 records without a keyword theme. These are not silently removed. Exclusions, language decisions and per-store coverage are saved in data/qa.

| Store | Bank | Fetched | In-window all languages | English |
|---|---|---|---|---|
| Google Play | SC Mobile | 1051 | 53 | 48 |
| Google Play | HSBC HK | 3227 | 99 | 92 |
| Google Play | BOCHK | 600 | 56 | 47 |
| Apple App Store | SC Mobile | 500 | 108 | 50 |
| Apple App Store | HSBC HK | 500 | 268 | 121 |
| Apple App Store | BOCHK | 500 | 281 | 60 |
