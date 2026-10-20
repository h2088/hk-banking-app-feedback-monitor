# Google Play 英文评论抓取结果（截至 2026/10/19）

最终结果目录：`data/google_play_2026-10-19/run_03_full_history/`。

打开 [离线评论核查网页](data/google_play_2026-10-19/run_03_full_history/review_browser.html)，默认显示 2026/04/19–2026/10/19 的英文评论，按时间从新到老。可以按应用、星级和关键词筛选；取消六个月筛选后可看本次取回的更早英文历史记录。

| 应用 | 取回历史记录（不同 ID） | 英文历史记录 | 六个月内全部返回记录 | 六个月内英文 | 最新英文评论（香港时间） |
|---|---:|---:|---:|---:|---|
| SC Mobile Hong Kong | 1,051 | 882 | 53 | 48 | 2026/10/16 09:25:03 |
| HSBC HK Mobile Banking | 3,227 | 2,720 | 99 | 92 | 2026/10/15 02:39:51 |
| 合计 | 4,278 | 3,602 | 152 | 140 | — |

历史英文识别主要为自动分类；近六个月额外复核了初次被排除的记录，修正了 18 条明确英文短评。其他 12 条保留在全部数据中，未纳入六个月英文子集。

## 来源与翻页结果

- 渣打使用 `hl=en-US`；汇丰使用 `hl=en`；两者均使用 `gl=HK` 和最新排序 `sort=2`。
- 渣打 6 页，最后一页 51 条；汇丰 17 页，最后一页 27 条。两者均因接口不再提供下一页 token 而停止，没有达到 500 页安全上限。
- 渣打最早返回记录为香港时间 2013/09/06，汇丰为 2016/10/26。
- 交换 en/en-US 后对照每家最新 200 条，ID、正文、评分、时间及顺序一致；这 400 条不重复计数。
- 2026/10/19 是用户指定的日期上限。本次未观测到该日评论，不会把较早评论改写成该日期。
- 上述数字只描述当前公开入口、页面语言和地区设置下取回的数据，不代表已证明覆盖平台所有语言、地区和设备的全部评论。

## 数据文件

- `english_six_months.csv` / `.json`：140 条，适合当前项目分析。
- `english_as_of_2026-10-19.csv` / `.json`：3,602 条，含更早英文历史。
- `all_languages_fetched.csv` / `.json`：4,278 条全部已取回记录。
- `other_languages_or_uncertain.csv` / `.json`：未纳入英文子集的记录。
- `sc_mobile/raw/`、`hsbc_hk/raw/`：原始 HTTP 响应、解码后 RPC 数组、请求参数和 SHA-256。
- `collection_report.json`：每家样本数、时间范围和分页情况。
- `verification.json`：4,278 条逐条追溯到原始响应的检查结果。
- `independent_checks.json`：排序、日期边界、网页内嵌数据、JS 语法及英语页面参数对照检查。
- `manual_language_review.json`：18 条语言标签修正及理由，评论正文未修改。

CSV 为 UTF-8 BOM，适合 Windows Excel。字段类型与含义见 [数据字典](data/google_play_2026-10-19/data_dictionary.md)。

## 原文示例

以下均保持来源拼写，没有翻译或改写。完整记录含来源链接、review ID 和原始响应位置。

| 应用 | 香港时间 | 用户公开显示名 | 星级 | 评论原文 |
|---|---|---|---:|---|
| SC Mobile Hong Kong | 2026/10/16 09:25:03 | Patrick Wong | 1 | the app force closed unexpectedly after the update, can't even manage anything. please fix ASAP |
| HSBC HK Mobile Banking | 2026/10/15 02:39:51 | dunn c | 1 | poor verification process |
| SC Mobile Hong Kong | 2026/10/13 18:45:02 | Ricky Kam | 1 | Crashing after latest update |
| HSBC HK Mobile Banking | 2026/10/10 22:58:06 | TW Gerrard | 5 | Both services, systems and app are the best. |

## 验证与复现

检查结果：4,278 个应用/评论 ID 组合唯一；23 页评论原始 HTTP 可解码回导出证据；25 个原始响应文件的 SHA-256 一致；缺失日期 0；非法评分 0；导出倒序正确。

核查平台时打开来源链接，选择全部评论并切换为 Newest。平台可能只打开应用主页而不会定位 reviewId，可以通过显示名、日期和原文关键词查找。浏览器地区、语言、设备及评论后续编辑/删除会影响显示。

脚本及锁定版本依赖：`scripts/collect_google_play.py`、`requirements-scraping.txt`。再次采集请使用新的输出目录，以保留本轮证据：

```powershell
.\.venv\Scripts\python.exe scripts\collect_google_play.py crawl --app sc_mobile --all-history --output data\google_play_2026-10-19\run_04
.\.venv\Scripts\python.exe scripts\collect_google_play.py crawl --app hsbc_hk --all-history --output data\google_play_2026-10-19\run_04
.\.venv\Scripts\python.exe scripts\collect_google_play.py export --output data\google_play_2026-10-19\run_04
```

时间来自 Google 返回的 UNIX 秒，显式转换为 UTC 与香港时间；可能是更新后的评论时间，不能据此独立推断首次发表时间。页面汇总评分与评分人数是当前快照，未冒充本轮已抓取评论数量。
