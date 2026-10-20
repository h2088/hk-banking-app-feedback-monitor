"""Build the self-contained offline Checkpoint E HTML report.

Only standard-library files are read. No network requests or external assets are
used, so the generated HTML can be opened directly in a clean browser.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "data/checkpoint_D_analysis_2026-10-19"
OUTPUT = ROOT / "report_customer_feedback_2026-10-19.html"
REPORT_FIELDS = (
    "record_key", "app_key", "review_id", "review_time_hk", "rating", "title", "text",
    "rating_sentiment", "themes", "theme_labels", "short_text_for_theme_review",
    "source_url", "raw_response_workspace_path",
)


def load_json(name):
    return json.loads((ANALYSIS / name).read_text(encoding="utf-8"))


def load_csv(name):
    with (ANALYSIS / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def pct(value):
    return f"{float(value) * 100:.2f}%"


def stars(value):
    return "★" * int(value) + "☆" * (5 - int(value))


def safe_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def build():
    report = load_json("analysis_summary.json")
    comments = load_json("comment_labels.json")
    benchmark = load_csv("overall_benchmark.csv")
    monthly = load_csv("monthly_overall_feedback.csv")
    themes = load_csv("themes_by_app.csv")
    quotes = load_csv("representative_quotes.csv")
    input_path = ROOT / report["input"]
    if hashlib.sha256(input_path.read_bytes()).hexdigest() != report["input_sha256"]:
        raise ValueError("Master data changed since Checkpoint D; refusing a stale report")
    used_artifacts = ("comment_labels.json", "overall_benchmark.csv", "monthly_overall_feedback.csv", "themes_by_app.csv", "representative_quotes.csv")
    for name in used_artifacts:
        if hashlib.sha256((ANALYSIS / name).read_bytes()).hexdigest() != report["artifact_sha256"][name]:
            raise ValueError(f"Analysis artifact changed since Checkpoint D: {name}")
    sc = next(row for row in benchmark if row["group"] == "SC Mobile")
    hsbc = next(row for row in benchmark if row["group"] == "HSBC benchmark")

    # Keep the report's benchmark labels separate from the internal keys used
    # by the analysis exports (sc_mobile / hsbc_hk).
    app_group_labels = {"sc_mobile": "SC Mobile", "hsbc_hk": "HSBC benchmark"}
    comments.sort(key=lambda row: row.get("review_time_hk") or "", reverse=True)
    latest_date = comments[0]["review_time_hk"][:10]
    short_body_count = sum(len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", row["text"])) <= 4 for row in comments)
    short_analysis_count = sum(row["short_text_for_theme_review"] for row in comments)
    # Display-only projection: do not redistribute usernames or developer
    # replies in the HTML. The immutable source files retain their metadata.
    embedded_comments = [{key: row.get(key) for key in REPORT_FIELDS} for row in comments]

    benchmark_rows = (
        f"<tr><th>评论数</th><td>{sc['review_count']}</td><td>{hsbc['review_count']}</td><td>{int(sc['review_count']) - int(hsbc['review_count']):,}</td></tr>"
        f"<tr><th>平均星级</th><td><strong>{sc['mean_rating']}</strong></td><td><strong>{hsbc['mean_rating']}</strong></td><td>{float(sc['mean_rating']) - float(hsbc['mean_rating']):+.4f}</td></tr>"
        f"<tr><th>1–2 星比例</th><td>{sc['negative_count_rating_1_2']} / {sc['review_count']} ({pct(sc['negative_rate_rating_1_2'])})</td><td>{hsbc['negative_count_rating_1_2']} / {hsbc['review_count']} ({pct(hsbc['negative_rate_rating_1_2'])})</td><td class=\"risk\">+{(float(sc['negative_rate_rating_1_2']) - float(hsbc['negative_rate_rating_1_2'])) * 100:.2f} pp</td></tr>"
        f"<tr><th>4–5 星比例</th><td>{sc['positive_count_rating_4_5']} / {sc['review_count']} ({pct(sc['positive_rate_rating_4_5'])})</td><td>{hsbc['positive_count_rating_4_5']} / {hsbc['review_count']} ({pct(hsbc['positive_rate_rating_4_5'])})</td><td class=\"risk\">{(float(sc['positive_rate_rating_4_5']) - float(hsbc['positive_rate_rating_4_5'])) * 100:+.2f} pp</td></tr>"
        f"<tr><th>1 星比例</th><td>{sc['one_star_count']} / {sc['review_count']} ({pct(sc['one_star_rate'])})</td><td>{hsbc['one_star_count']} / {hsbc['review_count']} ({pct(hsbc['one_star_rate'])})</td><td class=\"risk\">+{(float(sc['one_star_rate']) - float(hsbc['one_star_rate'])) * 100:.2f} pp</td></tr>"
    )

    rating_counts = {app_key: Counter() for app_key in app_group_labels}
    for comment in comments:
        if comment.get("app_key") in rating_counts:
            rating_counts[comment["app_key"]][int(comment["rating"])] += 1
    rating_distribution_rows = "".join(
        f"<tr><th>{label}</th>"
        + "".join(f"<td>{rating_counts[app_key][rating]}</td>" for rating in range(1, 6))
        + f"<td>{sum(rating_counts[app_key].values())}</td></tr>"
        for app_key, label in app_group_labels.items()
    )

    theme_map = {}
    for row in themes:
        display_group = app_group_labels.get(row["group"], row["group"])
        theme_map.setdefault(row["theme"], {"label": row["theme_label"]})[display_group] = row
    theme_rows = []
    for item in theme_map.values():
        s = item["SC Mobile"]
        h = item["HSBC benchmark"]
        gap = (float(s.get("theme_mention_rate", 0)) - float(h.get("theme_mention_rate", 0))) * 100
        cls = " class=\"risk\"" if gap > 5 else ""
        theme_rows.append(
            f"<tr><th>{esc(item['label'])}</th><td>{s.get('theme_mentions', 0)} ({pct(s.get('theme_mention_rate', 0))})</td><td>{h.get('theme_mentions', 0)} ({pct(h.get('theme_mention_rate', 0))})</td><td{cls}>{gap:+.2f} pp</td></tr>"
        )

    # representative_quotes is theme-oriented, so one review can occur more
    # than once. Deduplicate by review_id before showing evidence cards.
    unique_quotes = []
    seen_quote_ids = set()
    for quote in quotes:
        quote_id = quote.get("review_id") or quote.get("source_url")
        if quote_id in seen_quote_ids:
            continue
        seen_quote_ids.add(quote_id)
        unique_quotes.append(quote)
    quote_cards = []
    for quote in unique_quotes[:8]:
        quote_cards.append(
            f"<article class=\"quote\"><div><span class=\"pill\">{esc(app_group_labels.get(quote['app_key'], quote['app_key']))}</span> <span class=\"stars\">{stars(quote['rating'])}</span> <time>{esc(quote['review_time_hk'][:10])}</time></div><p>{esc(quote['text'])}</p><a href=\"{esc(quote['source_url'])}\" target=\"_blank\" rel=\"noreferrer\">打开来源核查</a></article>"
        )

    css = """
