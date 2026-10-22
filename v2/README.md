# Hong Kong Banking App Feedback Monitor - V2

Manager-ready English report with separate Google Play and Apple App Store comparisons of SC Mobile against HSBC HK and BOCHK.

Open [the offline report](report_customer_feedback_v2.html). Read [the executive brief](executive_summary.md), [methodology](methodology.md) and [handover](handover.md). The Excel workbook is [data/reviews_v2.xlsx](data/reviews_v2.xlsx); its two review sheets are separated by store.

Observation window: 19 April to 19 October 2026 inclusive, Hong Kong time. SC and HSBC retain the 19 October V1 capture; BOCHK was captured on 22 October and filtered to the same review dates. A later BOCHK capture cannot reconstruct deleted or edited reviews as they appeared on 19 October. Public endpoints provide a bounded, request-specific sample, not every customer or all historical reviews.

Accepted English records: **418** (311 unchanged SC/HSBC records plus 107 BOCHK records). Full fetched source records, including excluded dates/languages: 6378.

## What changed

| Manager request | V2 delivery |
|---|---|
| Change it into English | Report, controls, methods, checkpoints and handover in English; source comments preserved verbatim |
| Separate stores | Six bank/store groups; separate metric, theme, monthly and review views; two Excel review sheets and six CSV slices |
| Add BOC HK | Verified BOCHK retail app from Bank of China (Hong Kong) Limited; independent HSBC and BOCHK benchmark deltas in each store |

V1 remains intact. The original installed Skill and its CLI still support the original two-bank combined-store scope. V2 uses `scripts/pipeline.py`, with a frozen copy of its collection, classification and export helpers in `engine/`; do not use `engine/run_feedback.py` for V2.

See [reproduction.md](reproduction.md) to rerun locally. No server, API key or CDN is needed to read the report.
