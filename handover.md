# SC Mobile 客户反馈监测 — 交接说明

交付日期：2026-10-19。当前范围的 Checkpoints A–F 已完成；这是静态监测快照，不会自动抓取或更新。

## 打开与阅读

直接双击 [report_customer_feedback_2026-10-19.html](report_customer_feedback_2026-10-19.html)，用桌面浏览器打开即可。无需启动服务、安装 Python 或联网加载图表。已验证本机桌面 Edge；其他浏览器和手机未逐一测试。

建议顺序：总体比较 → 月度监测 → 主题反馈 → 评论浏览。评论浏览可组合筛选应用、星级、星级情绪、主题与关键词。每页 60 条，共 6 页，全部 311 条按香港时间从新到老排序。

## 本次结果怎么理解

只分析英文客户评论，以 SC 为主对象、HSBC 为 benchmark，合并 Google Play 和 Apple App Store，不拆平台指标。

- 观察窗口：香港时间 2026-04-19 00:00（含）至 2026-10-20 00:00（不含）；样本实际最新记录为 **2026-10-16**，不是 10 月 19 日。
- 样本：311 条；SC 98 条、HSBC 213 条。
- 平均星级：SC 2.2551，HSBC 3.2817；1–2 星比例分别为 66.33%（65/98）、40.38%（86/213）。
- 当前样本中，SC 的反馈更负面，稳定性、登录认证、转账支付是重点监测方向；这是描述性比较，不是总体客户调查、故障率或显著性结论。
- 情绪主标签由星级映射，主题由保守短语规则多标签匹配；10 条人工抽查不等于分类准确率评估。

## 如何自己核查一条评论

1. 在“评论浏览器”先清空筛选，确认显示 311 条；首条为 SC、2026-10-16 09:25:03、1 星，正文以 “the app force closed unexpectedly after the update” 开头。
2. 筛选应用或关键词，记录评论 ID、日期、标题（如有）、原始正文及星级。
3. 点击“来源核查”（需要联网）。Google 或 Apple 可能只打开应用评论列表；Apple 尤其不保证定位单条。结合日期、星级、原文核查，网页排序／地区／后续编辑都可能造成差异。
4. 点击“已存原始响应”核查采集快照。文件是原始 HTTP 内容，浏览器可能显示文本或下载；可用文本编辑器查看，不必执行。若编码、转义或整页内容不便阅读，在总表用 `record_key` 查找 `source_json_file`、`source_row_index`、`raw_item_index`／`raw_entry_index` 追溯。
5. 总表以 [master_english_six_months.csv](data/merged_2026-10-19/master_english_six_months.csv) 为准；需要保留数字、布尔值、空值类型时用 [同名 JSON](data/merged_2026-10-19/master_english_six_months.json)。Excel 若自动转换评论 ID，建议从“数据 → 自文本/CSV”导入并将 ID 列设为文本。

网站不能显示某条评论，不应直接删掉采集记录或推断其不存在；应标为当前网页尚未核实，并保留已存来源证据。

## 分享与保存哪些文件

- **只看报告**：发送单个 HTML 即可离线浏览全部指标与评论；CSV、方法文档、原始响应链接会因为配套文件不在而无法打开。
- **可核查交付**：保留 HTML、`plan.md`、A–F 检查点、本文档，以及整个 `data/`、`scripts/` 的相对目录结构。无需分享 `.venv/` 和 `.cache/`；只阅读不需要 Python。接收者若要重跑测试，需准备 Python 3.13（本项目使用的版本）及脚本所需环境。
- 不要只复制 `merged_2026-10-19/`：原始响应位于 `data/google_play_2026-10-19/run_03_full_history/` 和 `data/apple_2026-10-19/run_03/`，不在合并表目录中。
- HTML 不内嵌用户名，但总表／原始响应仍保留公开显示名等来源字段。完整证据包用于核查，对外发布前需另查授权与脱敏，不默认视为已脱敏资料。

## 方法、测试与维护

- [最终审核记录](checkpoint_F_final_review.md)：验收范围、事实核对、限制及交付判断。
- [分析方法与结论](checkpoint_D_customer_feedback_analysis.md)、[数据质量](checkpoint_C_data_qa.md)、[构建与测试](checkpoint_E_build_test.md)。
- [逐条标签 CSV](data/checkpoint_D_analysis_2026-10-19/comment_labels.csv)：原评论加派生情绪／主题字段。
- [最终复核结果](data/checkpoint_F_review_2026-10-19/final_review_results.json)：哈希、复核项目与结果。

已有项目 Python 环境时，在根目录重新核查（不联网、不重抓取）：

```powershell
.\.venv\Scripts\python.exe scripts\test_feedback_report.py
.\.venv\Scripts\python.exe scripts\final_review_feedback.py
```

静态测试 12 项通过；E 的浏览器交互 1,398 项断言通过。F 确认同一 HTML 哈希后沿用浏览器结果，并非新增人工标注。HTML 顶部的 “Checkpoint E” 指构建阶段，不表示 F 未完成。

若数据需要更新，应另建批次、重新采集／QA／分类／构建并重新测试；不要覆盖本轮原始快照，也不要只修改网页上的数字或日期。
