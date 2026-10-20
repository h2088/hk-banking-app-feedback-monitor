# 合并评论总表字段说明

所有 45 列均在 Excel、CSV 和 JSON 中一致排列。原始字段逐值、逐类型保留在 JSON 中；来源没有的字段补 null。CSV 使用 UTF-8 BOM，空值为留空，对象和布尔值以 JSON 文本保存。XLSX 明确保存文本、数值和布尔类型，ID 是文本。

| 字段 | JSON 类型 | 说明 |
|---|---|---|
| platform | string | 统一平台名：Google Play / Apple App Store；新增字段 |
| bank | string | 银行：Standard Chartered / HSBC；新增字段 |
| app | string | 原始应用名称 |
| review_time_hk | ISO 8601 string | 香港时间 UTC+08:00；按对应 UNIX 时间从新到老排序 |
| rating | integer 1–5 | 来源星级，不按评论情绪调整 |
| title | string / null | Apple 原始评论标题；Google 没有标题，留空，不编造 |
| text | string | 评论正文原文；不翻译、不改写、不删除换行或表情 |
| language_status | string | english / non_english / mixed / uncertain；沿用最终语言标签 |
| within_six_month_window | boolean | 香港时间 [2026-04-19 00:00, 2026-10-20 00:00) |
| user_display_name | string / null | 来源公开显示名；不据此判断身份、语言或居住地 |
| app_key | string | 跨平台应用组：sc_mobile / hsbc_hk；新增字段 |
| app_id | string | Google 包名或 Apple 数字应用 ID，均按文本保存 |
| review_id | string | 原始评论 ID，按文本保存；不能视作跨平台用户 ID |
| record_key | string | 平台键:app_id:review_id；新增唯一键，不按相同正文跨平台去重 |
| review_time_utc | ISO 8601 string | 来源评论时间换算为 UTC，可能反映编辑时间 |
| review_timestamp_seconds | number | 原始 UNIX 秒数；排序依据，保留原始整数/浮点类型 |
| source_updated_time | string / null | Apple RSS 原始 updated 及其时区；Google 留空 |
| review_app_version | string / null | 评论对应的应用版本 |
| thumbs_up | integer / null | 仅 Google 返回的有用/点赞数量；不与 Apple 投票字段合并 |
| vote_sum | integer / null | 仅 Apple 的 im:voteSum 原始字段 |
| vote_count | integer / null | 仅 Apple 的 im:voteCount 原始字段 |
| developer_reply | string / null | Google 开发者回复；Apple RSS 未提供，空值不代表未回复 |
| reply_availability | string / null | Apple: not_exposed_by_public_rss；Google 无此原始字段，留空 |
| reply_time_hk | ISO 8601 string / null | 仅 Google 的开发者回复时间，香港时区 |
| reply_time_utc | ISO 8601 string / null | 仅 Google 的开发者回复时间，UTC |
| detected_language | string | 保留已完成的自动/人工复核语言结果，不重新检测 |
| language_method | string | 最终数据集的语言识别或人工复核方法 |
| language_probabilities | object | 原始自动识别概率；CSV/XLSX 中以 JSON 文本保存 |
| on_or_before_cutoff | boolean | 是否早于香港时间 2026-10-20 00:00；不声称存在 10/19 评论 |
| source | string | 原始来源名：Google Play / Apple App Store RSS |
| storefront | string / null | Apple 原始 storefront=hk；Google 无该字段，留空 |
| request_language | string / null | 原始数据记录的请求语言；不能视作评论语言 |
| request_country | string / null | Google 请求地区 HK；Apple 无该原始字段，留空 |
| source_url | string | 原始网站核查链接；平台可能只打开应用页而非定位单条评论 |
| feed_review_url | string / null | 仅 Apple RSS 返回的评论 related 链接 |
| collected_at_utc | ISO 8601 string | 原始抓取时间，不是本次合并时间 |
| source_dataset | string | 来源最终数据目录，相对项目根目录；新增字段 |
| source_json_file | string | 来源最终 JSON 路径，相对项目根目录；新增字段 |
| source_row_index | integer | 该评论在来源 JSON 数组中的零起始索引；新增字段 |
| raw_response_file | string | 保留来源原值；相对 source_dataset，不是相对合并目录 |
| raw_response_workspace_path | string | 无歧义的原始 HTTP 响应路径，相对项目根目录；新增字段 |
| raw_items_file | string / null | Google 原始解码 JSON 路径，相对 source_dataset |
| raw_items_workspace_path | string / null | Google 解码 JSON 路径，相对项目根目录；新增字段 |
| raw_item_index | integer / null | Google 解码评论数组中的零起始索引 |
| raw_entry_index | integer / null | Apple feed.entry 中的零起始索引 |
