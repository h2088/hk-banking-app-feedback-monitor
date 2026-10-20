"""Reusable HK English app-review workflow, with fresh dates and immutable batches.

Python 3.10+; offline stages use only the standard library. See SKILL.md.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import shutil
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from feedback_io import (HK, SKILL, app_for, bounds, config_for, csv_write, dump,
    fingerprints, load, now, require, safe_path, sha, six_months_before,
    sorted_rows, validate_row, xlsx_write)
from theme_rules import THEMES, classify, metrics, normalized, theme_metrics, word_count


def text_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def initialize(args):
    root = args.root.resolve()
    require(not root.exists() or not any(root.iterdir()), "Choose an empty/new batch directory")
    as_of = date.fromisoformat(args.as_of) if args.as_of else datetime.now(HK).date()
    since = date.fromisoformat(args.since) if args.since else six_months_before(as_of)
    apps = load(args.apps or SKILL / "assets/apps.json")
    config = {"schema_version": 1, "since": since.isoformat(), "as_of": as_of.isoformat(),
        "country": "HK", "timezone": "Asia/Hong_Kong", "language": "english", "platform_split": False,
        "all_history": False, "google_max_pages": 100, "apple_max_pages": 10, "pause_seconds": 0.9,
        "apps": apps, "language_overrides": []}
    dump(root / "config.json", config, exclusive=True)
    config_for(root)
    text_file(root / "plan.md", f"""# Customer-feedback workflow

窗口：{since} 至 {as_of}，香港时间，含起止日期。仅英文客户评论；主对象对比 benchmark，按应用汇总。

- A：核对应用 ID、公开来源、真实可达性、窗口与边界。
- B：保存原始响应／请求参数／采集时间；或声明导入已有快照；按实际返回记录计数。
- C：合并、日期／身份／缺失／重复／语言／来源证据 QA。
- D：星级映射情绪、补充文本词典、11 类银行主题、多标签、分层人工阅读检查。
- E：离线 HTML、完整翻页和组合筛选；静态数值检查与真实浏览器交互检查。
- F：事实、限制、哈希、交付文档复核；只在实际完成的范围内标记完成。

