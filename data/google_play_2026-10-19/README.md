# Google Play 评论采集结果入口

请优先查看 **run_03_full_history**，这是本轮最终数据集。

- `run_03_full_history/review_browser.html`：双击即可在浏览器中查看、搜索和筛选英文评论，默认显示近六个月，按时间从新到老。
- `run_03_full_history/english_six_months.csv`：2026/04/19–2026/10/19 的英文评论，共 140 条。
- `run_03_full_history/all_languages_fetched.csv`：公开接口在本次英文页面、香港地区设置下返回的全部 4,278 条不同 ID 的历史评论。
- `run_03_full_history/collection_report.json`：数量、日期范围、分页结果和终止原因。
- `run_03_full_history/sc_mobile/raw`、`run_03_full_history/hsbc_hk/raw`：原始响应、请求参数、时间和 SHA-256。

两家应用均已翻页至接口不再返回下一页 token：渣打 6 页 / 1,051 条，汇丰 17 页 / 3,227 条。
这描述的是当前接口及设置能访问到的数据，不保证等同于平台所有地区、语言和设备下的全部评论。

其他目录仅用于保留采集过程证据，**不要将不同目录的重复评论相加**：

- `run_01`：沙箱联网失败的请求日志，没有成功抓取评论。
- `run_02`：首次按六个月边界停止的试抓，每家 600 条；评论已包含在最终数据集中。
- `locale_probe`：交换 `en` / `en-US` 设置，对每家最新 200 条进行对照。不是额外的新评论。

2026/10/19 是日期上限。本次实际最新英文评论：渣打 2026/10/16，汇丰 2026/10/15。
所有导出日期显式使用香港时间 UTC+08:00，同时保留 UTC 与原始 UNIX 秒。
