"""Build a parameterized offline report; no historical findings are hardcoded."""
from __future__ import annotations

import html
import json
from pathlib import Path

from feedback_io import SKILL, load, dump, sha, require


def esc(value):
    return html.escape(str(value), quote=True)


def safe_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def table(headers, rows, identity):
    return '<table id="' + identity + '"><thead><tr>' + ''.join('<th>' + esc(v) + '</th>' for v in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + esc(v) + '</td>' for v in row) + '</tr>' for row in rows) + '</tbody></table>'


def percent(count, total):
    return f"{count} / {total} ({count/total*100:.2f}%)" if total else "0 / 0（无样本）"


def build(root, config):
    output = root / "report_customer_feedback.html"
    require(not output.exists(), "Report already exists; create a new batch to rebuild")
    analysis = load(root / "data/analysis/summary.json")
    require(sha(root / "data/merged/master_english_six_months.json") == analysis["input_sha256"], "Analysis input changed")
    for name, digest in analysis["artifact_sha256"].items():
        require(sha(root / "data/analysis" / name) == digest, f"Stale analysis: {name}")
    labels = load(root / "data/analysis/comment_labels.json")
    review = load(root / "manual_review.json")
    require(review.get("status") == "reviewed", "Read and annotate validation_sample before building; see manual_review.json")
    metrics = {m["group"]: m for m in analysis["benchmark"]}
    apps = sorted(config["apps"], key=lambda a: a["role"] != "primary")
    p, b = apps
    pm, bm = metrics[p["key"]], metrics[b["key"]]
    sizes = {a["key"]: metrics[a["key"]]["review_count"] for a in apps}
    benchmark = table(["指标", p["name"], b["name"] + "（benchmark）"], [
        ["评论数", pm["review_count"], bm["review_count"]],
        ["平均星级", f"{pm['mean_rating']:.4f}" if pm["mean_rating"] is not None else "无样本", f"{bm['mean_rating']:.4f}" if bm["mean_rating"] is not None else "无样本"],
        ["1–2 星比例", percent(pm["negative_count_rating_1_2"], pm["review_count"]), percent(bm["negative_count_rating_1_2"], bm["review_count"])],
        ["4–5 星比例", percent(pm["positive_count_rating_4_5"], pm["review_count"]), percent(bm["positive_count_rating_4_5"], bm["review_count"])],
        ["1 星比例", percent(pm["one_star_count"], pm["review_count"]), percent(bm["one_star_count"], bm["review_count"])],
    ], "benchmarkTable")
    distribution = table(["应用", "1★", "2★", "3★", "4★", "5★", "总计"], [
        [a["name"], *[sum(r["rating"] == star and r["app_key"] == a["key"] for r in labels) for star in range(1, 6)], sizes[a["key"]]] for a in apps
    ], "ratingTable")
    grouped = {name["key"]: {t["group"]: t for t in analysis["themes"] if t["theme"] == name["key"]} for name in analysis["theme_names"]}
    theme_rows = []
    for theme in analysis["theme_names"]:
        left, right = grouped[theme["key"]][p["key"]], grouped[theme["key"]][b["key"]]
        gap = ((left["theme_mentions"] / sizes[p["key"]] - right["theme_mentions"] / sizes[b["key"]]) * 100) if all(sizes.values()) else None
        theme_rows.append([theme["label"], percent(left["theme_mentions"], sizes[p["key"]]), percent(right["theme_mentions"], sizes[b["key"]]), f"{gap:+.2f} pp" if gap is not None else "无可比样本"])
    themes = table(["主题", p["name"], b["name"], "主对象 − benchmark"], theme_rows, "themeTable")
    observed_latest = labels[0]["review_time_hk"][:10] if labels else "无记录"
    primary_themes = sorted((t for t in analysis["themes"] if t["group"] == p["key"] and t["theme_mentions"] > 0), key=lambda t: -t["theme_mentions"])[:3]
    insight = "两款应用都有样本后才能比较低星比例。"
    if sizes[p["key"]] and sizes[b["key"]]:
        delta = pm["negative_count_rating_1_2"] / sizes[p["key"]] - bm["negative_count_rating_1_2"] / sizes[b["key"]]
        direction = "高于" if delta > 0 else "低于" if delta < 0 else "等于"
        insight = f"当前英文评论样本中，{p['name']} 的 1–2 星比例{direction} benchmark，差异为 {delta*100:+.2f} 个百分点。"
    insight += " 主对象提及较多的主题：" + ("、".join(t["theme_label"] for t in primary_themes) or "无可识别主题") + "。"
    quotes = []
    for row in analysis["quotes"][:8]:
        quotes.append('<article class="quote"><div>' + esc(row["app"]) + ' · ' + esc(row["review_time_hk"]) + ' · ' + str(row["rating"]) + ' 星</div><p>' + esc(row["text"]) + '</p><a target="_blank" rel="noreferrer" href="' + esc(row["source_url"]) + '">打开来源核查</a></article>')
    fields = ("record_key", "app_key", "review_id", "review_time_hk", "rating", "title", "text", "rating_sentiment", "themes", "theme_labels", "short_text_for_theme_review", "source_url", "raw_response_workspace_path")
    payload = {"apps": [{k: a[k] for k in ("key", "name", "role")} for a in apps],
        "comments": [{k: r.get(k) for k in fields} for r in labels], "monthly": analysis["monthly"], "theme_names": analysis["theme_names"]}
    script = (SKILL / "assets/report.js").read_text(encoding="utf-8").replace("__DATA__", safe_json(payload))
    css = (SKILL / "assets/report.css").read_text(encoding="utf-8")
    review_count = len(review["judgements"])
    document = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(p['name'])} 客户反馈监测</title><style>{css}</style></head><body>
