# Reusable Skill update — combined bilingual V3

The maintained app-review-feedback Skill now reproduces the corrected V3 reporting brief: English delivery; SC Mobile primary; HSBC HK and BOCHK benchmarks; separate Google Play and Apple results; one combined English/Chinese analysis; original source wording; V1 horizontal blue monthly volume bars with bank counts and low-star shares.

The update includes instructions, default bank identities, multilingual collection jobs, source-preserving preparation, bilingual classification, parameterized aggregation/reporting, eight-sheet Excel output, exact raw verification, actual-browser tests and evidence-bound delivery. Dates, sample size, app names and benchmark directions are computed from input/configuration. Schema 2 batches use a new output directory.

## Maintained locations

- Project release source: skills/v3/app-review-feedback/SKILL.md.
- Installed canonical source: C:/Users/1/.codex/skills/app-review-feedback/SKILL.md.
- Distributable: dist/app-review-feedback-v3.skill (ZIP-format Skill archive).
- Package hashes: dist/app-review-feedback-v3.manifest.json.
- Full offline reproduction: runs/skill_v3_replay_2026-10-22/report_customer_feedback.html.
- Reproduction comparison: that batch's validation/reproduction_comparison.json.
- Alternate-window analysis-only test: runs/skill_v3_september_test_2026-10-22/.

The historical project source skills/app-review-feedback/ and original dist/app-review-feedback.zip remain immutable because historical preservation manifests cover them. Before replacement, the old installed Skill is archived in runs/app_review_feedback_installed_before_v3_2026-10-22.zip. Only the installed canonical path and the new release copy receive this update.

## Observed validation

The saved 9,963-row all-date V3 snapshot reproduced 1,682 included comments: Google Play 1,026; Apple 656. All original fingerprints, per-row star/topic labels, combined bank/store metrics, topic/monthly tables and benchmark numeric values match corrected V3. The new delta schema adds explicit primary/benchmark keys. The HTML differs because its copy is reusable and its import coverage note describes this run.

All 47 selected reading records and their sample SHA-256 matched. Prior actual source-bound notes were explicitly reused with reviewer/time and source file digest, after unchanged source and labels were verified. This is not a fresh reading or independent human annotation claim.

Six offline behavioral tests passed; static validation passed 17 groups and verified all 1,682 exact raw source items; Edge passed 10,778 assertions; all seven resulting screenshots were actually inspected. An additional synthetic two-bank/empty-store/reversed-gap browser test passed 386 assertions. The same real snapshot narrowed to September 2026 produced 284 independently reconciled records and one complete calendar month per store. That analysis-only test's new 37-record reading sample remains pending and is not a completed customer delivery. Skill frontmatter passed the skill-creator validator.

This update performs no new live collection. Multilocale job orchestration and Apple page-11 HTTP 400 behavior are mock-tested; public endpoints and coverage must be checked on a future fresh crawl. The package contains no customer comments, raw responses or private reading notes.

Final release integrity: installed/project/staged/archive copies match all 25 packaged files; all 191 files in the completed Skill replay manifest match. The installed verifier also passed a read-only finalized-batch audit. Historical preservation maps (1,811 + 2,020 + 198 entries) and all 208 V2 final files match. The original V3 final manifest has one observed difference out of 265 files: data/reviews_v3.xlsx is 683,690 bytes with SHA-256 1e5432a7a89d5530b2d78fe2d5159f03050868d3738efbf0cdd99d688276b50b, while its old manifest expects 782,944 bytes / b92014d4daad28262398a851d7b07cc81a1ee1eb04632d1db7c3e7c04370cd59. The original workbook was preserved, not overwritten; the new replay workbook and all source JSON/raw comparisons passed. See release_verification.json for exact hashes and counts. This discrepancy is not presented as a passing historical file check.

## Invoke the installed Skill

> 使用 $app-review-feedback，基于当前保存的 V3 原始快照离线复跑，沿用 2026-04-19 至 2026-10-19。SC Mobile 为主要对象，HSBC HK 和 BOCHK 作 benchmark。生成英文报告；Google Play 和 Apple 分开，中英文评论合并分析，保留 V1 横向蓝色月度反馈监测图，结果保存到新的批次目录。

For a fresh future crawl, request collection and a new date window explicitly. The default future window is current HK date minus six calendar months. The workflow requires actual reading and visual inspection before finalization; it is not a scheduled monitoring service. If an existing session still displays the V1 catalog description, open a new session or explicitly ask it to read the installed SKILL.md.