每阶段状态以 checkpoint 文件及 JSON 证据为准；初始化不代表任何阶段通过。
社交媒体、多语言、主题逐月趋势、事件严重性、生产监测／报警不是此引擎已实现功能。
""")
    print(json.dumps({"batch": str(root), "config": config}, ensure_ascii=False, indent=2))


def import_snapshot(root, config, args):
    require(not (root / "source_records.json").exists() and not (root / "data/raw").exists(), "Batch input already started")
    source = args.input.resolve()
    evidence_root = args.evidence_root.resolve()
    require(source.suffix.lower() == ".json", "Normalized JSON required; map other schemas explicitly before importing")
    originals = load(source)
    require(isinstance(originals, list) and originals, "Import needs non-empty row array")
    rows, copied = copy.deepcopy(originals), {}
    for index, row in enumerate(rows):
        for field in ("raw_response_workspace_path", "raw_items_workspace_path"):
            value = row.get(field)
            if not value:
                continue
            original = safe_path(evidence_root, value)
            require(original.is_file(), f"Missing imported evidence: {value}")
            digest = sha(original)
            target = root / "data/raw/imported" / (digest + original.suffix)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copyfile(original, target)
            require(sha(target) == digest, "Copied evidence hash mismatch")
            row["origin_" + field] = value
            row[field] = target.relative_to(root).as_posix()
            copied[row[field]] = digest
        row["origin_input_row"] = index
        validate_row(row, config, root)
    dump(root / "source_records.json", rows, exclusive=True)
    dump(root / "collection_summary.json", {"status": "imported", "mode": "offline_snapshot",
        "input_filename": source.name, "input_sha256": sha(source), "input_rows": len(rows),
        "raw_evidence_sha256": copied, "live_source_validation_performed": False,
        "limitations": args.coverage_note or "导入已有快照；未重新访问来源，覆盖范围仅为所提供文件。Apple 公共 RSS 和 Google 返回样本均不能宣称是评论全集。"}, exclusive=True)
    checkpoint_a(root, config, "导入已存快照，未声称本轮验证来源实时可达性。")


def checkpoint_a(root, config, statement):
    lines = ["# Checkpoint A — 来源可行性与身份", "", statement, ""]
    for app in config["apps"]:
        lines.extend([f"- {app['name']}（{app['role']}）：Google `{app['google_id']}`；Apple `{app['apple_id']}`。",
            f"  Google：https://play.google.com/store/apps/details?id={app['google_id']}&gl=HK",
            f"  Apple：https://apps.apple.com/hk/app/{app['apple_slug']}/id{app['apple_id']}"])
    lines.extend(["", "来源覆盖、返回页数、错误与停止原因见 [collection_summary.json](collection_summary.json)。",
        "请求语言不是作者语言；香港 storefront 参数不是用户居住地证明。社交媒体未纳入。", ""])
    text_file(root / "checkpoint_A_source_feasibility.md", "\n".join(lines))


def prepare(root, config):
    output = root / "data/merged"
    require(not output.exists(), "Merged batch already exists")
    source_hash = sha(root / "source_records.json")
    rows = copy.deepcopy(load(root / "source_records.json"))
    by_key = {row["record_key"]: row for row in rows}
    require(len(by_key) == len(rows), "Duplicate record identity; investigate without silently deleting")
    applied = []
    for override in config["language_overrides"]:
        row = by_key[override["record_key"]]
        require(row.get("title") == override.get("expected_title") and row["text"] == override["expected_text"], "Language override source mismatch")
        require(override.get("reason") and override.get("reviewer") and override.get("reviewed_at"), "Language correction needs actual review provenance")
        require(override["status"] in {"english", "non_english", "mixed", "uncertain"}, "Invalid override status")
        applied.append({"record_key": row["record_key"], "previous_status": row["language_status"], **override})
        row.update(language_status=override["status"], detected_language=override["language"], language_method="manual_review:" + override["reviewed_at"])
    start, end = bounds(config)
    for row in rows:
        validate_row(row, config, root)
        row["within_six_month_window"] = start.timestamp() <= row["review_timestamp_seconds"] < end.timestamp()
        row["on_or_before_cutoff"] = row["review_timestamp_seconds"] < end.timestamp()
    rows = sorted_rows(rows)
    subsets = {"master_all_reviews": rows,
        "master_english_all": [r for r in rows if r["language_status"] == "english" and r["on_or_before_cutoff"]],
        "master_six_months_all": [r for r in rows if r["within_six_month_window"]],
        "master_english_six_months": [r for r in rows if r["language_status"] == "english" and r["within_six_month_window"]]}
    require(subsets["master_english_six_months"], "No English in-window records; report actual gap, do not generate invented results")
    output.mkdir(parents=True)
    for name, subset in subsets.items():
        dump(output / (name + ".json"), subset)
        csv_write(output / (name + ".csv"), subset, list(rows[0]))
    xlsx_write(output / "reviews_master.xlsx", {"English_window": subsets["master_english_six_months"], "All_fetched": rows,
        "Field_notes": [{"field": key, "note": "Preserved source or documented derived value; see schema reference"} for key in rows[0]]})
    dump(output / "manual_language_review.json", applied)
    manifest = {"source_sha256": source_hash, "config_sha256": sha(root / "config.json"), "counts": {k: len(v) for k, v in subsets.items()},
        "window_start": start.isoformat(), "window_end_exclusive": end.isoformat(),
        "latest_all_languages": rows[0]["review_time_hk"], "latest_english_window": subsets["master_english_six_months"][0]["review_time_hk"],
        "artifact_sha256": {p.name: sha(p) for p in output.iterdir() if p.is_file()}}
    require(sha(root / "source_records.json") == source_hash, "Source changed")
    dump(output / "merge_manifest.json", manifest)
    text_file(root / "checkpoint_B_data_collection.md", f"""# Checkpoint B — 数据采集／导入与合并

本批输入：{len(rows)} 条；窗口内所有语言 {len(subsets['master_six_months_all'])} 条；英文分析 {len(subsets['master_english_six_months'])} 条。
窗口：{start.isoformat()}（含）至 {end.isoformat()}（不含）。
全语言最新 {manifest['latest_all_languages']}；英文窗口最新 {manifest['latest_english_window']}。截至日期不代表该日存在评论。

