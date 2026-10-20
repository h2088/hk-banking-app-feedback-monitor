# 导出字段与数据类型

CSV 单元格中的空值对应 JSON 的 null；JSON 保留数字、布尔值和对象类型。CSV 使用 UTF-8 BOM，适合 Windows Excel。

| 字段 | JSON 类型 | 含义 |
|---|---|---|
| app / app_id | string | 应用名称与 Google Play 包名 |
| review_id | string | Google 返回的评论 ID，与 app_id 共同用于去重 |
| review_time_hk / review_time_utc | string, ISO 8601 | 返回的评论时间，分别为香港时间与 UTC；可能反映评论编辑时间 |
| review_timestamp_seconds | number | Google 原始 UNIX 时间戳秒数，导出排序依据 |
| rating | integer, 1–5 | 该条评论的星级，不是商店当前平均分 |
| text | string | Google 接口返回的评论正文，保留拼写、换行、表情等；没有由采集脚本翻译或改写 |
| user_display_name | string / null | 来源公开显示名，不推断真实身份 |
| thumbs_up | integer / null | 来源返回的有用/点赞数量 |
| review_app_version | string / null | 评论所关联的应用版本，不保证每条都有 |
| developer_reply | string / null | 开发者回复正文，不是用户评论 |
| reply_time_hk / reply_time_utc | string / null | 回复时间，与用户评论时间分开保存 |
| detected_language | string | 派生语言标签，不是 Google 验证的用户语言 |
| language_status | string | english、non_english、mixed 或 uncertain |
| language_method | string | 自动检测、短英文词表、文字系统判断，或本次人工复核 |
| language_probabilities | object | 自动检测原始概率；人工修正时仍保留原始模型输出以便追溯 |
| within_six_month_window | boolean | 是否位于香港时间 2026/04/19 00:00:00 至 2026/10/20 00:00:00（后者不含） |
| on_or_before_cutoff | boolean | 评论时间是否早于香港时间 2026/10/20 00:00:00 |
| source | string | Google Play |
| request_language / request_country | string | 请求页面语言 en 或 en-US，地区 HK；不证明作者所在地 |
| source_url | string | 包含应用 ID、语言、地区、reviewId 的核查链接；平台可能只打开应用页 |
| collected_at_utc | string | 取得该页响应时记录的请求时间 |
| raw_response_file | string | 相对最终数据目录的原始 HTTP 响应文件路径 |
| raw_items_file / raw_item_index | string / integer | 解码后的 RPC JSON 路径，以及其中评论数组的零起始索引 |

原始 `.body` 文件保存响应字节；`.http.json` 保存请求 URL、请求体、状态、响应头、时间和 SHA-256；`.decoded.json` 保存解码后的 RPC 数组，含接口原始字段和分页 token。

最近六个月的初次自动分类中，有 18 条明确英文短评被误分。人工修正只修改派生语言标签，逐条核对应用 ID 和完整原文。修正清单及原因见最终数据目录 `manual_language_review.json`。中文、混合语言、纯表情，以及无法可靠判定语言的短评保留在其他语言文件中。
