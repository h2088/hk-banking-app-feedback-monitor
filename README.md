# Hong Kong Banking App Feedback Monitor

Monitor public customer feedback on Hong Kong banking apps and compare **SC Mobile** with **HSBC HK** and **BOCHK (Bank of China Hong Kong)**. The project turns saved app-store reviews into an English management report, traceable review exports and a reusable analysis workflow.

**Current release: V3.** Google Play and Apple App Store results are presented separately. English, Chinese and mixed English/Chinese reviews contribute to one combined analysis within each store. Original comments and Apple review titles retain their source wording.

Start with the [V3 offline report](v3/report_customer_feedback_v3.html), [executive summary](v3/executive_summary.md) or [release overview](RELEASE_V3.md). Download the HTML report and open it in a browser to use its interactive controls; GitHub's file view shows the source. The report works offline without a server, login or API key.

## Current scope and sample

The observation window is **19 April–19 October 2026 inclusive, Hong Kong time**. The saved analysis includes **1,682 reviews**.

| Bank | Google Play reviews | Apple App Store reviews |
|---|---:|---:|
| SC Mobile — primary app | 202 | 108 |
| HSBC HK — benchmark | 378 | 267 |
| BOCHK — benchmark | 446 | 281 |
| **Total** | **1,026** | **656** |

Metrics, topics and benchmark differences are calculated within each store using all eligible English and Chinese comments together. Language metadata is retained for eligibility checks and audit; it is not a reporting split.

## What the report provides

- Separate Google Play and Apple App Store views comparing SC Mobile with both benchmarks.
- Review volumes, average ratings and low-star shares, with a consistent rating-based sentiment proxy.
- Bilingual, multi-label topic classification covering login, authentication, transfers, payments, stability, customer service and other banking app experiences.
- The V1 horizontal blue monthly feedback chart, extended to all three banks and switched by store, with bank review counts and low-star shares.
- Original comments displayed newest first, with bank, rating, sentiment, topic and text-search controls, plus source references for verification.

## Reports, data and reusable Skill

| Deliverable | Location |
|---|---|
| V3 management report | [report_customer_feedback_v3.html](v3/report_customer_feedback_v3.html) |
| Executive summary | [v3/executive_summary.md](v3/executive_summary.md) |
| Methodology and field definitions | [v3/methodology.md](v3/methodology.md), [v3/data_dictionary.md](v3/data_dictionary.md) |
| Combined original reviews, newest first | [CSV](v3/data/merged/master_bilingual_six_months.csv), [JSON](v3/data/merged/master_bilingual_six_months.json) |
| Per-review sentiment and topic labels | [v3/data/analysis/comment_labels.csv](v3/data/analysis/comment_labels.csv) |
| Bank/store metrics and benchmark differences | [store_benchmarks.csv](v3/data/analysis/store_benchmarks.csv), [benchmark_deltas.csv](v3/data/analysis/benchmark_deltas.csv) |
| Monthly feedback chart data | [monthly_feedback_monitoring.csv](v3/data/analysis/monthly_feedback_monitoring.csv) |
| Raw source evidence | [v3/data/raw/imported/](v3/data/raw/imported/), [v3/data/chinese_collection/](v3/data/chinese_collection/) |
| Updated Skill replay report | [runs/skill_v3_replay_2026-10-22/report_customer_feedback.html](runs/skill_v3_replay_2026-10-22/report_customer_feedback.html) |
| Verified replay workbook — eight sheets | [runs/skill_v3_replay_2026-10-22/data/reviews_master.xlsx](runs/skill_v3_replay_2026-10-22/data/reviews_master.xlsx) |
| Maintained reusable Skill | [skills/v3/app-review-feedback/SKILL.md](skills/v3/app-review-feedback/SKILL.md) |
| Skill distribution and package hashes | [app-review-feedback-v3.skill](dist/app-review-feedback-v3.skill), [manifest](dist/app-review-feedback-v3.manifest.json) |
| Skill release notes and verification | [skills/v3/README.md](skills/v3/README.md), [release_verification.json](skills/v3/release_verification.json) |

## Workflow and methods

