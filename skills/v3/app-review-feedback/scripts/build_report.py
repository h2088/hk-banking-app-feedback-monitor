"""English offline report and workbook with configurable banks and dates."""
import html
import json
from feedback_io import SKILL, dump, load, require, sha, xlsx_write
from bilingual_rules import THEMES
from run_feedback import STORES, guard, note, validate_review


def safe_json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def build(root, config):
    guard(root)
    validate_review(root)
    require(not (root / "report_customer_feedback.html").exists(), "Report exists; use a new batch")
    summary = load(root / "data/analysis/summary.json")
    for name, digest in summary["files"].items():
        require(sha(root / name) == digest, "Stale analysis: " + name)
    rows = load(root / "data/analysis/comment_labels.json")
    apps = sorted(config["apps"], key=lambda a: a["role"] != "primary")
    data = dict(config=config, apps=[{k:a[k] for k in ("key", "name", "role")} for a in apps], summary=summary,
        collection=load(root / "collection_summary.json"), coverage=load(root / "data/qa/coverage.json"), theme_names={k:v[0] for k,v in THEMES.items()})
    for key, name in (("groups", "store_benchmarks"), ("themes", "themes_by_store_bank"), ("monthly", "monthly_by_store_bank"), ("monthly_totals", "monthly_feedback_monitoring"), ("deltas", "benchmark_deltas")):
        data[key] = load(root / ("data/analysis/" + name + ".json"))
    fields = ["record_key", "platform", "app_key", "app", "rating", "title", "text", "review_time_hk", "review_timestamp_seconds", "source_url", "rating_sentiment", "themes", "theme_labels"]
    data["rows"] = [{k:r.get(k) for k in fields} for r in rows]
    template = (SKILL / "assets/report.html").read_text(encoding="utf-8")
    tokens = dict(__PRIMARY__=apps[0]["name"], __BANK_SCOPE__=apps[0]["name"] + " compared with " + ", ".join(a["name"] for a in apps[1:]) + ", separately for each app store.", __WINDOW__=config["since"] + " through " + config["as_of"])
    for key, value in tokens.items():
        template = template.replace(key, html.escape(value))
    template = template.replace("__BANK_HEADERS__", "".join("<th>" + html.escape(a["name"]) + "</th>" for a in apps))
    report = root / "report_customer_feedback.html"
    report.write_text(template.replace("__PAYLOAD__", safe_json(data)), encoding="utf-8")
    xlsx_write(root / "data/reviews_master.xlsx", {"Google Play reviews":[r for r in rows if r["platform"] == STORES[0]], "Apple App Store reviews":[r for r in rows if r["platform"] == STORES[1]],
        "Bank store metrics":data["groups"], "Benchmark deltas":data["deltas"], "Topics by store":data["themes"], "Monthly by bank and store":data["monthly"], "Monthly feedback monitoring":data["monthly_totals"], "Coverage":data["coverage"]})
    note(root, "methodology.md", (SKILL / "references/methods.md").read_text(encoding="utf-8"))
    table = "| Store | Bank | Reviews | Mean rating | 1–2 star share |\n|---|---|---:|---:|---:|\n"
    for g in data["groups"]:
        mean = "N/A" if g["mean_rating"] is None else f"{g['mean_rating']:.2f}"
        rate = "N/A" if g["negative_rate_rating_1_2"] is None else f"{100*g['negative_rate_rating_1_2']:.1f}%"
        table += f"| {g['platform']} | {g['app']} | {g['review_count']} | {mean} | {rate} |\n"
    differences = []
    for d in data["deltas"]:
        gap = d["low_star_rate_difference_percentage_points"]
        wording = "not comparable (empty sample)" if gap is None else f"{gap:+.1f} percentage points in 1–2 star share (primary minus benchmark)"
        differences.append(f"- {d['platform']}, {d['primary']} vs {d['benchmark']}: {wording}.")
    priorities = []
    for store in STORES:
        topics = sorted((t for t in data["themes"] if t["platform"] == store and t["app_key"] == apps[0]["key"]), key=lambda t:(-t["theme_negative_count"],-t["theme_mentions"]))[:3]
        priorities.append("- " + store + ": " + "; ".join(f"{t['theme_label']} ({t['theme_mentions']} mentions; {t['theme_negative_count']} low-star)" for t in topics) + ".")
    note(root, "executive_summary.md", f"""# Banking app customer feedback

{len(rows):,} combined English/Chinese review records, {config['since']} through {config['as_of']} inclusive HKT. {apps[0]['name']} is the primary bank; {', '.join(a['name'] for a in apps[1:])} are benchmarks. Google Play and Apple App Store have separate denominators. Review language is eligibility metadata, not a performance dimension.

{table}
{chr(10).join(differences)}

Primary-bank topics with the most low-star mentions:

{chr(10).join(priorities)}

Use source comments to investigate candidate journeys, then check release/device data, telemetry and support cases. Topic mentions overlap and include praise; no root cause or complaint rate is established. The monthly chart retains V1 horizontal blue volume bars, with each bank's count and low-star share. Partial months are marked. Original wording is unchanged.

Source mode: {data['collection']['status']}. Latest included review: {rows[0]['review_time_hk']}. {data['collection'].get('limitations', 'Bounded public samples; not exhaustive history.')} Actual capture ranges by bank/store are in data/qa/coverage.csv. See methodology.md for proxy, language and sampling limits.
""")
    note(root, "handover.md", f"""# Delivery guide

Open report_customer_feedback.html locally. Switch App store to update all comparisons/topics/monthly figures. Comment filters operate only on the unified English/Chinese comment list. No language selector is provided.

- Workbook: data/reviews_master.xlsx (two original-review store sheets and six combined aggregate/coverage sheets).
- Combined newest-first CSV/JSON: data/merged/master_bilingual_six_months.*.
- Row labels and analysis tables: data/analysis/.
- Raw evidence and capture metadata: data/raw/, collection_summary.json.
- Methods, A–F, sample judgments and checks: methodology.md, checkpoints, manual_review.json, validation/, screenshots/.

Included records: {len(rows)}. Window: {config['since']} through {config['as_of']} inclusive HKT. Actual latest: {rows[0]['review_time_hk']}. Build completion does not mean final validation: F and manifest.json are created only after static/browser checks and actual screenshot inspection. Source links need network; the report itself has no remote assets. New input/rules/windows require a new batch and actual reading judgments. Reproduction does not refresh live coverage.
""")
    note(root, "checkpoint_E_report_and_validation.md", "# Checkpoint E — build and verification status\n\nEnglish standalone report, separate stores and combined English/Chinese results built. V1-style horizontal monthly chart, original source comments, full pagination and formula-safe workbook are present. Static/browser/visual status is recorded separately in validation/. This build note does not claim those later checks have passed; finalize requires exact report/screenshot hash bindings.")
    dump(root / "build_manifest.json", dict(report_sha256=sha(report), config_sha256=sha(root / "config.json"), manual_review_sha256=sha(root / "manual_review.json"), analysis_sha256=sha(root / "data/analysis/summary.json"), workbook_sha256=sha(root / "data/reviews_master.xlsx")), exclusive=True)
    print(json.dumps(dict(records=len(rows), report_sha256=sha(report))))