原始响应在 data/raw，source_records.json 是本批不可变输入；合并／语言修订为派生产物。
语言标签可错；手动修订需精确匹配原文并记录理由。应用身份、原文、星级保留。
来源覆盖与停止原因见 [collection_summary.json](collection_summary.json)，哈希见 [merge_manifest.json](data/merged/merge_manifest.json)。
""")


def qa(root, config):
    output = root / "data/qa"
    require(not output.exists(), "QA already exists")
    rows = load(root / "data/merged/master_english_six_months.json")
    keys = [r["record_key"] for r in rows]
    require(len(keys) == len(set(keys)), "Duplicate IDs")
    require(rows == sorted_rows(rows), "Not newest-first")
    text_counts = Counter(normalized(r["text"]) for r in rows)
    results = []
    for row in rows:
        validate_row(row, config, root, require_english=True)
        results.append({**row, "analysis_eligible": True, "is_duplicate": False,
            "normalized_text_duplicate_count": text_counts[normalized(row["text"])],
            "normalized_text_sha256": hashlib.sha256(normalized(row["text"]).encode()).hexdigest(),
            "word_count_body": word_count(row["text"]), "short_body": word_count(row["text"]) <= 4})
    coverage = []
    for (platform, app, month, rating), count in sorted(Counter((r["platform"], r["app_key"], r["review_time_hk"][:7], r["rating"]) for r in rows).items()):
        coverage.append({"platform": platform, "app_key": app, "month_hk": month, "rating": rating, "count": count})
    output.mkdir()
    dump(output / "rows.json", results)
    csv_write(output / "rows.csv", results)
    csv_write(output / "coverage_by_source_app_month_rating.csv", coverage)
    summary = {"rows": len(rows), "analysis_eligible": len(results), "short_body_count": sum(r["short_body"] for r in results),
        "repeated_text_groups": sum(n > 1 for n in text_counts.values()), "repeated_text_rows": sum(n for n in text_counts.values() if n > 1),
        "input_sha256": sha(root / "data/merged/master_english_six_months.json"),
        "artifact_sha256": {p.name: sha(p) for p in output.iterdir() if p.is_file()}}
    dump(output / "summary.json", summary)
    text_file(root / "checkpoint_C_data_qa.md", f"""# Checkpoint C — 数据质量

检查 {len(rows)} 条，全部通过身份、日期、语言标签、字段、星级、唯一键与来源文件存在性检查；未删除评论。
正文不超过 4 词：{summary['short_body_count']} 条；重复措辞组 {summary['repeated_text_groups']} 个，覆盖 {summary['repeated_text_rows']} 条，ID 不同即保留。
这不是语言识别准确率或来源实时可见性验证。平台分层只在 QA 证据中保留，最终报告按应用汇总。
明细：[QA summary](data/qa/summary.json) · [覆盖表](data/qa/coverage_by_source_app_month_rating.csv)。
""")


def analyze(root, config):
    output = root / "data/analysis"
    require(not output.exists(), "Analysis already exists")
    qa_summary = load(root / "data/qa/summary.json")
    input_file = root / "data/merged/master_english_six_months.json"
    require(sha(input_file) == qa_summary["input_sha256"], "Input changed since QA")
    source = load(input_file)
    labels = [{**row, **classify(row)} for row in source]
    benchmark = [metrics([r for r in labels if r["app_key"] == a["key"]], a["key"]) for a in config["apps"]]
    themes = []
    for app in config["apps"]:
        themes.extend(theme_metrics([r for r in labels if r["app_key"] == app["key"]], app["key"]))
    monthly = []
    for month in sorted({r["review_time_hk"][:7] for r in labels}):
        part = [r for r in labels if r["review_time_hk"].startswith(month)]
        monthly.append({"month": month, "review_count": len(part), "apps": {
            a["key"]: metrics([r for r in part if r["app_key"] == a["key"]], a["key"]) for a in config["apps"]}})
    quotes, seen = [], set()
    for theme in THEMES:
        for app in config["apps"]:
            part = [r for r in labels if r["app_key"] == app["key"] and theme in r["themes"] and r["rating"] <= 2]
            if part:
                row = min(part, key=lambda r: (r["rating"], -r["review_timestamp_seconds"]))
                if row["record_key"] not in seen:
                    quotes.append({k: row[k] for k in ("record_key", "app", "app_key", "review_id", "review_time_hk", "rating", "text", "title", "source_url")})
                    seen.add(row["record_key"])
    sample = []
    for app in config["apps"]:
        for rating in range(1, 6):
            row = next((r for r in labels if r["app_key"] == app["key"] and r["rating"] == rating), None)
            if row:
                sample.append({k: row[k] for k in ("record_key", "app_key", "review_time_hk", "title", "text", "rating", "rating_sentiment", "themes", "theme_labels")})
                sample[-1]["fingerprint"] = fingerprints(row)
    output.mkdir()
    artifacts = {"comment_labels": labels, "overall_benchmark": benchmark, "themes_by_app": themes,
        "monthly_overall_feedback": monthly, "representative_quotes": quotes, "validation_sample": sample}
    for name, value in artifacts.items():
        dump(output / (name + ".json"), value)
        csv_write(output / (name + ".csv"), value)
    dump(output / "summary.json", {"input_sha256": sha(input_file), "rows": len(labels), "benchmark": benchmark,
        "themes": themes, "theme_names": [{"key": key, "label": label} for key, (label, _) in THEMES.items()],
        "monthly": monthly, "quotes": quotes, "short_body_count": qa_summary["short_body_count"],
        "short_analysis_count": sum(r["short_text_for_theme_review"] for r in labels),
        "window": {"start": bounds(config)[0].isoformat(), "end_exclusive": bounds(config)[1].isoformat()},
        "artifact_sha256": {p.name: sha(p) for p in output.iterdir() if p.is_file()}})
    dump(root / "manual_review.json", {"status": "pending", "reviewer": None, "reviewed_at": None,
        "sample_sha256": sha(output / "validation_sample.json"), "judgements": [
            {"record_key": row["record_key"], "fingerprint": row["fingerprint"], "rating_assessment": None,
             "theme_assessment": None, "notes": None} for row in sample]}, exclusive=True)
    text_file(root / "checkpoint_D_customer_feedback_analysis.md", f"""# Checkpoint D — 分析与人工合理性抽查

