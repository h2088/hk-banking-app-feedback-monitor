# Checkpoint D - customer feedback analysis

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

There are six bank/store metrics, 66 theme rows, 42 monthly rows and four SC-versus-benchmark comparisons. The reading sample contains 29 observed bank/store/rating strata. Per-comment judgments and source fingerprints are in manual_review.json.

The customer comment body is `text`. Apple `title` is retained separately and included with the body for theme matching and search. Developer replies are excluded. Comments are never translated or rewritten. The English subset uses deterministic script/short-word checks and langdetect 1.0.9 (seed 0, threshold 0.80), plus separately recorded exact-text agent language corrections. Existing SC/HSBC language decisions are frozen.

Rating sentiment is a proxy: 1-2 stars negative, 3 neutral, 4-5 positive. Text lexicon sentiment is supplemental and can disagree. Eleven transparent keyword themes are multi-label mentions, including positive mentions. V2 adds explicit face/facial recognition, HKID scan and ID/email checking patterns to the access theme, and suggest/consider/combine wording to feature requests; see scripts/v2_rules.py. Raw V1 comments stay unchanged; derived themes are recomputed. A first matched theme is not a severity ranking. Broad terms such as service, notification, account, ads and FX can overmatch. The rules do not reliably handle sarcasm, negation or root causes.

Each metric uses one bank within one store. Low-star share = 1-2 star records / all English records for that bank and store. Theme mention share = records mentioning a theme / all records in that bank/store; theme low-star share uses theme mentions as its denominator. Monthly means and shares are recomputed within bank/store/month. April and October are partial calendar months. Empty groups are N/A. Differences are SC minus the named benchmark; rate differences are percentage points. Store-level sample means are not the stores' headline lifetime ratings.

Different review IDs with repeated wording remain separate; observations are review records, not unique customers. No statistical significance, incident severity, causal diagnosis, customer-population satisfaction or issue incidence is established. The reading check is performed by a Codex agent and is not an independent human annotation accuracy study.
