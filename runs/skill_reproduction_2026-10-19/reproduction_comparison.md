# app-review-feedback Skill 复现对照报告

本批复现验证：**通过**。实际调用已安装 Skill 的执行入口，保存到独立批次目录；原项目文件保留。

## 验证范围

采用原项目保存的 5,278 条全量快照及关联原始响应，按相同口径重新合并、质检、分类、生成报告与验证。
观察窗口为 2026-04-19 至 2026-10-19（香港时间，含截止日）；只分析英文评论，SC Mobile 为主对象，HSBC 为 benchmark，Google Play 与 Apple 合并报告。
本轮为离线快照复现；未重新联网采集，沿用原始语言识别结果。A/B 文档记录的是导入快照及其覆盖限制。

## 一致性结果

| 对照项 | 原项目 | 本次 Skill | 结果 |
|---|---:|---:|---|
| master_all_reviews | 5,278 | 5,278 | 一致 |
| master_english_all | 4,071 | 4,071 | 一致 |
| master_six_months_all | 528 | 528 | 一致 |
| master_english_six_months | 311 | 311 | 一致 |
| 逐条分类 | 311 条 × 15 个派生字段 | 同左 | 一致 |
| 银行 × 主题统计 | 22 行 | 22 行 | 一致 |
| 月度统计 | 7 个月 | 7 个月 | 见逐项检查 |

逐条核对全部 45 个原始字段。两列原始证据路径因批次迁移，使用 origin_* 回溯列比较原路径，并核对 66 个原始路径的文件内容 SHA-256；其余字段直接精确比较。
近六个月 QA 仍为：311 条可分析，105 条短正文，5 组 / 20 条重复标准化文本；重复文本保留，未按正文删除。

| 指标 | SC Mobile | HSBC benchmark |
|---|---:|---:|
| 评论数 | 98 | 213 |
| 平均星级 | 2.2551 | 3.2817 |
| 1–2 星评论数 | 65 | 86 |
| 1–2 星比例 | 66.33% | 40.38% |
| 4–5 星评论数 | 29 | 117 |

原数据、重新计算值与本次输出的逐指标对照保存在 [metric_comparison.csv](metric_comparison.csv)。
星级情绪、补充文本规则、主题、主主题、匹配词计数、分析文本等全部派生字段均逐条比较；这验证规则运行一致性，不代表分类准确率达到 100%。

## 已解释的差异

- 代表性评论：原表 20 行，涉及 14 条不同评论；本批去重为 14 条。评论集合与原文字段一致性见 JSON 的 representative_quote_semantics，统计样本仍是 311 条。
- 原总表 45 列，本批 48 列：新增来源回溯字段 origin_input_row, origin_raw_items_workspace_path, origin_raw_response_workspace_path。两列 raw_*_workspace_path 指向批次内保存的证据副本。
- CSV/JSON/Excel 的字节与哈希随来源字段变化；HTML 使用 Skill 的通用模板，代表评论去重、复核备注及证据路径也不同，因此不声称文件逐字节相同。
- QA 的部分等价字段改名；原项目同时做过全历史 QA，本批 QA 聚焦 311 条分析窗口。月度 JSON 结构也不同，已比较对应月度数值。

- 10 条复核样本的评论集合相同，排列方式不同：原表按时间从新到老，Skill 按应用及星级排列复核样本。311 条分析总表及网页评论仍按时间从新到老。

## 新批验证与保存结果

- 静态检查 7 组；浏览器检查 1,386 项。通过状态及报告哈希见下方机器记录。
- 10 条验证样本已重新逐条阅读并保存备注；这是代理抽查，不是独立人工标注集。
- 核对原项目 54 个受审计文件是否仍与原 Checkpoint F 哈希相同，并核对已安装 Skill 的 24 个文件与打包清单是否相同。
- 三张截图已保存并查看：[概览](screenshots/overview.png)、[主题](screenshots/themes.png)、[评论浏览](screenshots/comments.png)。

[离线 HTML 报告](report_customer_feedback.html) · [英文总表 CSV](data/merged/master_english_six_months.csv) · [Excel 总表](data/merged/reviews_master.xlsx) · [逐条分类 CSV](data/analysis/comment_labels.csv)

[机器对照记录（含逐文件哈希）](reproduction_comparison.json) · [静态验证](static_test_results.json) · [浏览器验证](browser_test_results.json) · [本批复核记录](manual_review.json) · [执行步骤](replay_commands.ps1)

## 逐项对照状态

- 通过：fixed_scope
- 通过：merged:master_all_reviews
- 通过：merged:master_english_all
- 通过：merged:master_six_months_all
- 通过：merged:master_english_six_months
- 通过：raw_evidence_content
- 通过：all_comment_labels
- 通过：window_qa_rows
- 通过：window_qa_summary
- 通过：benchmark:sc_mobile
- 通过：benchmark:hsbc_hk
- 通过：benchmark_difference
- 通过：all_theme_metrics
- 通过：all_monthly_metrics
- 通过：representative_quote_semantics
- 通过：validation_sample_identity
- 通过：fresh_sample_review
- 通过：installed_skill_matches_package
- 通过：original_project_unchanged
- 通过：fresh_report_validation

原样本的公开接口覆盖限制继续适用。本轮没有新增网站核验或重新识别语言，也未通过独立标注集评价主题/情绪准确率。
