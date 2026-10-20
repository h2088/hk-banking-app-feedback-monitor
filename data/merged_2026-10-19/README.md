# Google Play + Apple 合并评论总表

首选打开 `reviews_master.xlsx`：含汇总说明、全部评论、英文全部、近六月全部、近六月英文、字段说明六个工作表。所有评论表均有标题筛选、首行冻结和正文自动换行。每行是一条评论，不是一个独立用户。

| 文件（均有 CSV 和 JSON） | 范围 | 条数 |
|---|---|---:|
| `master_all_reviews` | 全部已抓取记录，含所有语言及更早记录 | 5,278 |
| `master_english_all` | 英文、截至 2026/10/19，含更早记录 | 4,071 |
| `master_six_months_all` | 近六个月，所有语言 | 528 |
| `master_english_six_months` | 近六个月英文，建议用于当前项目分析 | 311 |

## 应用和平台计数

| 平台 | 应用 | 全部 | 英文全部 | 近六月全部 | 近六月英文 |
|---|---|---:|---:|---:|---:|
| Google Play | SC Mobile Hong Kong | 1051 | 882 | 53 | 48 |
| Google Play | HSBC HK Mobile Banking | 3227 | 2720 | 99 | 92 |
| Apple App Store | SC Mobile Hong Kong | 500 | 261 | 108 | 50 |
| Apple App Store | HSBC HK Mobile Banking | 500 | 208 | 268 | 121 |

## 口径与核查

- 时间窗：香港时间 **2026/04/19 00:00（含）至 2026/10/20 00:00（不含）**。按数值时间戳倒序；同秒按唯一键升序。不代表最新一条恰好发布于 10/19。
- 仅使用 Google `run_03_full_history` 和 Apple `run_03` 两份最终数据，不混入试抓、中间版本或其他地区。原始采集文件未修改，也没有重新抓取或重新做语言识别。
- 按 `record_key = 平台键:app_id:review_id` 检查唯一性，不按相同正文跨平台合并，不做跨平台用户身份推断。Apple 标题与正文分开；来源星级、换行、拼写、表情及已人工修正的语言标签均保留。
- `source_json_file` + `source_row_index` 定位原始导出记录；`raw_response_workspace_path` 从项目根目录定位 HTTP 原始响应。`raw_response_file` 原值仍相对 `source_dataset`。不要将其误作相对本合并目录。
- `source_url` 可用于网站核查；`raw_item_index` / `raw_entry_index` 用于原始响应内核查。网站展示可能更新、排序不同或无法直接定位单条。
- Apple 香港 RSS 每应用仅取得 10 页、共 500 条；并非完整历史。Google 也只代表本次请求参数下返回的公开记录。不能据此把没抓到的时间段解释为没有评论。
- Apple RSS 不暴露开发者回复，空值不代表银行从未回复。Google 点赞与 Apple 投票分别保存，不直接视作相同指标。
- 英文子集严格匹配此前两个平台的最终英文导出；历史语言分类主要自动完成，仍有误判可能。评论日期可能是编辑时间。
- 推荐直接使用 XLSX：所有用户文本均为文本单元格，不执行公式。CSV 为保留原文没有加防公式前缀；若用 Excel 导入 CSV，请将评论、标题、显示名等用户内容列设为文本。JSON 保留完整类型和 null/空字符串区别，适合后续分析程序。
- `merge_report.json` 记录输入/输出 SHA-256、计数和检查结果。导出后逐值验证全部 JSON/CSV、XLSX 每个数据单元格、日期窗口、排序、唯一键、证据文件存在性及原始字段未改动。

重新生成到新目录（仅标准库，无需联网或安装）：

```powershell
.\.venv\Scripts\python.exe scripts\merge_reviews.py --output data\merged_2026-10-19_rerun
```

脚本拒绝覆盖非空输出目录。
