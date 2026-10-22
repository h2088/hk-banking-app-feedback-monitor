# Validation and release history

## Release scope

The maintained combined bilingual release uses schema 2. English manager delivery; SC Mobile primary, HSBC HK and BOCHK benchmarks by default; separate Google Play / Apple results; one combined English/Chinese population; V1 horizontal monthly monitoring chart. Custom bank names/IDs, multiple benchmarks and date windows are configuration, not fixed historical facts.

The historical V1 engine was English-only, one benchmark and pooled stores. Keep that release immutable; never run its extraction utility over this release. Original parsing/theme/typed-cell provenance remains in resource_provenance.json. The bilingual and English extensions are separate modules, and the schema-2 orchestration/report/browser verification are maintained here.

## Meaningful maintenance checks

~~~powershell
python -B '<skill>\scripts\test_workflow.py'
python -B '<skill-creator>\scripts\quick_validate.py' '<skill>'
~~~

Tests must cover combined eligibility (including Chinese-only text), bilingual themes, exact language overrides, imported source-decision bindings, date boundaries and dynamic partial months, zero denominators, renamed apps/benchmark directions, locale job orchestration, Apple page-11 HTTP 400 boundary, and refusal of pending/stale review/config/raw data. No network is required for these maintenance checks.

Separately run the full CLI pipeline against a saved real snapshot, actually inspect the sample or safely reuse an exact prior source-bound review, verify every included raw response, run the real browser and inspect screenshots. A narrow test is not a substitute for this full workflow.

## Reproduction baseline

The corrected V3 project snapshot covers 2026-04-19 through 2026-10-19 inclusive HKT. It has 9,963 saved unique all-date records and 1,682 included English/Chinese records: Google Play 1,026 and Apple App Store 656.

| Store | Bank | Reviews | Mean rating | 1–2 star count |
|---|---|---:|---:|---:|
| Google Play | SC Mobile | 202 | 1.9208 | 149 |
| Google Play | HSBC HK | 378 | 3.0079 | 171 |
| Google Play | BOCHK | 446 | 2.7646 | 228 |
| Apple App Store | SC Mobile | 108 | 2.2870 | 68 |
| Apple App Store | HSBC HK | 267 | 3.3670 | 102 |
| Apple App Store | BOCHK | 281 | 2.9253 | 137 |

This is a regression fixture, never the expected outcome for fresh collection or a different window. A reproduction compares original fingerprints, per-row star/topic labels, all combined metrics, monthly values and benchmark differences. Generic report copy/build times can change its HTML hash without changing data results.

New samples start pending. Actual agent reading is not independent human labeling or an accuracy estimate. Topic limitations and rating/text disagreements must stay visible in reading notes and methodology.

## Checks performed for this release (2026-10-22)

- Six offline behavioral test cases passed, covering source/config/raw guards, exact language decisions, Chinese topics, window/partial-month boundaries, changed app names/IDs, reversed comparisons, formula-safe export, three Google locale jobs per bank, failed capture status and Apple page-11 HTTP 400.
- The saved all-date V3 input reproduced 1,682 included rows. All original fingerprints, per-row star/topic labels, bank/store metrics, topic tables, monthly tables and benchmark numeric values matched. Added explicit benchmark keys account for the delta-table schema extension.
- All 47 sample records and the sample SHA-256 matched. Previously recorded actual reading notes were reused with original reviewer/time/file digest after exact source and label checks; this was not represented as a fresh reading.
- Static verification passed 17 groups and matched all 1,682 included records against exact saved raw HTTP items.
- Actual Edge browser verification passed 10,778 assertions, generated seven screenshots, and those seven screenshots were actually opened and inspected by the agent. Both store charts and the combined comment browser were checked.
- A separate synthetic browser run passed 386 assertions with renamed two-bank configuration, a full one-month window, empty Google data, negative benchmark gap and literal markup. Synthetic annotations remained test-only.
- The same real input narrowed to 2026-09-01 through 2026-09-30 selected 284 records, independently reconciled to source fingerprints and six bank/store metrics. It produced one complete calendar month per store. Its new 37-record reading sample stayed pending; this analysis-only test was not finalized as a customer report.
- Skill frontmatter passed the skill-creator quick validator. Fresh collection orchestration was mock-tested; this release did not perform a new live crawl.

The full replay and release records are stored outside the Skill package. These checks establish the observed reproducibility and behavior above; future inputs still require their own validation.

## Coverage limits

Saved SC/HSBC snapshots and later BOCHK/Chinese retrieval have different capture dates. Apple public RSS is bounded; Google locales may expose overlapping/request-specific samples. Reproduction is offline and does not update current coverage. Fresh collector orchestration must be described as mock-tested unless a new live crawl has actually been performed.

No statistical significance, full historical completeness, live alerts, cross-device certification or production scheduling is implied. Each delivered run records its own results in validation/ and manifest.json. The Skill package contains code/templates/methods only, not comments, raw responses, user names, run files or personal reading judgments.
