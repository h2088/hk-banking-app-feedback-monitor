# Hong Kong Banking App Feedback Monitor — current V3 delivery

The current delivery is an English management report comparing SC Mobile with HSBC HK and BOCHK. Google Play and Apple App Store results are presented separately. English, Chinese and mixed English/Chinese reviews contribute to one combined analysis within each store; review language is not a reporting split.

The observation window is **19 April–19 October 2026 inclusive, Hong Kong time**. The saved sample contains **1,682 included reviews**: 1,026 from Google Play and 656 from Apple App Store. Original review bodies and Apple titles are preserved, with comments displayed newest first. The report retains the V1 horizontal blue monthly feedback chart.

## Open the current deliverables

| Deliverable | Location |
|---|---|
| V3 offline management report | [v3/report_customer_feedback_v3.html](v3/report_customer_feedback_v3.html) |
| Executive brief and methodology | [v3/executive_summary.md](v3/executive_summary.md), [v3/methodology.md](v3/methodology.md) |
| Combined original reviews | [v3/data/merged/master_bilingual_six_months.csv](v3/data/merged/master_bilingual_six_months.csv) |
| Reproduced report from the updated Skill | [runs/skill_v3_replay_2026-10-22/report_customer_feedback.html](runs/skill_v3_replay_2026-10-22/report_customer_feedback.html) |
| Reproduced workbook | [runs/skill_v3_replay_2026-10-22/data/reviews_master.xlsx](runs/skill_v3_replay_2026-10-22/data/reviews_master.xlsx) |
| Maintained reusable Skill | [skills/v3/app-review-feedback/SKILL.md](skills/v3/app-review-feedback/SKILL.md) |
| Skill package | [dist/app-review-feedback-v3.skill](dist/app-review-feedback-v3.skill) |
| Skill release notes and validation | [skills/v3/README.md](skills/v3/README.md), [skills/v3/release_verification.json](skills/v3/release_verification.json) |

Download an HTML report and open it locally. The reports contain their data and need no server, login, API key or network connection. GitHub's file view displays HTML source rather than running the interactive report.

## Reuse and verification

The updated Skill supports saved-input reproduction and fresh collection into new batch directories, configurable banks and date windows, bilingual eligibility and topic rules, separate store comparisons, eight-sheet Excel exports, raw-source checks and browser verification. Follow its instructions for reading the selected review sample and inspecting actual screenshots before finalizing a new delivery.

The full saved-input replay reproduced all 1,682 included reviews, original fingerprints, sentiment/topic labels, bank/store metrics, monthly figures and benchmark numeric values. Six behavioral tests, 17 static check groups and 10,778 browser assertions passed; seven screenshots were inspected. This Skill update did not perform a new live crawl.

The September-only batch in `runs/skill_v3_september_test_2026-10-22/` is an analysis test with 284 reviews. Its manual review remains pending; it is not a finalized management delivery.

## Historical releases and data limits

The root [README.md](README.md), original `skills/app-review-feedback/` and original package describe the preserved V1 release. [v2/README.md](v2/README.md) describes the English-only three-bank release. The current Skill source is under `skills/v3/`; historical files are retained to preserve their recorded hashes. Older documents describe the state at their own release time.

Public store endpoints provide bounded samples. SC/HSBC English inputs were captured on 19 October; BOCHK and the later Chinese Google Play inputs were captured on 22 October and filtered to the agreed review-date window. Apple collection is limited by its public feed pagination. These samples do not establish complete historical coverage or represent all customers.

One historical V3 file, `v3/data/reviews_v3.xlsx`, differs from its original final-manifest hash. The observed workbook was preserved without overwriting it, and the difference is recorded in the release verification. The new Skill replay workbook linked above and all 191 files in that completed replay manifest passed integrity checks.
