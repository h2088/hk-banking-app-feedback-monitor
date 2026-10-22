# Methodology and limits

Observation window: 19 April to 19 October 2026 inclusive, Hong Kong time. SC and HSBC retain the 19 October V1 capture; BOCHK was captured on 22 October and filtered to the same review dates. A later BOCHK capture cannot reconstruct deleted or edited reviews as they appeared on 19 October. Public endpoints provide a bounded, request-specific sample, not every customer or all historical reviews.

The customer comment body is `text`. Apple `title` is retained separately and included with the body for theme matching and search. Developer replies are excluded. Comments are never translated or rewritten. The English subset uses deterministic script/short-word checks and langdetect 1.0.9 (seed 0, threshold 0.80), plus separately recorded exact-text agent language corrections. Existing SC/HSBC language decisions are frozen.

Rating sentiment is a proxy: 1-2 stars negative, 3 neutral, 4-5 positive. Text lexicon sentiment is supplemental and can disagree. Eleven transparent keyword themes are multi-label mentions, including positive mentions. V2 adds explicit face/facial recognition, HKID scan and ID/email checking patterns to the access theme, and suggest/consider/combine wording to feature requests; see scripts/v2_rules.py. Raw V1 comments stay unchanged; derived themes are recomputed. A first matched theme is not a severity ranking. Broad terms such as service, notification, account, ads and FX can overmatch. The rules do not reliably handle sarcasm, negation or root causes.

Each metric uses one bank within one store. Low-star share = 1-2 star records / all English records for that bank and store. Theme mention share = records mentioning a theme / all records in that bank/store; theme low-star share uses theme mentions as its denominator. Monthly means and shares are recomputed within bank/store/month. April and October are partial calendar months. Empty groups are N/A. Differences are SC minus the named benchmark; rate differences are percentage points. Store-level sample means are not the stores' headline lifetime ratings.

Different review IDs with repeated wording remain separate; observations are review records, not unique customers. No statistical significance, incident severity, causal diagnosis, customer-population satisfaction or issue incidence is established. The reading check is performed by a Codex agent and is not an independent human annotation accuracy study.

## Collection and app identities

| Bank | Google package | Apple ID |
|---|---|---|
| SC Mobile Hong Kong | com.scb.breezebanking.hk | 445795688 |
| HSBC HK Mobile Banking | hk.com.hsbc.hsbchkmobilebanking | 1164066737 |
| BOCHK | com.bochk.app.aos | 1534534188 |

Apple search/lookup identifies BOCHK as published by Bank of China (Hong Kong) Limited; Google search and listing use the matching retail description and developer. BoC Pay+, BOCHK iGTB, BOCHK Brunei and mainland Bank of China are excluded. Identity response captures are retained.

BOCHK Google Play: 600 unique records from three 200-record pages; collection stopped after two pages entirely before the window. Apple: 500 unique records from ten 50-record pages. The page-11 boundary request returned HTTP 400; that failed response and metadata are retained. The ten accepted pages are usable; there is no claim of exhaustive Apple history. Per-group earliest dates and whether the capture reaches before the window are in coverage.csv.