:root{--ink:#172033;--muted:#647087;--line:#e4e9f1;--bg:#f5f7fb;--card:#fff;--navy:#12335b;--blue:#2563eb;--red:#b42318}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",Arial,sans-serif}a{color:#1257b5}
header{background:linear-gradient(135deg,#102d50,#1e527e);color:#fff;padding:48px max(24px,calc((100% - 1180px)/2)) 42px}header h1{font-size:clamp(28px,4vw,46px);line-height:1.15;margin:0 0 12px}header p{max-width:820px;color:#dcecff;margin:8px 0}.eyebrow{letter-spacing:.1em;text-transform:uppercase;font-size:12px;color:#9fd5ff;font-weight:700}
nav{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid var(--line);box-shadow:0 2px 12px #12233b0d}nav .inner{max-width:1180px;margin:auto;padding:9px 24px;display:flex;gap:18px;overflow:auto;white-space:nowrap}nav a{text-decoration:none;font-size:13px;color:var(--muted);font-weight:600}
main{max-width:1180px;margin:0 auto;padding:28px 24px 70px}section{margin:0 0 42px}h2{font-size:25px;margin:0 0 8px;color:var(--navy)}h3{margin:24px 0 8px;color:var(--navy)}.lead{color:var(--muted);margin-top:0}.notice{border-left:4px solid #2e76c7;background:#eaf3ff;padding:14px 17px;border-radius:8px}.warning{border-left-color:#d98300;background:#fff6e6}
.grid{display:grid;gap:16px}.cards{grid-template-columns:repeat(4,minmax(0,1fr))}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;box-shadow:0 4px 15px #14233d08}.card .label{font-size:12px;color:var(--muted);font-weight:700}.card .value{font-size:30px;font-weight:800;margin-top:4px}.card .sub{font-size:12px;color:var(--muted)}.card.sc{border-top:4px solid #2563eb}.card.hsbc{border-top:4px solid #0f766e}.card.risk{border-top:4px solid #c2410c}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}thead th,table th{font-weight:700;color:var(--navy);background:#f1f5fa}tbody tr:last-child td,tbody tr:last-child th{border-bottom:0}.risk{color:var(--red);font-weight:700}
.chart{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px}.month-row{display:grid;grid-template-columns:62px 1fr 44px 145px;gap:10px;align-items:center;margin:10px 0}.bar{height:14px;background:#edf1f6;border-radius:99px;overflow:hidden}.bar i{display:block;height:100%;background:linear-gradient(90deg,#2869d6,#71a5ff);border-radius:99px}.month-row small{color:var(--muted);font-size:11px}.small{font-size:12px;color:var(--muted)}
.quote-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.quote{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px}.quote p{margin:9px 0;font-size:14px}.pill{background:#e7efff;color:#194d9b;border-radius:99px;padding:2px 8px;font-size:11px;font-weight:700}.stars{color:#bb7200;letter-spacing:1px}.quote time{color:var(--muted);font-size:12px}
.filters{display:flex;gap:10px;flex-wrap:wrap;background:#fff;border:1px solid var(--line);padding:14px;border-radius:10px;margin-bottom:12px}.filters input,.filters select{border:1px solid #cbd5e1;border-radius:7px;padding:9px 10px;background:#fff;color:var(--ink)}.filters input{min-width:240px;flex:1}.table-scroll{overflow-x:auto}.comment-table{font-size:13px;table-layout:fixed;min-width:1100px}.comment-table th{position:static}.comment-table th:nth-child(1){width:16%}.comment-table th:nth-child(2){width:10%}.comment-table th:nth-child(3){width:9%}.comment-table th:nth-child(4){width:6%}.comment-table th:nth-child(5){width:15%}.comment-table th:nth-child(6){width:34%}.comment-table th:nth-child(7){width:10%}.comment-table td:nth-child(1){white-space:nowrap}.comment-table .pill{display:inline-block;margin:2px 0;max-width:100%}.comment-title{font-weight:700;margin-bottom:3px}.comment-text{white-space:pre-wrap;overflow-wrap:anywhere}.comment-meta{color:var(--muted);font-size:11px;margin-top:5px;overflow-wrap:anywhere}.empty{padding:22px;text-align:center;color:var(--muted)}.pager{display:flex;gap:12px;align-items:center;justify-content:center;margin:18px 0;flex-wrap:wrap}.pager button{padding:8px 16px;background:#fff;border:1px solid #cbd5e1;border-radius:6px;color:var(--navy);cursor:pointer}.pager button:disabled{opacity:.4;cursor:default}section{scroll-margin-top:64px}.quote p{white-space:pre-wrap;overflow-wrap:anywhere}
.method{columns:2;column-gap:40px}.method li{break-inside:avoid;margin:7px 0}footer{background:#102d50;color:#dcecff;padding:26px max(24px,calc((100% - 1180px)/2));font-size:12px}footer a{color:#bfe1ff}@media(max-width:800px){.cards,.quote-grid{grid-template-columns:1fr 1fr}.month-row{grid-template-columns:48px 1fr 30px}.month-row small{display:none}.comment-table{display:block;overflow-x:auto}.method{columns:1}}@media(max-width:540px){.cards,.quote-grid{grid-template-columns:1fr}header{padding-top:32px}.card .value{font-size:25px}}
"""
    html_doc = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SC Mobile 客户反馈监测｜HSBC Benchmark</title><style>{css}</style></head><body>
<header><div class="eyebrow">Customer feedback monitoring · Checkpoint E</div><h1>SC Mobile 客户反馈监测</h1><p>以 SC Mobile Hong Kong 为主对象，以 HSBC HK Mobile Banking 为 benchmark。报告只分析应用商店客户评论，不拆分 Google Play 与 Apple App Store。</p><p>观察窗口：2026/04/19–2026/10/19（香港时间） · 英文评论 · {len(comments)} 条 · 数据截至：2026/10/19 · 样本最新评论：{latest_date}</p></header>
<nav><div class="inner"><a href="#summary">执行摘要</a><a href="#benchmark">总体比较</a><a href="#trend">月度监测</a><a href="#themes">主题反馈</a><a href="#quotes">证据评论</a><a href="#comments">评论浏览</a><a href="#method">方法与限制</a></div></nav>
<main>
<section id="summary"><h2>执行摘要</h2><p class="lead">客户反馈正文使用评论的 <strong>text</strong> 字段；Apple 的 title 只作为辅助上下文。星级是主要满意度信号，正文主题是反馈监测信号。</p>
<div class="grid cards"><div class="card sc"><div class="label">SC Mobile 平均星级</div><div class="value">{sc['mean_rating']}</div><div class="sub">{sc['review_count']} 条评论</div></div><div class="card hsbc"><div class="label">HSBC benchmark 平均星级</div><div class="value">{hsbc['mean_rating']}</div><div class="sub">{hsbc['review_count']} 条评论</div></div><div class="card risk"><div class="label">SC 1–2 星比例</div><div class="value">{pct(sc['negative_rate_rating_1_2'])}</div><div class="sub">HSBC：{pct(hsbc['negative_rate_rating_1_2'])}</div></div><div class="card"><div class="label">SC 重点反馈</div><div class="value">3 类</div><div class="sub">稳定性 · 认证 · 转账／支付</div></div></div>
<div class="notice" style="margin-top:18px"><strong>总体结论：</strong>在当前收集到的六个月英文评论样本中，SC 的反馈比 HSBC 更负面；SC 的评论更集中在稳定性、登录／认证和转账／支付等核心操作路径。结果是描述性 benchmark，不是因果或显著性结论。</div></section>
<section id="benchmark"><h2>总体 benchmark</h2><p class="lead">所有平台记录按应用合并；报告不拆分平台。百分比旁边保留评论数，避免样本量造成误读。</p><table><thead><tr><th>指标</th><th>SC Mobile</th><th>HSBC benchmark</th><th>SC − HSBC</th></tr></thead><tbody>{benchmark_rows}</tbody></table><h3>评分分布</h3><table><thead><tr><th>应用</th><th>1★</th><th>2★</th><th>3★</th><th>4★</th><th>5★</th><th>总计</th></tr></thead><tbody>{rating_distribution_rows}</tbody></table></section>
<section id="trend"><h2>月度反馈监测</h2><p class="lead">每个月显示总体评论量及 SC／HSBC 评论量；下方比例是 1–2 星占比。4 月和 10 月是部分观察月份。</p><div class="chart" id="monthlyChart"></div><p class="small">月份数据不拆分平台。未观察到的日期不等于没有评论。</p></section>
<section id="themes"><h2>主题反馈</h2><p class="lead">一条评论可以有多个主题。主题比例表示该应用评论中命中相关词／短语的评论比例，不是所有客户的问题发生率。</p><table><thead><tr><th>主题</th><th>SC Mobile</th><th>HSBC benchmark</th><th>SC − HSBC</th></tr></thead><tbody>{''.join(theme_rows)}</tbody></table><p class="small" style="margin-top:10px">规则标签用于监测和报告，不能单独证明根因。</p></section>
<section id="quotes"><h2>代表性低星评论</h2><p class="lead">以下评论用于将总体观察追溯到原文，不代表主题的全部样本，也不展示用户名。</p><div class="grid quote-grid">{''.join(quote_cards)}</div></section>
<section id="comments"><h2>评论浏览器</h2><p class="lead">可按应用、星级、星级情绪、主题和正文关键词筛选，每页 60 条，可翻页浏览全部评论。平台不作为报告筛选维度。</p><div class="filters"><input id="search" type="search" aria-label="搜索评论" placeholder="搜索评论正文、标题或主题…"><select id="appFilter" aria-label="应用"><option value="">全部应用</option><option value="sc_mobile">SC Mobile</option><option value="hsbc_hk">HSBC benchmark</option></select><select id="ratingFilter" aria-label="星级"><option value="">全部星级</option><option value="1">1 星</option><option value="2">2 星</option><option value="3">3 星</option><option value="4">4 星</option><option value="5">5 星</option></select><select id="sentimentFilter" aria-label="星级情绪"><option value="">全部星级情绪</option><option value="negative">负面（1–2 星）</option><option value="neutral">中性（3 星）</option><option value="positive">正面（4–5 星）</option></select><select id="themeFilter" aria-label="主题"><option value="">全部主题</option></select></div><div id="resultCount" class="small" aria-live="polite"></div><div class="pager"><button id="prevPage" type="button">上一页</button><span id="pageInfo"></span><button id="nextPage" type="button">下一页</button></div><div class="table-scroll"><table class="comment-table"><thead><tr><th>日期（香港时间）</th><th>应用</th><th>星级</th><th>情绪</th><th>主题</th><th>评论正文</th><th>来源</th></tr></thead><tbody id="commentRows"></tbody></table></div><div id="empty" class="empty" hidden>没有符合筛选条件的评论。</div><p class="small">来源链接可能只打开评论列表，尤其是 Apple。请结合评论 ID、日期和原文核对；“已存原始响应”链接需要保留项目内 data 文件夹。</p></section>
<section id="method"><h2>方法、限制与证据</h2><div class="notice warning"><strong>数据口径：</strong>这是 {len(comments)} 条已抓取英文评论的监测报告，不是所有客户的调查，也不是两个商店的完整历史评论。Apple 公开 RSS 每应用本轮最多 500 条；Google 是本次香港请求参数下返回的公开样本。</div><ul class="method"><li><strong>评论正文：</strong>Google 的 text；Apple 的 title + text 仅用于检索和规则匹配。</li><li><strong>情绪信号：</strong>1–2 星负面、3 星中性、4–5 星正面；文本词典仅作补充，不代表已使用独立 NLP 模型识别情绪。</li><li><strong>主题：</strong>登录／认证、转账／支付、稳定性、可用性、客服、注册、安全、费用等保守短语规则；多标签。提及主题不等于投诉。</li><li><strong>数据时间：</strong>香港时间 2026/04/19 00:00（含）至 2026/10/20 00:00（不含）；样本最新记录为 {latest_date}，不能声称已观察到 10/19 评论。</li><li><strong>月份：</strong>4 月从 19 日开始，10 月是部分观察月份；不能把缺失日期当作零评论。</li><li><strong>人工检查：</strong>Checkpoint D 记录了 10 条分层样本检查；这是小样本合理性检查，不是分类准确率评估。</li><li><strong>短评论：</strong>仅正文计词有 {short_body_count} 条不超过 4 词；加上 Apple 标题后，分析标签中的短文本标记为 {short_analysis_count} 条。两种口径不同；均不影响评论数或星级统计。</li><li><strong>对比：</strong>HSBC 是 benchmark；SC 与 HSBC 的样本量和平台构成不完全相同，结论是描述性监测。</li><li><strong>离线使用：</strong>HTML 内嵌数据、样式和脚本，单文件可浏览；外部来源核查需要联网，CSV／原始证据链接需要原项目文件。</li></ul><p>可核查文件：<a href="data/merged_2026-10-19/master_english_six_months.csv">合并分析输入 CSV</a> · <a href="data/checkpoint_D_analysis_2026-10-19/comment_labels.csv">逐条标签</a> · <a href="checkpoint_D_customer_feedback_analysis.md">Checkpoint D 方法报告</a> · 输入 SHA-256：<code>{report['input_sha256']}</code></p></section>
</main><footer>SC Mobile Customer Feedback Monitoring · HSBC benchmark · Local self-contained report · Last updated 2026-10-19</footer>
<script>
const DATA = {safe_json({'comments': embedded_comments, 'monthly': monthly})};
const PAGE_SIZE = 60;
let currentPage = 0;
const esc = value => String(value == null ? "" : value).replace(/[&<>"']/g, ch => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[ch]));
const sentimentLabel = s => s === "negative" ? "负面" : s === "neutral" ? "中性" : "正面";
function renderMonthly() {{
  const target = document.getElementById("monthlyChart");
  const max = Math.max.apply(null, DATA.monthly.map(x => Number(x.review_count)));
  target.innerHTML = DATA.monthly.map(function(x) {{
    return '<div class="month-row"><span>' + esc(x.group) + '</span><div class="bar"><i style="width:' + (Number(x.review_count) / max * 100).toFixed(1) + '%"></i></div><b>' + x.review_count + '</b><small>SC ' + x.sc_review_count + ' / HSBC ' + x.hsbc_review_count + '<br>负面 ' + (Number(x.sc_negative_rate) * 100).toFixed(0) + '% / ' + (Number(x.hsbc_negative_rate) * 100).toFixed(0) + '%</small></div>';
  }}).join("");
}}
function allThemeOptions() {{
  const values = new Map();
  DATA.comments.forEach(function(r) {{ (r.theme_labels || []).forEach(function(name, i) {{ values.set((r.themes || [])[i], name); }}); }});
  const select = document.getElementById("themeFilter");
  Array.from(values.entries()).sort(function(a,b) {{ return a[1].localeCompare(b[1]); }}).forEach(function(pair) {{
    select.insertAdjacentHTML("beforeend", '<option value="' + esc(pair[0]) + '">' + esc(pair[1]) + '</option>');
  }});
}}
function renderComments() {{
  const search = document.getElementById("search").value.trim().toLowerCase();
  const app = document.getElementById("appFilter").value;
  const rating = document.getElementById("ratingFilter").value;
  const sentiment = document.getElementById("sentimentFilter").value;
  const theme = document.getElementById("themeFilter").value;
  const filtered = DATA.comments.filter(function(r) {{
    const hay = [r.text, r.title].concat(r.theme_labels || []).join(" ").toLowerCase();
    return (!search || hay.includes(search)) && (!app || r.app_key === app) && (!rating || String(r.rating) === rating) && (!sentiment || r.rating_sentiment === sentiment) && (!theme || (r.themes || []).includes(theme));
  }});
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  currentPage = Math.max(0, Math.min(currentPage, pageCount - 1));
  const start = currentPage * PAGE_SIZE;
  const visible = filtered.slice(start, start + PAGE_SIZE);
  document.getElementById("resultCount").textContent = "显示 " + (filtered.length ? start + 1 : 0) + "–" + (start + visible.length) + " / " + filtered.length + " 条匹配评论（按时间从新到老）";
  document.getElementById("pageInfo").textContent = "第 " + (currentPage + 1) + " / " + pageCount + " 页";
  document.getElementById("prevPage").disabled = currentPage === 0;
  document.getElementById("nextPage").disabled = currentPage >= pageCount - 1;
  document.getElementById("commentRows").innerHTML = visible.map(function(r) {{
    const themeHtml = (r.theme_labels || []).map(function(x) {{ return '<span class="pill">' + esc(x) + '</span>'; }}).join(" ");
    const title = r.title ? '<div class="comment-title">' + esc(r.title) + '</div>' : "";
    const starText = "★".repeat(Number(r.rating)) + "☆".repeat(5 - Number(r.rating));
    const evidence = r.raw_response_workspace_path ? '<br><a href="' + esc(r.raw_response_workspace_path) + '" target="_blank" rel="noreferrer">已存原始响应</a>' : "";
    return '<tr data-record-key="' + esc(r.record_key) + '"><td><time datetime="' + esc(r.review_time_hk) + '">' + esc(r.review_time_hk.replace("T", " ").replace("+08:00", "")) + '</time></td><td>' + esc(r.app_key === "sc_mobile" ? "SC Mobile" : "HSBC benchmark") + '</td><td class="stars" title="' + r.rating + ' 星">' + starText + '</td><td>' + sentimentLabel(r.rating_sentiment) + '</td><td>' + (themeHtml || '<span class="small">未分类</span>') + '</td><td><div class="comment-text">' + title + esc(r.text) + '</div><div class="comment-meta">评论 ID：' + esc(r.review_id) + '<br>' + (r.short_text_for_theme_review ? "短评论，主题证据有限" : "") + '</div></td><td><a href="' + esc(r.source_url) + '" target="_blank" rel="noreferrer">来源核查</a>' + evidence + '</td></tr>';
  }}).join("");
  document.getElementById("empty").hidden = visible.length !== 0;
}}
renderMonthly(); allThemeOptions(); renderComments();
["search","appFilter","ratingFilter","sentimentFilter","themeFilter"].forEach(function(id) {{ document.getElementById(id).addEventListener("input", function() {{ currentPage = 0; renderComments(); }}); }});
document.getElementById("prevPage").addEventListener("click", function() {{ currentPage--; renderComments(); }});
document.getElementById("nextPage").addEventListener("click", function() {{ currentPage++; renderComments(); }});
</script></body></html>"""
    OUTPUT.write_text(html_doc, encoding="utf-8")
    manifest = {
        "report": OUTPUT.name,
        "report_sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "input": "data/merged_2026-10-19/master_english_six_months.json",
        "input_sha256": report["input_sha256"],
        "rows_embedded": len(comments),
        "external_network_assets": False,
        "platform_split_in_metrics": False,
        "pagination": {"page_size": 60, "all_rows_browsable": True},
        "display_names_embedded": False,
        "latest_review_date_hk": latest_date,
        "short_body_count": short_body_count,
        "short_analysis_count": short_analysis_count,
        "analysis_artifact_sha256": {name: hashlib.sha256((ANALYSIS / name).read_bytes()).hexdigest() for name in used_artifacts},
        "sections": ["summary", "benchmark", "trend", "themes", "quotes", "comments", "method"],
    }
    (ANALYSIS / "report_build_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build()
