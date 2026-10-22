# V2 handover

Open report_customer_feedback_v2.html locally. Select Google Play or Apple App Store, compare all three banks, then filter comments by bank, rating sentiment, rating, topic or search term. Comments are sorted newest first. Google links include reviewId; Apple generally opens the app review listing, so match the exact title, body, rating and date. Store websites may have changed since capture.

Observation window: 19 April to 19 October 2026 inclusive, Hong Kong time. SC and HSBC retain the 19 October V1 capture; BOCHK was captured on 22 October and filtered to the same review dates. A later BOCHK capture cannot reconstruct deleted or edited reviews as they appeared on 19 October. Public endpoints provide a bounded, request-specific sample, not every customer or all historical reviews.

BOCHK Google Play: 600 unique records from three 200-record pages; collection stopped after two pages entirely before the window. Apple: 500 unique records from ten 50-record pages. The page-11 boundary request returned HTTP 400; that failed response and metadata are retained. The ten accepted pages are usable; there is no claim of exhaustive Apple history. Per-group earliest dates and whether the capture reaches before the window are in coverage.csv.

The report and executive brief are for managers; data/reviews_v2.xlsx has separate review sheets for each store. JSON is authoritative for typed values; CSV is UTF-8 with BOM and preserves exact comments. Prefer the typed XLSX for spreadsheet review of untrusted text. All fetched records, exclusions, per-comment labels, group metrics and source evidence remain available.

No social-media monitoring, automatic alerts, deployment or scheduled job is included. No message or report has been sent to the manager. V1 and its installed Skill remain unchanged.
