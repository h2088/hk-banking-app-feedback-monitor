# Apple 英文评论采集结果与方法

最终目录：`data/apple_2026-10-19/run_03/`。

[打开离线核查网页](data/apple_2026-10-19/run_03/review_browser.html)。默认展示 2026/04/19–2026/10/19 的 171 条英文记录，可按应用、星级、标题、正文、显示名或评论 ID 筛选。

| 应用 | Apple ID | 返回记录 | 返回样本中的英文 | 六个月内全部记录 | 六个月内英文 |
|---|---|---:|---:|---:|---:|
| SC Mobile Hong Kong | 445795688 | 500 | 261 | 108 | 50 |
| HSBC HK Mobile Banking | 1164066737 | 500 | 208 | 268 | 121 |
| 合计 | — | 1,000 | 469 | 376 | 171 |

渣打最新英文评论为香港时间 2026/10/12 17:46:39；汇丰为 2026/10/10 08:21:26。若包含非英文，最新返回记录分别为 2026/10/15 22:48:31 和 2026/10/17 14:33:05。没有把这些日期改成用户指定的 10 月 19 日。

## 采集方法

Google Play：Python 自写采集脚本通过 urllib 发出 HTTP POST，使用 google-play-scraper 1.2.7 的请求格式与字段映射。访问网页加载评论所使用的 `/_/PlayStoreUi/data/batchexecute`，RPC 为 oCPfdb，sort=2（NEWEST），每次请求 200 条，通过返回的 continuation token 翻页。此前保存了 4,278 条不同 ID 的历史记录，六个月英文子集为 140 条。

Apple：直接 GET Apple 的公开香港区 Customer Reviews RSS，使用 mostRecent 排序，读取 JSON 和 Atom/XML。应用身份由 Apple lookup/search 资料核对，渣打官网也提供了相同的 Apple ID 链接。没有使用登录账号或 App Store Connect 私有开发者接口。

公开 RSS 地址示例：

```text
https://itunes.apple.com/hk/rss/customerreviews/page=1/id=445795688/sortBy=mostRecent/json?l=en-GB
https://itunes.apple.com/hk/rss/customerreviews/page=1/id=1164066737/sortBy=mostRecent/json?l=en-US
```

RSS 语言参数不保证正文为英文。出现空 feed 时，在香港区不变的前提下，对照 JSON/Atom XML 与页面语言参数补取；原始空响应同样保存。每家成功取得 1–10 页，每页 50 条，没有未解决的缺页。第 11 页测试为空，保存在 `probe_limit`。500 条是本次公开入口返回样本，不是应用完整历史评论数。

原始标题、正文、星级、版本、时间、显示名及投票字段完整保存；RSS 未提供的开发者回复标明缺失原因。XML 同时含纯文本和 HTML 正文时导出纯文本字段，完整 XML 不变。

语言筛选使用 langdetect 1.0.9、文字系统检查和短英文词表，综合标题与正文判断；本次人工修正了 15 条近期明确英文短评的标签，保留逐条理由与原文匹配校验。

## 证据和交付

- `english_six_months.csv` / `.json`：171 条。
- `english_as_of_2026-10-19.csv` / `.json`：469 条，含更早样本，不能称为全部英文历史。
- `all_languages_fetched.csv` / `.json`：1,000 条。
- `other_languages_or_uncertain.csv` / `.json`：未纳入英文子集的记录。
- 各应用 `raw/`：原始 HTTP 响应、请求 URL、头、状态、时间、SHA-256。
- `collection_report.json`、`verification.json`、`independent_checks.json`：统计、原始记录追溯和独立检查。
- `manual_language_review.json`：语言修正记录。

1,000 条评论均逐条核对原始响应中的 ID、标题、正文、评分和时间；导出无重复应用/评论 ID 组合，评分均为 1–5，时间倒序正确。两个样本最早日期都早于六个月起点，但只代表此入口返回的记录，不能证明所有设备和语言展示中的评论完全收录。

Apple 时间来自 RSS updated，可能包含评论编辑。评分始终保存原值；负面正文也可能带 5 星，不推断或改写用户评分。

已有 Google Play 六个月英文 140 条，加上本轮 Apple 171 条，当前四组来源合计 311 条英文评论记录；这是记录数，不是不同客户人数。

复现脚本：`scripts/collect_apple.py`。请使用新的输出目录保留本轮证据：

```powershell
.\.venv\Scripts\python.exe scripts\collect_apple.py crawl --app sc_mobile --output data\apple_2026-10-19\run_04
.\.venv\Scripts\python.exe scripts\collect_apple.py crawl --app hsbc_hk --output data\apple_2026-10-19\run_04
# 如果 crawl_summary.json 中仍有 unresolved_empty_pages，运行对应应用的 --resume 补取。
.\.venv\Scripts\python.exe scripts\collect_apple.py export --output data\apple_2026-10-19\run_04
```
