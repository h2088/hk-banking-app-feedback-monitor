# HK Banking App Feedback Monitor

香港银行手机应用客户评论监测与对比分析项目。项目以 SC Mobile Hong Kong 为主对象、HSBC HK Mobile Banking 为 benchmark，整理 Google Play 和 Apple App Store 的公开英文评论，完成来源可行性评估、采集与覆盖说明、数据质量检查、星级情绪与银行业务主题分类、应用总体对比，以及可离线筛选的 HTML 报告。

> 本仓库保存的是截至 2026-10-19 的研究快照，不是持续更新的服务。数据覆盖取决于各应用商店公开接口，不能视为评论全集或客户总体意见；对比是描述性样本分析，不推断因果或统计显著性。

## 项目结果

- 最终观察窗口：2026-04-19 至 2026-10-19（香港时间，含起止日期）。
- 分析集：311 条英文评论；评论保留来源、日期、星级、原文与回溯字段。
- 合并来源：Google Play 和 Apple App Store；报告按应用汇总，不拆分平台。
- SC Mobile：98 条，平均星级 2.2551，1–2 星占 66.33%。
- HSBC benchmark：213 条，平均星级 3.2817，1–2 星占 40.38%。
- 交互式离线报告可搜索评论、过滤应用／星级／情绪／主题，并查看来源及原始响应证据。
- `runs/skill_reproduction_2026-10-19/` 保存了可复核的 Skill 复现批次、逐条对照、运行结果和截图。复现使用保存的历史快照，不是重新抓取。

## 快速查看

- [最终客户反馈报告](report_customer_feedback_2026-10-19.html)
- [英文六个月合并评论 CSV](data/merged_2026-10-19/master_english_six_months.csv)
- [英文六个月合并评论 JSON](data/merged_2026-10-19/master_english_six_months.json)
- [Excel 合并数据表](data/merged_2026-10-19/reviews_master.xlsx)
- [逐条情绪与主题标签](data/checkpoint_D_analysis_2026-10-19/comment_labels.csv)
- [复用 Skill](skills/app-review-feedback/SKILL.md)
- [项目计划与交接说明](plan.md) · [最终复核](checkpoint_F_final_review.md)
- [Skill 复现对照报告](runs/skill_reproduction_2026-10-19/reproduction_comparison.md)

## 目录结构

```text
.
├── plan.md, checkpoint_A...checkpoint_F...md, handover.md
├── report_customer_feedback_2026-10-19.html
├── data/
│   ├── google_play_2026-10-19/       # Google Play 采集、原始响应与探测证据
│   ├── apple_2026-10-19/             # App Store 采集、RSS 原始响应与探测证据
│   ├── merged_2026-10-19/             # 统一主表与数据字典／哈希清单
│   ├── checkpoint_C_qa_2026-10-19/   # 数据 QA 与覆盖统计
│   ├── checkpoint_D_analysis_2026-10-19/ # 评论标签、主题和 benchmark 统计
│   └── checkpoint_F_review_2026-10-19/   # 最终复核与文件哈希
├── scripts/                            # 项目分析、报告及审计脚本
├── skills/app-review-feedback/         # 可复用 Codex Skill 源文件
├── dist/                               # Skill 分发包与文件清单
└── runs/skill_reproduction_2026-10-19/ # 使用已安装 Skill 的离线复现批次
```

仓库有意忽略本机 `.venv`、`.cache` 和 Python 字节码；采集原始证据与研究产物保留。完整复现批次约 65 MB，整个跟踪文件约 178 MB。提交前请检查原始公开评论和公开显示名是否符合你的分享与隐私要求。

## 方法与限制

- 来源及样本覆盖方式、端点限制和运行记录见 `checkpoint_A_source_feasibility.md`、`checkpoint_B_data_collection.md` 及 `data/**/README.md`。
- QA 标记重复正文、短评论、日期和来源覆盖；重复文本是审查提示，不据此删除不同 ID 的评论。
- 主要情绪口径采用来源星级：1–2 星负面、3 星中性、4–5 星正面。文本词典结果作为补充信号单独报告。
- 主题使用可审计的关键词／短语规则，多主题可并存；未命中主题的评论不会强行分类。人工样本复核是抽查，不等同分类准确率评估。
- 不同应用样本数和平台构成不均衡；报告不作因果、显著性或总体客户满意度推断。Apple 与 Google 的公开接口覆盖也不保证完整。
- 数据时间截止于 2026-10-19，边界月份可能不完整。重新运行时应建立新批次并重新验证来源、数据和标签，而不是将旧快照当作当前状态。

## 重用 Skill

Skill 源码在 `skills/app-review-feedback/`，包含工作流说明、采集器、质量检查、规则分类、报告模板、验证步骤和离线测试入口。先阅读 `SKILL.md` 与 `references/` 再运行。

```powershell
# 安装项目依赖后，可通过 Skill 的 CLI 建立独立批次。
# 例如：
python skills/app-review-feedback/scripts/run_feedback.py init `
  --root runs/next_snapshot `
  --since 2026-04-20 `
  --as-of 2026-10-20
```

重新联网采集可能受端点可用性、应用商店分页策略、网络和速率限制影响；不要假设会重现这份历史样本。项目原采集器和 Skill 各自有自己的执行说明与依赖文件，请按对应说明准备环境。

## 环境与使用

HTML 报告可直接在浏览器中离线打开。审阅精确字段和类型时优先用 JSON；CSV 更便于表格软件筛选。原始采集响应只用于证据追溯，解码格式依来源而异。

如运行项目原有采集脚本，请先查看 `requirements-scraping.txt`、对应脚本参数、来源限制和应用商店条款。公开可访问不代表拥有无限制抓取或再发布授权。