已生成 {len(labels)} 条逐条标签、应用总体对比、月度计数／低星占比和 {len(THEMES)} 个主题。
情绪主体为 1–2 星负面、3 星中性、4–5 星正面；正文词典为补充。主题多标签，提及不是投诉。
正文／标题保留原值；Apple 标题仅补充规则匹配和检索。不作根因、因果、显著性或全体客户外推。

样本选择：每应用 × 已有星级取最新一条，共 {len(sample)} 条。只按该分层抽取，不代表覆盖所有月份或平台。
必须实际阅读 [validation_sample.json](data/analysis/validation_sample.json) 再填写 [manual_review.json](manual_review.json)。
人工状态以 JSON 为准；生成样本不等于已经人工检查，更不等于分类准确率测试。
若发现实质规则错误，修正 Skill／规则后用新批次重新计算，不得只改网页或旧标签。
""")


def validate_review(root):
    review = load(root / "manual_review.json")
    sample = load(root / "data/analysis/validation_sample.json")
    require(review["status"] == "reviewed" and review.get("reviewer") and review.get("reviewed_at"), "Manual review still pending")
    require(review["sample_sha256"] == sha(root / "data/analysis/validation_sample.json"), "Reviewed sample changed")
    judgements = {j["record_key"]: j for j in review["judgements"]}
    require(len(judgements) == len(review["judgements"]) == len(sample), "Review keys are missing or duplicated")
    for row in sample:
        judgement = judgements[row["record_key"]]
        require(judgement["fingerprint"] == row["fingerprint"], "Review fingerprint mismatch")
        require(judgement["rating_assessment"] in {"plausible", "disagreement_noted"}, "Rating review requires resolution")
        require(judgement["theme_assessment"] in {"plausible", "insufficient_text", "limitation_noted"}, "Theme review requires resolution")
        require(isinstance(judgement["notes"], str) and judgement["notes"].strip(), "Actual reading notes required")
    return review


def finalize(root, config):
    from verify_report import verify
    verify(root, config)
    browser = load(root / "browser_test_results.json")
    report_hash = sha(root / "report_customer_feedback.html")
    require(browser["report_sha256"] == report_hash and browser["successful"] is True, "Browser verification missing/stale/failed")
    validate_review(root)
    checks = load(root / "static_test_results.json")
    require(checks["successful"], "Integrity tests failed")
    n = load(root / "data/analysis/summary.json")["rows"]
    text_file(root / "checkpoint_E_build_test.md", f"""# Checkpoint E — 离线报告构建与测试