<header><h1>{esc(p['name'])} 客户反馈监测</h1><p>Benchmark：{esc(b['name'])}；英文客户评论；应用总体汇总。</p><p>观察窗口：{esc(config['since'])} 至 {esc(config['as_of'])}（香港时间，含起止日期） · {len(labels)} 条 · 样本最新评论：{observed_latest}</p></header>
<nav><div class="inner"><a href="#summary">摘要</a><a href="#benchmark">总体比较</a><a href="#trend">月度监测</a><a href="#themes">主题反馈</a><a href="#quotes">证据评论</a><a href="#comments">评论浏览</a><a href="#method">方法与限制</a></div></nav><main>
<section id="summary"><h2>执行摘要</h2><div class="notice">{esc(insight)}</div><p>这是收集样本的描述性 benchmark。样本量和平台构成可能不同，不能据此证明根因、统计显著性或总体用户满意度。</p></section>
<section id="benchmark"><h2>总体 benchmark</h2><p>计数和分母按应用计算；Google Play 与 Apple 不拆分展示。</p>{benchmark}<h3>评分分布</h3>{distribution}</section>
<section id="trend"><h2>月度反馈监测</h2><p>窗口边界月份为部分观察月份；无记录表示未观察到，不能当作零反馈。</p><div id="monthlyChart" class="chart"></div></section>
<section id="themes"><h2>主题反馈</h2><p>多标签短语匹配；主题提及不等于投诉或问题发生率，比例不能相加解释为 100%。</p>{themes}</section>
<section id="quotes"><h2>代表性低星评论</h2><p>仅作证据示例，按记录唯一键去重，不表示主题全部样本。</p><div class="grid quote-grid">{''.join(quotes)}</div></section>
<section id="comments"><h2>评论浏览器</h2><p>按应用、星级、星级情绪、主题及正文／标题关键词组合筛选；每页 60 条。</p><div class="filters"><input id="search" type="search" aria-label="搜索评论" placeholder="搜索正文、标题或主题…"><select id="appFilter" aria-label="应用"><option value="">全部应用</option></select><select id="ratingFilter" aria-label="星级"><option value="">全部星级</option>{''.join(f'<option value="{n}">{n} 星</option>' for n in range(1,6))}</select><select id="sentimentFilter" aria-label="星级情绪"><option value="">全部星级情绪</option><option value="negative">负面（1–2 星）</option><option value="neutral">中性（3 星）</option><option value="positive">正面（4–5 星）</option></select><select id="themeFilter" aria-label="主题"><option value="">全部主题</option></select></div><div id="resultCount" aria-live="polite"></div><div class="pager"><button id="prevPage">上一页</button><span id="pageInfo"></span><button id="nextPage">下一页</button></div><div class="table-scroll"><table class="comment-table"><thead><tr><th>日期（香港时间）</th><th>应用</th><th>星级</th><th>情绪</th><th>主题</th><th>评论原文</th><th>来源</th></tr></thead><tbody id="commentRows"></tbody></table></div><p id="empty" class="empty" hidden>没有匹配的评论</p></section>
<section id="method"><h2>方法、限制与证据</h2><div class="notice warning">{esc(load(root / 'collection_summary.json').get('limitations','公开端点样本，不是评论全集。'))}</div><ul class="method"><li>正文使用 text；Apple title 仅作为独立上下文及规则匹配补充，不替换原文。</li><li>1–2 星负面、3 星中性、4–5 星正面；文本词典仅作补充，未声称是独立 NLP 情绪准确识别。</li><li>主题使用英文银行业务短语规则；不证明根因、严重性或业务影响。</li><li>实际检查 {review_count} 条分层样本，只是合理性抽查，不是分类准确率。</li><li>仅正文不超过 4 词有 {analysis['short_body_count']} 条；Apple 标题加正文的分析短文本标记有 {analysis['short_analysis_count']} 条。两种口径不同，均不删除。</li><li>时间窗为 {esc(analysis['window']['start'])}（含）至 {esc(analysis['window']['end_exclusive'])}（不含）；截至日期不是实际最新评论日期。</li><li>来源网页可能只打开评论列表，且内容可能后续编辑／删除。本轮是否联网核实见采集记录。</li><li>核心 HTML 可离线浏览；来源需联网，CSV／原始响应／方法文档需保留目录。</li><li>静态快照，不自动更新；社交媒体、多语言、主题逐月趋势、严重性验证、报警未实现。</li></ul><p><a href="data/merged/master_english_six_months.csv">合并输入 CSV</a> · <a href="data/analysis/comment_labels.csv">逐条标签</a> · <a href="manual_review.json">人工抽查记录</a> · <a href="collection_summary.json">来源覆盖记录</a></p></section></main><footer>Last updated {esc(config['as_of'])} · Static customer-feedback monitoring</footer><script>{script}</script></body></html>'''
    output.write_text(document, encoding="utf-8")
    dump(root / "build_manifest.json", {"report": output.name, "report_sha256": sha(output), "rows": len(labels),
        "input_sha256": analysis["input_sha256"], "manual_review_sha256": sha(root / "manual_review.json"),
        "analysis_summary_sha256": sha(root / "data/analysis/summary.json"), "config_sha256": sha(root / "config.json"),
        "external_assets": False, "platform_split": False}, exclusive=True)
