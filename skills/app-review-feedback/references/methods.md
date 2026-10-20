# 数据和分析方法

## 行级数据约定

原始响应是来源证据，`source_records.json` 是批次标准化输入。JSON 是精确类型版本；CSV 为 UTF-8 BOM，数组／对象序列化为 JSON，空值为空单元格；XLSX 使用明确文本／数字／布尔单元格，ID 不转数字，评论不执行公式。CSV 的原文不加防公式前缀，因此在电子表格中核查不可信评论时优先使用类型明确的 XLSX。

| 字段 | 约定 |
|---|---|
| platform | `Google Play` 或 `Apple App Store`，保留溯源，HTML 不按平台分析 |
| app_key, app, app_id, bank | 配置键、应用名、来源 ID、所属银行；同一应用在两个来源的 app_id 不同 |
| review_id | 来源评论 ID，字符串 |
| record_key | `google_play:<package>:<review_id>` 或 `apple:<numeric_app_id>:<review_id>` |
| text, title | 原始正文字符串；Google title 可为 null；不翻译或改写原文 |
| rating | 原始整数 1–5 |
| review_timestamp_seconds | 有限 Unix 秒数，用于过滤和排序 |
| review_time_utc, review_time_hk | 带偏移 ISO 时间，必须表示与秒数相同的时刻；HK 为 +08:00 |
| source_url | HTTPS 商店链接，必须包含对应应用 ID；Apple 链接通常只到列表 |
| collected_at_utc | 原采集 UTC 时间；导入时间不可伪装成采集时间 |
| raw_response_workspace_path | 相对批次目录的实际来源文件，必须存在且不能逃出目录 |
| raw_items_workspace_path | 可选 Google decoded 文件，相对路径 |
| raw_item_index / raw_entry_index | Google item／Apple entry 在来源页的索引（从 0 开始） |
| detected_language, language_status | 识别语言；状态为 english／non_english／mixed／uncertain |
| language_method, language_probabilities | 短词／字形／langdetect／手工修订方法与分数，保留不确定性 |
| developer_reply 等 | 保留来源提供的回复、版本、点赞／投票等可选元数据；不混入正文分析 |

导入保留额外来源字段；raw 路径迁移后增加 `origin_raw_*`，增加 `origin_input_row`。不同来源不强行补造相同元数据。当前引擎要求非空正文；遇来源只有标题／无正文时会拒绝进入分析，应记录例外并明确适配，不能编造正文。

字段语义与原项目一致；原项目的固定 45 列不是新脚本的固定列数承诺。引擎校验 ID、字段类型、时间一致性、来源域名／应用 ID 和文件存在性；它不靠文件存在就证明评论真实，核查时应在 raw 中按评论 ID 找到对应文本和评分。原始 Google response 可为转义 RPC，先用 `source_utils.parse_rpc` 解码；Apple 用 `apple_parser.parse_feed` 处理 JSON／Atom。

## 时间、样本与语言

窗口按香港时间 `[since 00:00, as_of 次日00:00)`；默认往前六个日历月，在月末按目标月最后一天截齐。截止日前保留从最新往旧页取回的样本。用户截止日可能没有评论，分别报告全部已取回记录的最新评论和英文窗口的最新评论。

联网采集在 Apple 标题加正文／Google 正文上做语言识别：先看 CJK 等字形，至少 3 个拉丁词且含 CJK 标 mixed；短英文白名单可直接接受；不足 10 个拉丁字母的短 ASCII 文本标 uncertain；其余 `langdetect==1.0.9` 固定 seed=0，最高语言分数 ≥0.80 才定 english／non_english，否则 uncertain。分数不是已经校准的正确率，短文本和混合语言会误判。

人工语言修订写入 config 的 `language_overrides`：

```json
{
  "record_key": "apple:445795688:EXAMPLE",
  "expected_title": "原始标题或 null",
  "expected_text": "必须逐字相同的原始正文",
  "status": "english",
  "language": "en",
  "reason": "实际阅读后的理由",
  "reviewer": "实际检查者／agent",
  "reviewed_at": "本轮实际日期"
}
```

默认保留短评：正文不超过 4 个英文词记录 `short_body`；主题分析使用 Apple 标题加正文，另记 `short_text_for_theme_review`，两者不能混用。相同措辞而 ID 不同不去重，统计对象是评论记录，不是独立客户。

## 情绪与主题

主体情绪 `rating_sentiment`：1–2 星 negative、3 星 neutral、4–5 星 positive。这是来源星级代理，可以与文字不同。补充词典在标题加正文上匹配正负短语，命中数量差形成 `text_sentiment_rule`，不处理完整的讽刺、否定和语境，不能宣传为 NLP 准确情绪识别。具体正负词和主题短语以 `scripts/theme_rules.py` 为准，规则源代码可直接审阅。

11 个银行主题：

| key | 含义 |
|---|---|
| app_stability_performance | 稳定性、崩溃、性能、连接／加载 |
| login_authentication_access | 登录、密码、认证、OTP、生物识别、访问 |
| transfers_payments_cards | 转账、付款、交易、卡片 |
| usability_navigation_design | 易用性、导航、界面、设计 |
| customer_support_service | 客服、支持、服务 |
| account_registration | 账户、注册、开户 |
| balance_statements_history | 余额、账单、历史记录 |
| security_fraud_trust | 安全、隐私、欺诈、信任 |
| language_localization | 语言、本地化 |
| fees_rates | 费用、汇率 |
| feature_request | 功能建议、需求 |

规则为多标签匹配，未命中保留 unclassified；`primary_theme` 是规则列表中首个命中，不是已经判断出的最严重问题。宽泛词可能误命中，例如 notification 可能与认证无关、FX 广告可能不是费用投诉；没命中也不表示没问题。改为其他行业应更换主题体系并重新验证。

## 统计口径和证据

- 平均星级 = 星级总和 / 本应用记录数。低星比例 = 1–2 星数 / 本应用记录数。比较差异用百分点，分母为零显示无样本。
- 主题提及率 = 本主题记录数 / 本应用全部记录数；主题内低星比例 = 本主题低星数 / 本主题记录数。不要把两个分母互换。多主题可重叠，提及率之和不需为 100%。
- 月度为香港月份桶，输出总体数量和每应用数量／低星比例。边界月份不完整，无观察不能视为总体真实零反馈；当前引擎没有主题逐月趋势。
- 示例评论从每主题 × 应用的低星记录选择星级最低、同星级最新者，按唯一键去重；HTML 最多展示前 8 个，完整列表另存。不是随机样本，也不是所有主题的代表性证明。
- 阅读检查按每应用 × 已有星级选最新一条。样本文件 SHA 和逐条指纹绑定正文、标题、ID、星级、时间；每批重新阅读。不代表所有月份／平台均覆盖，更不是独立标注集准确率评估。

结论限定为“本批收集到的英文评论样本中”。不能推出全部客户满意度、银行总体服务质量、真实故障发生率、因果或统计显著性。版本更新、根因、事件严重性及业务损失需额外证据。