1. **Define the scope and verify sources.** Confirm official app identities, the primary bank, benchmarks, stores and date window.
2. **Collect or import reviews.** Preserve public Google Play responses and Apple Hong Kong App Store feeds, request parameters, capture timestamps and bounded stopping reasons. Saved-input reproduction is recorded separately from fresh collection.
3. **Prepare and check the data.** Deduplicate by store, app ID and review ID; preserve original text and source variants; apply Hong Kong date boundaries and English/Chinese eligibility checks. Identical wording under different review IDs is retained.
4. **Classify and compare feedback.** Use 1–2 stars as a negative sentiment proxy, 3 as neutral and 4–5 as positive. Apply auditable bilingual topic rules; a review can mention multiple topics. Calculate metrics and both benchmark differences within each store, then read a stratified sample and record the review judgments.
5. **Build and test the delivery.** Export CSV, JSON, Excel and a standalone English HTML report. Verify exact source text, aggregate calculations, chart data, controls and pagination; inspect screenshots from the actual browser run.
6. **Finalize an auditable batch.** Save checkpoints A–F, coverage notes, validation evidence and file hashes. New date windows, inputs or classification rules use a new batch directory.

The customer feedback body is the `text` field. Apple `title` is retained separately and supplements search and topic matching. Developer replies are excluded from the analysis. Source comments are preserved rather than translated or rewritten.

## Reuse the workflow

The maintained Skill source is **[skills/v3/app-review-feedback/](skills/v3/app-review-feedback/)**. Follow its [execution guide](skills/v3/app-review-feedback/references/execution.md) for dependencies, collection/import steps and validation requirements. The `.skill` distribution is a ZIP-format archive containing instructions, code and templates; customer comments and raw responses are stored separately in the project.

Example request for an agent with the Skill installed:

> Use $app-review-feedback to reproduce the saved V3 snapshot offline for 2026-04-19 through 2026-10-19. Use SC Mobile as the primary app, with HSBC HK and BOCHK as benchmarks. Produce an English report with separate Google Play and Apple App Store results, combine English and Chinese comments within each store, retain the horizontal blue monthly feedback chart, and save the output in a new batch directory.

For a fresh update, explicitly request live collection and a new date window. New batches require the selected review sample to be read and the generated screenshots to be inspected before finalization.

## Verification and coverage limits

The completed Skill replay reproduced all **1,682 included reviews**, original fingerprints, rating/topic labels, bank/store metrics, monthly figures and benchmark numeric values. Six behavioral tests, 17 static check groups and 10,778 browser assertions passed; seven screenshots were inspected. All 191 files in the completed replay manifest matched. See the [reproduction comparison](runs/skill_v3_replay_2026-10-22/validation/reproduction_comparison.json) and [release verification](skills/v3/release_verification.json).

The saved inputs were captured on different dates: SC/HSBC English inputs on 19 October 2026, and BOCHK and the later Chinese Google Play inputs on 22 October. All included review dates use the agreed observation window. Apple coverage is bounded by its public feed pagination. These are descriptive public-review samples, not complete historical archives or estimates of all customers' satisfaction. Ratings are sentiment proxies; topic mentions do not establish complaint incidence, root causes or statistical significance. April and October are partial observation months.

The Skill update and full replay used saved inputs and performed no new live collection. The September-only batch in `runs/skill_v3_september_test_2026-10-22/` is an analysis test with 284 reviews; its manual review remains pending. The original `v3/data/reviews_v3.xlsx` has a documented historical-manifest difference; the verified replay workbook linked above is available for use.

## Repository and release history

```text
v3/                                      Current bilingual, three-bank report and evidence
skills/v3/app-review-feedback/            Maintained reusable Skill source
dist/app-review-feedback-v3.skill         Current Skill distribution
runs/skill_v3_replay_2026-10-22/           Completed saved-input Skill reproduction
runs/skill_v3_september_test_2026-10-22/   Alternate-window analysis test
v2/                                      Historical English-only, three-bank release
data/, scripts/, skills/app-review-feedback/
                                         Historical V1 inputs, workflow and Skill
```

The [original V1 README](https://github.com/h2088/hk-banking-app-feedback-monitor/blob/5f141f3a0131405e2783218d516d6303708ed4eb/README.md) describes the 311-review, English-only, two-bank release. [V2](v2/README.md) added BOCHK and separate stores; V3 added Chinese reviews to the combined analysis and restored the monthly chart. Older documents describe the state at their release time.

The root README now serves as the current project homepage. Historical V2/V3 preservation manifests include the former root README; to rerun those exact historical checks, use the [frozen delivery commit `4f3fd1e`](https://github.com/h2088/hk-banking-app-feedback-monitor/tree/4f3fd1e54348e206c03817a282811c41e330fae9). For new analysis batches, use the maintained V3 Skill and its execution guide.
