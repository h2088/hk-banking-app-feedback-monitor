# Apple 评论字段说明

CSV 为 UTF-8 BOM；相同文件名的 JSON 保留数字、布尔值、对象及 null 类型。

| 字段 | 类型 | 含义 |
|---|---|---|
| source / storefront | string | Apple App Store RSS；香港区 hk |
| app / app_id | string | 应用名与 Apple 数字 ID |
| review_id | string | 来源评论 ID，与 app_id 共同用于去重 |
| review_time_hk / review_time_utc | ISO 8601 string | 来源时间转换成香港时间与 UTC |
| source_updated_time | string | RSS 原始 updated 值，保留来源时区，可能是编辑时间 |
| review_timestamp_seconds | number | 由来源时间计算的 UNIX 秒，排序依据 |
| title / text | string | 评论标题与正文，分别保存，不翻译、不改写 |
| rating | integer, 1–5 | 原始评论星级；不按文本情绪修正 |
| user_display_name | string / null | 来源公开显示名，不据此推断身份、语言或所在地 |
| review_app_version | string / null | RSS im:version 的应用版本 |
| vote_sum / vote_count | integer / null | RSS im:voteSum / im:voteCount 的原始投票字段，不等同于银行用户数 |
| developer_reply | null | 此公开 RSS 未提供回复正文 |
| reply_availability | string | not_exposed_by_public_rss，标明缺失原因 |
| detected_language / language_status | string | 派生语言判断：english、non_english、mixed、uncertain |
| language_method | string | 自动识别、文字系统判断、短词表或人工复核 |
| language_probabilities | object | 自动模型输出；人工修正时保留原模型输出用于追溯 |
| within_six_month_window | boolean | 是否在香港时间 2026/04/19 00:00 至 2026/10/20 00:00（后者不含） |
| on_or_before_cutoff | boolean | 是否早于香港时间 2026/10/20 00:00 |
| source_url | string | 香港区应用评论页核查链接，不保证定位单条评论 |
| feed_review_url | string / null | RSS 中该评论提供的 related 链接 |
| collected_at_utc | string | 获取该页时记录的请求时间 |
| raw_response_file | string | 相对最终数据目录的原始响应路径 |
| raw_entry_index | integer | 该评论在解析后的 feed.entry 数组中零起始索引 |

`.body` 文件保留原始响应字节；同名 `.http.json` 保存请求参数、状态、时间、响应头和 SHA-256。XML 可能同时包含纯文本与 HTML 正文，导出选择 type=text 的正文；原始 XML 两个版本均保留。所有导出 CSV/JSON 按来源评论时间倒序排列，原始响应保持收到时的原样。