评论 {n} 条全部内嵌；每页 60 条，按时间从新到老；应用／星级／星级情绪／主题／关键词可组合筛选。
静态检查 {checks['checks_run']} 组通过；浏览器断言 {browser['checks_run']} 项通过。
浏览器：{browser['browser']}；测试模式：本地文件、全新无界面 profile。
SHA-256：`{report_hash}`。
检查范围以 JSON 为准，不是分类准确率验证，也不代表所有浏览器或手机都已验证。
""")
    text_file(root / "checkpoint_F_final_review.md", f"""# Checkpoint F — 最终复核

当前范围完成：英文客户评论、主对象对比 benchmark、跨商店总体汇总、静态离线报告。
{n} 条评论；日期、指标、主题及来源证据完整性已核对，人工抽查状态已检查，浏览器结果与本 HTML 哈希一致。
这是基于保存样本的描述性监测原型，不是全量客户调查、因果分析或自动监控服务。

保留限制：公开端点样本不完整；语言规则可错；主题包含正中负提及；小样本人工阅读不代表准确率；
边界月份不完整、来源构成及样本量不均衡。来源网页可能不能定位单条评论。
社交媒体、多语言、主题逐月趋势、严重性验证、自动报警未实现。
导入快照时没有重新采集；采集模式的当前来源状态见 collection_summary.json。

HTML SHA-256：`{report_hash}`。复核结果见 [final_manifest.json](final_manifest.json)。
只完成本地交付，没有对外发布或发送。
""")
    text_file(root / "handover.md", f"""# 交接说明

双击 [report_customer_feedback.html](report_customer_feedback.html) 即可离线浏览 {n} 条英文评论、趋势和 benchmark。
窗口：{config['since']} 至 {config['as_of']}（香港时间，含起止日期）；实际最新评论以页面为准。

核查顺序：总体比较 → 主题反馈 → 评论浏览。评论按时间从新到老，60 条一页。
记下评论 ID／日期／星级／原文，用“来源核查”联网比对；网页可能只打开评论列表。
“已存原始响应”对应采集快照，可用文本编辑器查找评论 ID；Google 内容可能为转义 RPC，Apple 为 JSON／XML。
CSV 在 data/merged 和 data/analysis；精确保留类型请使用同名 JSON。

只分享 HTML 可看核心内容；如需 CSV／方法／原始响应链接，保留本批完整目录结构。无需分享 Python 虚拟环境。
HTML 不内嵌用户名；原始数据可能含公开显示名和开发者回复，完整证据包不是默认已脱敏公开资料。
静态快照不自动更新。下一轮创建新批次，重新 QA／分析／人工阅读／构建／测试。
""")
    manifest = {"status": "complete_for_declared_scope", "reviewed_at_utc": now(), "report_sha256": report_hash,
        "scope": "English customer comments, overall app benchmark", "external_submission": False,
        "files": {p.relative_to(root).as_posix(): sha(p) for p in root.rglob("*") if p.is_file() and ".cache" not in p.relative_to(root).parts}}
    dump(root / "final_manifest.json", manifest, exclusive=True)
    print(json.dumps({"status": manifest["status"], "root": str(root), "report_sha256": report_hash}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "collect", "import", "prepare", "qa", "analyze", "review-status", "build", "verify", "browser-test", "finalize"])
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--since")
    parser.add_argument("--as-of")
    parser.add_argument("--apps", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--coverage-note")
    parser.add_argument("--browser", type=Path)
    args = parser.parse_args()
    if args.command == "init":
        initialize(args)
        return
    root = args.root.resolve()
    config = config_for(root)
    if args.command == "collect":
        from collect_reviews import collect
        collect(root, config)
        checkpoint_a(root, config, "本轮已访问官方来源并保存响应；见逐源采集结果。可访问不等于历史覆盖完整。")
    elif args.command == "import":
        require(args.input is not None and args.evidence_root is not None, "import requires --input and --evidence-root")
        import_snapshot(root, config, args)
    elif args.command == "prepare":
        prepare(root, config)
    elif args.command == "qa":
        qa(root, config)
    elif args.command == "analyze":
        analyze(root, config)
    elif args.command == "review-status":
        review = validate_review(root)
        print(json.dumps({"status": "reviewed", "rows": len(review["judgements"])}, ensure_ascii=False))
    elif args.command == "build":
        from build_report import build
        validate_review(root)
        build(root, config)
    elif args.command == "verify":
        from verify_report import verify
        verify(root, config)
    elif args.command == "browser-test":
        from browser_check import run
        run(root, args.browser)
    elif args.command == "finalize":
        finalize(root, config)


if __name__ == "__main__":
    main()
