# Hong Kong Banking App Feedback Monitor — V3

SC Mobile is compared with HSBC HK and BOCHK using **one combined English/Chinese customer-review sample for each bank within each app store**. Google Play and Apple App Store remain separate. Management reporting is English; original comments are unchanged. The review window is **19 April–19 October 2026 inclusive, Hong Kong time**.

The analysis contains **1,682 reviews**. Review language is an inclusion/quality-control attribute, not a reporting dimension. There is no language selector or language-specific performance comparison.

| Store | Bank | Reviews | Mean rating | 1–2 star share |
|---|---|---:|---:|---:|
| Google Play | SC Mobile | 202 | 1.92 | 73.8% |
| Google Play | HSBC HK | 378 | 3.01 | 45.2% |
| Google Play | BOCHK | 446 | 2.76 | 51.1% |
| Apple App Store | SC Mobile | 108 | 2.29 | 63.0% |
| Apple App Store | HSBC HK | 267 | 3.37 | 38.2% |
| Apple App Store | BOCHK | 281 | 2.93 | 48.8% |

SC has a higher low-star share and lower sample mean rating than both benchmarks within each store.

- Google Play, SC vs HSBC HK: **+28.5 percentage points** in low-star share; -1.09 stars in sample mean.
- Google Play, SC vs BOCHK: **+22.6 percentage points** in low-star share; -0.84 stars in sample mean.
- Apple App Store, SC vs HSBC HK: **+24.8 percentage points** in low-star share; -1.08 stars in sample mean.
- Apple App Store, SC vs BOCHK: **+14.2 percentage points** in low-star share; -0.64 stars in sample mean.

SC topics with the most low-star mentions:

- Google Play: App stability / performance — 69 mentions, 60 low-star; Login / authentication / access — 58 mentions, 51 low-star; Transfers / payments / cards — 56 mentions, 43 low-star.
- Apple App Store: Login / authentication / access — 43 mentions, 37 low-star; App stability / performance — 28 mentions, 24 low-star; Transfers / payments / cards — 31 mentions, 18 low-star.

Investigate login/identity and stability journeys first, then transfer/payment journeys, using source comments and separate store results. Confirm candidate issues with release/device information, telemetry and support cases. Topic mentions overlap and include praise; they do not establish defects, causes or complaint rates.

The V1 monthly chart is retained: horizontal blue bars show total captured reviews across three banks in the selected store; adjacent figures show each bank's review count and its own 1–2 star share. April and October are partial months. Volumes reflect saved samples, not all feedback generated that month.

This correction reuses the same 1,682 V3 records and labels. Original SC/HSBC captures are dated 19 October; BOCHK and additional Google Chinese-locale captures are dated 22 October. Apple uses bounded saved HK feeds. Capture timing and endpoint limits prevent a complete historical census. See methodology.md.
