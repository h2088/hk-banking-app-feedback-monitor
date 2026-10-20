"""Compare this saved Skill replay with the original project, without reclassifying.

Uses only Python's standard library and never writes to the original project
artifacts or installed Skill. Run after browser-test and before finalize.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


BATCH = Path(__file__).resolve().parent
PROJECT = BATCH.parent.parent
SKILL = Path(r"C:\Users\1\.codex\skills\app-review-feedback")
OLD_MERGED = PROJECT / "data/merged_2026-10-19"
OLD_ANALYSIS = PROJECT / "data/checkpoint_D_analysis_2026-10-19"
OLD_QA = PROJECT / "data/checkpoint_C_qa_2026-10-19"
checks: list[dict] = []
metric_rows: list[dict] = []


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(name, passed, **detail):
    checks.append({"name": name, "passed": bool(passed), **detail})


def csv_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def metrics(rows):
    """Independent arithmetic over original labels; no Skill functions used."""
    n = len(rows)
    low = sum(r["rating"] <= 2 for r in rows)
    high = sum(r["rating"] >= 4 for r in rows)
    one = sum(r["rating"] == 1 for r in rows)
    text_negative = sum(r["text_sentiment_rule"] == "negative" for r in rows)
    return {
        "review_count": n,
        "mean_rating": round(sum(r["rating"] for r in rows) / n, 4) if n else None,
        "negative_count_rating_1_2": low,
        "negative_rate_rating_1_2": round(low / n, 6) if n else None,
        "positive_count_rating_4_5": high,
        "positive_rate_rating_4_5": round(high / n, 6) if n else None,
        "one_star_count": one,
        "one_star_rate": round(one / n, 6) if n else None,
        "text_negative_rule_count": text_negative,
        "text_negative_rule_rate": round(text_negative / n, 6) if n else None,
        "short_text_count": sum(r["short_text_for_theme_review"] for r in rows),
    }


def main():
    config = read(BATCH / "config.json")
    check("fixed_scope", config["since"] == "2026-04-19"
          and config["as_of"] == "2026-10-19"
          and config["language"] == "english" and not config["platform_split"],
          mode="offline_snapshot_replay", config=config)

    subset_results = []
    raw_pairs = set()
    original_keys = set()
    new_keys = set()
    for stem in ("master_all_reviews", "master_english_all", "master_six_months_all",
                 "master_english_six_months"):
        old = read(OLD_MERGED / f"{stem}.json")
        new = read(BATCH / f"data/merged/{stem}.json")
        old_map = {r["record_key"]: r for r in old}
        new_map = {r["record_key"]: r for r in new}
        differences = []
        field_checks = 0
        for key, left in old_map.items():
            right = new_map.get(key)
            if right is None:
                differences.append({"record_key": key, "missing": True})
                continue
            original_keys.update(left)
            new_keys.update(right)
            for field, value in left.items():
                actual_field = ("origin_" + field if field in (
                    "raw_response_workspace_path", "raw_items_workspace_path") else field)
                actual = right.get(actual_field)
                field_checks += 1
                if actual != value:
                    differences.append({"record_key": key, "field": field,
                                        "original": value, "replay": actual})
            for field in ("raw_response_workspace_path", "raw_items_workspace_path"):
                if left.get(field):
                    raw_pairs.add((left[field], right[field]))
        same_order = [r["record_key"] for r in old] == [r["record_key"] for r in new]
        result = {
            "subset": stem, "original_rows": len(old), "replay_rows": len(new),
            "unique_original_ids": len(old_map), "unique_replay_ids": len(new_map),
            "same_record_set": set(old_map) == set(new_map),
            "same_order": same_order, "original_fields_compared": field_checks,
            "field_mismatches": differences,
            "original_sha256": sha(OLD_MERGED / f"{stem}.json"),
            "replay_sha256": sha(BATCH / f"data/merged/{stem}.json"),
        }
        subset_results.append(result)
        check(f"merged:{stem}", set(old_map) == set(new_map) and same_order
              and not differences and len(old_map) == len(old) == len(new), **result)

    raw_results = []
    for old_path, new_path in sorted(raw_pairs):
        old_hash = sha(PROJECT / old_path)
        new_hash = sha(BATCH / new_path)
        raw_results.append({"original": old_path, "replay": new_path,
                            "original_sha256": old_hash, "replay_sha256": new_hash,
                            "matched": old_hash == new_hash})
    check("raw_evidence_content", all(r["matched"] for r in raw_results),
          original_paths_checked=len(raw_results),
          unique_replay_files=len({r["replay"] for r in raw_results}), files=raw_results)

    old_labels = read(OLD_ANALYSIS / "comment_labels.json")
    new_labels = read(BATCH / "data/analysis/comment_labels.json")
    new_by_id = {r["record_key"]: r for r in new_labels}
    derived_fields = sorted(set(old_labels[0]) - original_keys)
    label_differences = [
        {"record_key": r["record_key"], "field": field,
         "original": r[field], "replay": new_by_id[r["record_key"]].get(field)}
        for r in old_labels for field in derived_fields
        if r[field] != new_by_id[r["record_key"]].get(field)
    ]
    check("all_comment_labels", not label_differences and len(new_labels) == len(old_labels),
          rows=len(old_labels), fields=derived_fields,
          field_comparisons=len(old_labels) * len(derived_fields),
          mismatches=label_differences)

    old_qa = read(OLD_QA / "english_six_months_qa.json")
    new_qa = {r["record_key"]: r for r in read(BATCH / "data/qa/rows.json")}
    qa_fields = {"is_duplicate": "is_duplicate", "analysis_eligible": "analysis_eligible",
                 "normalized_text_sha256": "normalized_text_sha256",
                 "normalized_text_duplicate_count": "normalized_text_duplicate_count",
                 "word_count": "word_count_body",
                 "is_short_text_for_theme_review": "short_body"}
    qa_differences = [
        {"record_key": r["record_key"], "field": field}
        for r in old_qa for field, new_field in qa_fields.items()
        if r[field] != new_qa[r["record_key"]][new_field]
    ]
    duplicate_flags_match = all(
        r["is_normalized_text_duplicate"] == (
            new_qa[r["record_key"]]["normalized_text_duplicate_count"] > 1)
        for r in old_qa)
    check("window_qa_rows", not qa_differences and duplicate_flags_match,
          rows=len(old_qa), field_mapping=qa_fields, mismatches=qa_differences)
    old_qa_summary = read(OLD_QA / "qa_summary.json")
    new_qa_summary = read(BATCH / "data/qa/summary.json")
    qa_summary_mapping = {
        "rows_checked": "rows", "rows_analysis_eligible": "analysis_eligible",
        "short_text_for_theme_review_rows": "short_body_count",
        "normalized_text_duplicate_groups_analysis_sample": "repeated_text_groups",
        "normalized_text_duplicate_rows_analysis_sample": "repeated_text_rows",
    }
    qa_values = {k: {"original": old_qa_summary[k], "replay": new_qa_summary[v]}
                 for k, v in qa_summary_mapping.items()}
    check("window_qa_summary", all(v["original"] == v["replay"] for v in qa_values.values()),
          values=qa_values,
          scope="311-row window only; original full-history QA has a broader scope")

    old_benchmark = read(OLD_ANALYSIS / "overall_benchmark.json")
    new_benchmark = read(BATCH / "data/analysis/overall_benchmark.json")
    name_map = {"SC Mobile": "sc_mobile", "HSBC benchmark": "hsbc_hk"}
    for left in old_benchmark[:2]:
        app = name_map[left["group"]]
        right = next(r for r in new_benchmark if r["group"] == app)
        expected = metrics([r for r in old_labels if r["app_key"] == app])
        for field, value in expected.items():
            metric_rows.append({"group": app, "metric": field, "original": left[field],
                                "independently_recalculated": value, "replay": right[field],
                                "matched": left[field] == value == right[field]})
        check(f"benchmark:{app}", all(left[k] == v == right[k] for k, v in expected.items()),
              independently_recalculated=expected)
    old_delta = old_benchmark[2]
    new_bench_map = {r["group"]: r for r in new_benchmark}
    delta = {k: round(new_bench_map["sc_mobile"][k] - new_bench_map["hsbc_hk"][k], 6)
             for k in old_delta if k != "group"}
    check("benchmark_difference", all(old_delta[k] == v for k, v in delta.items()), values=delta)

    old_themes = {(r["group"], r["theme"]): r
                  for r in csv_rows(OLD_ANALYSIS / "themes_by_app.csv")}
    new_themes = {(r["group"], r["theme"]): r
                  for r in csv_rows(BATCH / "data/analysis/themes_by_app.csv")}
    check("all_theme_metrics", old_themes == new_themes, app_theme_rows=len(old_themes),
          fields_per_row=len(next(iter(old_themes.values()))),
          mismatched_keys=[list(k) for k in set(old_themes) | set(new_themes)
                           if old_themes.get(k) != new_themes.get(k)])

    old_months = read(OLD_ANALYSIS / "analysis_summary.json")["monthly_metrics"]
    new_months = {r["month"]: r for r in read(BATCH / "data/analysis/monthly_overall_feedback.json")}
    monthly_results = []
    for left in old_months:
        month = left["group"]
        right = new_months[month]
        actual = {}
        for app, prefix in (("sc_mobile", "sc"), ("hsbc_hk", "hsbc")):
            expected = metrics([r for r in old_labels if r["app_key"] == app
                                and r["review_time_hk"].startswith(month)])
            actual[app] = all(right["apps"][app][k] == v for k, v in expected.items())
            actual[prefix + "_count"] = left[prefix + "_review_count"] == expected["review_count"]
            actual[prefix + "_rate"] = left[prefix + "_negative_rate"] == expected["negative_rate_rating_1_2"]
        actual["total"] = left["review_count"] == right["review_count"]
        monthly_results.append({"month": month, "review_count": right["review_count"], **actual})
    check("all_monthly_metrics", len(new_months) == len(old_months)
          and all(all(v for k, v in r.items() if k not in ("month", "review_count"))
                  for r in monthly_results), months=monthly_results)

    old_quotes = csv_rows(OLD_ANALYSIS / "representative_quotes.csv")
    new_quotes = read(BATCH / "data/analysis/representative_quotes.json")
    quote_key = lambda r: (r["app_key"], r["review_id"])
    old_quote_ids = {quote_key(r) for r in old_quotes}
    new_quote_map = {quote_key(r): r for r in new_quotes}
    quote_fields = ("app_key", "app", "rating", "review_time_hk", "text", "source_url", "review_id")
    quote_contents_equal = all(
        quote_key(r) in new_quote_map
        and all(str(r[f]) == str(new_quote_map[quote_key(r)][f]) for f in quote_fields)
        for r in old_quotes)
    quote_detail = {"original_rows": len(old_quotes), "original_unique_reviews": len(old_quote_ids),
                    "replay_rows": len(new_quotes),
                    "same_unique_review_set": old_quote_ids == set(new_quote_map),
                    "same_original_comment_fields": quote_contents_equal,
                    "explanation": "Skill deduplicates representative quotes by record_key; original repeated reviews under different themes."}
    check("representative_quote_semantics", old_quote_ids == set(new_quote_map)
          and len(new_quote_map) == len(new_quotes) and quote_contents_equal, **quote_detail)

    old_sample = csv_rows(OLD_ANALYSIS / "validation_sample.csv")
    new_sample = read(BATCH / "data/analysis/validation_sample.json")
    old_sample_ids = [r["record_key"] for r in old_sample]
    new_sample_ids = [r["record_key"] for r in new_sample]
    sample_order_equal = old_sample_ids == new_sample_ids
    check("validation_sample_identity", set(old_sample_ids) == set(new_sample_ids)
          and len(old_sample_ids) == len(new_sample_ids) == len(set(new_sample_ids)),
          rows=len(new_sample), same_record_set=set(old_sample_ids) == set(new_sample_ids),
          same_order=sample_order_equal,
          explanation="Original sample is newest first; Skill sample is grouped by app then rating. The 311-row analysis dataset remains newest first.")
    review = read(BATCH / "manual_review.json")
    check("fresh_sample_review", review["status"] == "reviewed", status=review["status"],
          limitation="Agent spot-check of 10 comments, not an independent human-labeled accuracy set")

    package = read(PROJECT / "dist/app-review-feedback.manifest.json")
    skill_files = {name: {"expected": digest, "actual": sha(SKILL / name)}
                   for name, digest in package["file_sha256"].items()}
    check("installed_skill_matches_package", all(v["actual"] == v["expected"]
          for v in skill_files.values()), installed_path=str(SKILL),
          files_checked=len(skill_files), files=skill_files)

    old_audit = read(PROJECT / "data/checkpoint_F_review_2026-10-19/final_review_results.json")
    protected = {**old_audit["verified_hashes"], **old_audit["delivery_file_sha256_at_review"],
                 **old_audit["raw_evidence_sha256_at_review"]}
    protected_results = {name: sha(PROJECT / name) == digest for name, digest in protected.items()}
    check("original_project_unchanged", all(protected_results.values()),
          files_checked=len(protected_results), files=protected_results)

    report_hash = sha(BATCH / "report_customer_feedback.html")
    static = read(BATCH / "static_test_results.json")
    browser = read(BATCH / "browser_test_results.json")
    check("fresh_report_validation", static["successful"] and browser["successful"]
          and static["report_sha256"] == browser["report_sha256"] == report_hash,
          static_groups=static["checks_run"], browser_assertions=browser["checks_run"],
          report_sha256=report_hash,
          screenshots=[{"file": r["file"], "sha256": sha(BATCH / r["file"])}
                       for r in browser["screenshots"]],
          visual_review="Agent inspected overview, themes, comments screenshots")

    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "successful": all(c["passed"] for c in checks),
        "mode": "same-input offline snapshot replay, no live collection",
        "skill_path": str(SKILL), "batch_path": str(BATCH),
        "checks_run": len(checks), "checks": checks,
        "original_field_count": len(original_keys), "replay_field_count": len(new_keys),
        "added_provenance_fields": sorted(new_keys - original_keys),
        "normalization": "Only evidence paths relocate. Compare original paths with origin_* fields and compare actual evidence file hashes. All other original fields compare exactly, without rounding or dropping comments.",
        "expected_differences": {
            "representative_quotes": quote_detail,
            "html": {"original_sha256": old_audit["report_sha256"],
                     "replay_sha256": report_hash, "byte_identical": old_audit["report_sha256"] == report_hash,
                     "reason": "Reusable report template, evidence paths and manual review notes differ."},
            "data_files": "Added provenance and relocated raw evidence paths change CSV/JSON/workbook bytes; source comment values and labels are compared semantically above.",
            "qa_schema": "Equivalent window QA fields have renamed columns; original full-history QA is outside the new window QA scope.",
            "monthly_schema": "Skill stores app-level monthly metrics in nested JSON and CSV; compare equivalent monthly counts and rates plus independently recalculated app metrics.",
            "validation_sample_order": {"same_record_set": set(old_sample_ids) == set(new_sample_ids),
                                        "same_order": sample_order_equal,
                                        "reason": "Original sample is newest first; Skill groups the same ten comments by app and rating."},
        },
        "limits": ["No fresh crawling or current website validation.",
                   "Original language labels are reused; language detection is not rerun.",
                   "Deterministic rule reproducibility does not establish sentiment/theme accuracy.",
                   "The 10-comment spot-check is performed by the agent, not an independent annotator.",
                   "Original store sampling/coverage limitations remain."],
    }
    (BATCH / "reproduction_comparison.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (BATCH / "metric_comparison.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(metric_rows[0]))
        writer.writeheader()
        writer.writerows(metric_rows)

    status = "通过" if result["successful"] else "存在未通过项，详见 JSON"
    lines = [
        "# app-review-feedback Skill 复现对照报告", "",
        f"本批复现验证：**{status}**。实际调用已安装 Skill 的执行入口，保存到独立批次目录；原项目文件保留。", "",
        "## 验证范围", "",
        "采用原项目保存的 5,278 条全量快照及关联原始响应，按相同口径重新合并、质检、分类、生成报告与验证。",
        "观察窗口为 2026-04-19 至 2026-10-19（香港时间，含截止日）；只分析英文评论，SC Mobile 为主对象，HSBC 为 benchmark，Google Play 与 Apple 合并报告。",
        "本轮为离线快照复现；未重新联网采集，沿用原始语言识别结果。A/B 文档记录的是导入快照及其覆盖限制。", "",
        "## 一致性结果", "",
        "| 对照项 | 原项目 | 本次 Skill | 结果 |", "|---|---:|---:|---|",
    ]
    for r in subset_results:
        passed = r["same_record_set"] and r["same_order"] and not r["field_mismatches"]
        lines.append(f"| {r['subset']} | {r['original_rows']:,} | {r['replay_rows']:,} | {'一致' if passed else '有差异'} |")
    lines += [
        f"| 逐条分类 | {len(old_labels)} 条 × {len(derived_fields)} 个派生字段 | 同左 | {'一致' if not label_differences else '有差异'} |",
        f"| 银行 × 主题统计 | {len(old_themes)} 行 | {len(new_themes)} 行 | {'一致' if old_themes == new_themes else '有差异'} |",
        f"| 月度统计 | {len(old_months)} 个月 | {len(new_months)} 个月 | 见逐项检查 |", "",
        f"逐条核对全部 {len(original_keys)} 个原始字段。两列原始证据路径因批次迁移，使用 origin_* 回溯列比较原路径，并核对 {len(raw_results)} 个原始路径的文件内容 SHA-256；其余字段直接精确比较。",
        "近六个月 QA 仍为：311 条可分析，105 条短正文，5 组 / 20 条重复标准化文本；重复文本保留，未按正文删除。", "",
        "| 指标 | SC Mobile | HSBC benchmark |", "|---|---:|---:|",
    ]
    for field, label, formatter in (
        ("review_count", "评论数", lambda v: str(v)),
        ("mean_rating", "平均星级", lambda v: f"{v:.4f}"),
        ("negative_count_rating_1_2", "1–2 星评论数", lambda v: str(v)),
        ("negative_rate_rating_1_2", "1–2 星比例", lambda v: f"{v:.2%}"),
        ("positive_count_rating_4_5", "4–5 星评论数", lambda v: str(v)),
    ):
        lines.append(f"| {label} | {formatter(new_bench_map['sc_mobile'][field])} | {formatter(new_bench_map['hsbc_hk'][field])} |")
    lines += [
        "", "原数据、重新计算值与本次输出的逐指标对照保存在 [metric_comparison.csv](metric_comparison.csv)。",
        "星级情绪、补充文本规则、主题、主主题、匹配词计数、分析文本等全部派生字段均逐条比较；这验证规则运行一致性，不代表分类准确率达到 100%。", "",
        "## 已解释的差异", "",
        f"- 代表性评论：原表 {len(old_quotes)} 行，涉及 {len(old_quote_ids)} 条不同评论；本批去重为 {len(new_quotes)} 条。评论集合与原文字段一致性见 JSON 的 representative_quote_semantics，统计样本仍是 311 条。",
        f"- 原总表 {len(original_keys)} 列，本批 {len(new_keys)} 列：新增来源回溯字段 {', '.join(sorted(new_keys - original_keys))}。两列 raw_*_workspace_path 指向批次内保存的证据副本。",
        "- CSV/JSON/Excel 的字节与哈希随来源字段变化；HTML 使用 Skill 的通用模板，代表评论去重、复核备注及证据路径也不同，因此不声称文件逐字节相同。",
        "- QA 的部分等价字段改名；原项目同时做过全历史 QA，本批 QA 聚焦 311 条分析窗口。月度 JSON 结构也不同，已比较对应月度数值。", "",
        "- 10 条复核样本的评论集合相同，排列方式不同：原表按时间从新到老，Skill 按应用及星级排列复核样本。311 条分析总表及网页评论仍按时间从新到老。", "",
        "## 新批验证与保存结果", "",
        f"- 静态检查 {static['checks_run']} 组；浏览器检查 {browser['checks_run']:,} 项。通过状态及报告哈希见下方机器记录。",
        "- 10 条验证样本已重新逐条阅读并保存备注；这是代理抽查，不是独立人工标注集。",
        f"- 核对原项目 {len(protected_results)} 个受审计文件是否仍与原 Checkpoint F 哈希相同，并核对已安装 Skill 的 {len(skill_files)} 个文件与打包清单是否相同。",
        "- 三张截图已保存并查看：[概览](screenshots/overview.png)、[主题](screenshots/themes.png)、[评论浏览](screenshots/comments.png)。", "",
        "[离线 HTML 报告](report_customer_feedback.html) · [英文总表 CSV](data/merged/master_english_six_months.csv) · [Excel 总表](data/merged/reviews_master.xlsx) · [逐条分类 CSV](data/analysis/comment_labels.csv)", "",
        "[机器对照记录（含逐文件哈希）](reproduction_comparison.json) · [静态验证](static_test_results.json) · [浏览器验证](browser_test_results.json) · [本批复核记录](manual_review.json) · [执行步骤](replay_commands.ps1)", "",
        "## 逐项对照状态", "",
    ]
    lines.extend(f"- {'通过' if c['passed'] else '未通过'}：{c['name']}" for c in checks)
    lines += ["", "原样本的公开接口覆盖限制继续适用。本轮没有新增网站核验或重新识别语言，也未通过独立标注集评价主题/情绪准确率。", ""]
    (BATCH / "reproduction_comparison.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"successful": result["successful"], "checks_run": len(checks),
                      "failed": [c["name"] for c in checks if not c["passed"]],
                      "raw_files": len(raw_results), "quote_difference": quote_detail,
                      "original_project_files": len(protected_results)}, ensure_ascii=False, indent=2))
    return 0 if result["successful"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
