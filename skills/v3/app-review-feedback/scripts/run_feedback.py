"""Reusable HK banking feedback: combined English/Chinese, separate stores."""
import argparse
import copy
import json
import shutil
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from feedback_io import HK, SKILL, bounds, config_for, csv_write, dump, fingerprints, load, now, require, safe_path, sha, six_months_before, sorted_rows, validate_row, xlsx_write
from bilingual_rules import THEMES, classify, language_group, metrics, normalized, theme_metrics

STORES = ["Google Play", "Apple App Store"]
SLUGS = dict(zip(STORES, ["google_play", "apple_app_store"]))


def note(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text.strip() + "\n")


def export(root, name, rows, fields=None):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    dump(path.with_suffix(".json"), rows, exclusive=True)
    csv_write(path.with_suffix(".csv"), rows, fields)


def guard(root):
    manifest = load(root / "data/merged/merge_manifest.json")
    require(sha(root / "source_records.json") == manifest["source_sha256"], "Source changed")
    require(sha(root / "config.json") == manifest["config_sha256"], "Configuration changed; use a new batch")
    for name, digest in manifest["files"].items():
        require(sha(safe_path(root, name)) == digest, "Merged evidence changed: " + name)


def initialize(args):
    root = args.root.resolve()
    require(not root.exists() or not any(root.iterdir()), "Choose a new/empty output batch")
    cutoff = date.fromisoformat(args.as_of) if args.as_of else datetime.now(HK).date()
    since = date.fromisoformat(args.since) if args.since else six_months_before(cutoff)
    config = dict(schema_version=2, country="HK", timezone="Asia/Hong_Kong", language="english_and_chinese", platform_split=True,
        analysis_population="english_and_chinese_combined", since=since.isoformat(), as_of=cutoff.isoformat(),
        google_request_languages=["en", "zh-HK", "zh-CN"], google_max_pages=100, apple_max_pages=10,
        pause_seconds=0.9, all_history=False, language_overrides=[], apps=load(args.apps or SKILL / "assets/apps.json"))
    dump(root / "config.json", config, exclusive=True)
    config_for(root)
    note(root, "plan.md", f"""# Feedback monitoring plan

Window: {since} through {cutoff}, inclusive HKT. English and Chinese comments form one result per bank/store. Management delivery is English. Stores remain separate. Horizontal monthly volume bars retain the V1 design.

A: establish app identities, window and source mode. B: bounded capture or saved snapshot import, preserving raw evidence. C: deduplicate IDs, validate sources/dates, select eligible comments. D: uniform star sentiment, bilingual topics and actual sample reading. E: offline HTML, workbook, independent static/browser checks and actual screenshots. F: bind judgments/checks/screenshots to the delivered report and create the integrity manifest.

Initialization does not complete any checkpoint. No live alerts, incident severity, social media or population satisfaction claims are included.
""")
    print(json.dumps(dict(batch=str(root), config=config), ensure_ascii=True))


def checkpoint_a(root, config):
    capture = load(root / "collection_summary.json")
    note(root, "checkpoint_A_source_feasibility.md", "# Checkpoint A — sources and scope\n\n" +
        f"Mode: {capture['status']}. Window: {config['since']} through {config['as_of']} inclusive HKT. One combined English/Chinese population with separate Google/Apple results.\n\n" +
        "\n".join(f"- {a['name']} ({a['role']}): Google {a['google_id']}; Apple {a['apple_id']}." for a in config["apps"]) +
        "\n\nSaved import does not establish current endpoint availability. For live runs, inspect listing/lookup evidence for name, publisher and IDs. Source limits/capture dates/stop reasons are in collection_summary.json. Locale does not prove author language or location.")


def import_snapshot(root, config, args):
    require(not (root / "source_records.json").exists() and not (root / "data/raw").exists(), "Input already started")
    require(args.input and args.evidence_root, "Import requires --input and --evidence-root")
    rows = copy.deepcopy(load(args.input))
    input_digest = sha(args.input)
    require(isinstance(rows, list) and rows, "Need a nonempty normalized JSON array")
    copied = {}
    for index, row in enumerate(rows):
        for field in ("raw_response_workspace_path", "raw_items_workspace_path"):
            if not row.get(field):
                continue
            original = safe_path(args.evidence_root.resolve(), row[field])
            digest = sha(original)
            target = root / "data/raw/imported" / (digest + original.suffix)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copyfile(original, target)
            require(sha(target) == digest, "Imported evidence mismatch")
            row["origin_" + field] = row[field]
            row[field] = target.relative_to(root).as_posix()
            copied[row[field]] = digest
        row["origin_input_row"] = index
        if row.get("analysis_language") in {"english", "chinese", "mixed", "excluded"} and row.get("analysis_language_method"):
            # Reuse supplied decisions explicitly; never present them as newly read labels.
            row["imported_language_decision"] = dict(language=row["analysis_language"], method=row["analysis_language_method"], fingerprint=fingerprints(row), input_sha256=input_digest)
        validate_row(row, config, root)
    dump(root / "source_records.json", rows, exclusive=True)
    dump(root / "collection_summary.json", dict(status="imported", mode="offline_snapshot", input_filename=args.input.name,
        input_sha256=input_digest, input_rows=len(rows), raw_evidence_sha256=copied, live_source_validation_performed=False,
        limitations=args.coverage_note or "Saved public samples only; no new collection or complete historical coverage claim."), exclusive=True)
    checkpoint_a(root, config)


def month_buckets(config):
    start, end = bounds(config)
    cursor = date(start.year, start.month, 1)
    cutoff = date.fromisoformat(config["as_of"])
    result = []
    while cursor <= cutoff:
        following = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
        result.append((cursor.strftime("%Y-%m"), start.date() > cursor or end.date() < following))
        cursor = following
    return result


def prepare(root, config):
    require(not (root / "data/merged").exists(), "Prepared output exists; use a new batch")
    observations = copy.deepcopy(load(root / "source_records.json"))
    require(observations, "No source observations")
    index, refs, variants = {}, defaultdict(list), []
    for row in observations:
        validate_row(row, config, root)
        key = row["record_key"]
        refs[key].append({k: row.get(k) for k in ("request_language", "collected_at_utc", "raw_response_workspace_path", "raw_item_index", "raw_entry_index")})
        if key not in index:
            index[key] = row
        elif fingerprints(index[key]) != fingerprints(row):
            variants.append(dict(record_key=key, chosen_fingerprint=fingerprints(index[key]), variant_fingerprint=fingerprints(row), variant=row, reason="First supplied observation retained; alternate capture preserved"))
    overrides = {o["record_key"]: o for o in config["language_overrides"]}
    require(len(overrides) == len(config["language_overrides"]) and set(overrides) <= set(index), "Unknown/duplicate language override")
    start, end = bounds(config)
    for key, row in index.items():
        decision = row.get("imported_language_decision")
        if decision:
            require(decision["fingerprint"] == fingerprints(row), "Imported language decision source changed")
            row.update(analysis_language=decision["language"], analysis_language_method="Imported documented decision: " + decision["method"], language_override_applied=True)
        if key in overrides:
            o = overrides[key]
            require(row["text"] == o["expected_text"] and row.get("title") == o.get("expected_title"), "Override original differs")
            require(o.get("reason") and o.get("reviewer") and o.get("reviewed_at") and o["language"] in {"english", "chinese", "mixed", "excluded"}, "Actual language review provenance required")
            row.update(analysis_language=o["language"], analysis_language_method="Exact source review: " + o["reason"], language_override_applied=True)
        row["analysis_language"], row["analysis_language_method"] = language_group(row)
        row["within_six_month_window"] = start.timestamp() <= row["review_timestamp_seconds"] < end.timestamp()
        row["source_observations"] = refs[key]
    rows = sorted_rows(list(index.values()))
    included = [r for r in rows if r["within_six_month_window"] and r["analysis_language"] != "excluded"]
    require(included, "No eligible in-window comments; report the source gap")
    export(root, "data/merged/master_all_reviews", rows)
    export(root, "data/merged/master_bilingual_six_months", included)
    export(root, "data/merged/capture_variants", variants, ["record_key", "chosen_fingerprint", "variant_fingerprint", "variant", "reason"])
    export(root, "data/merged/exclusions", [dict(record_key=r["record_key"], platform=r["platform"], app_key=r["app_key"], reason="outside_window" if not r["within_six_month_window"] else "empty_unsupported_or_uncertain_language") for r in rows if not r["within_six_month_window"] or r["analysis_language"] == "excluded"])
    manifest = dict(source_sha256=sha(root / "source_records.json"), config_sha256=sha(root / "config.json"),
        observations=len(observations), unique_records=len(rows), included_records=len(included), duplicate_observations=len(observations)-len(rows), capture_variants=len(variants),
        files={p.relative_to(root).as_posix(): sha(p) for p in (root / "data/merged").iterdir() if p.is_file()})
    dump(root / "data/merged/merge_manifest.json", manifest, exclusive=True)
    note(root, "checkpoint_B_data_collection_and_quality.md", f"# Checkpoint B — saved input\n\n{len(observations)} source observations, {len(rows)} unique IDs, {len(included)} included combined reviews. Window {config['since']} through {config['as_of']} inclusive HKT; actual latest included {included[0]['review_time_hk']}. First supplied observation wins; originals, alternate captures and exclusions remain saved. See collection_summary.json and data/merged/merge_manifest.json.")
    print(json.dumps(manifest, ensure_ascii=True))


def qa(root, config):
    guard(root)
    require(not (root / "data/qa").exists(), "QA already exists")
    rows = load(root / "data/merged/master_bilingual_six_months.json")
    repeats = Counter(normalized(r["text"]) for r in rows)
    coverage = []
    for store in STORES:
        for app in config["apps"]:
            part = [r for r in rows if r["platform"] == store and r["app_key"] == app["key"]]
            coverage.append(dict(platform=store, app_key=app["key"], app=app["name"], included_bilingual=len(part), earliest_included_hk=part[-1]["review_time_hk"] if part else None, latest_included_hk=part[0]["review_time_hk"] if part else None,
                first_capture_utc=min((r["collected_at_utc"] for r in part), default=None), last_capture_utc=max((r["collected_at_utc"] for r in part), default=None)))
    export(root, "data/qa/coverage", coverage)
    dump(root / "data/qa/summary.json", dict(included_records=len(rows), language_counts=dict(Counter(r["analysis_language"] for r in rows)), repeated_text_groups=sum(n > 1 for n in repeats.values()), input_sha256=sha(root / "data/merged/master_bilingual_six_months.json")), exclusive=True)
    note(root, "checkpoint_C_data_preparation.md", f"# Checkpoint C — preparation and QA\n\n{len(rows)} unique, newest-first records. Original text, Apple titles, ratings and review/capture times remain separate. Repeated wording under different IDs is retained. Language is eligibility metadata; all eligible comments form one bank/store denominator. QA coverage retains capture dates and actual observation boundaries. Source-file presence is checked here; exact raw matching is required by verify.")


def analyze(root, config):
    guard(root)
    require(not (root / "data/analysis").exists(), "Analysis already exists")
    rows = load(root / "data/merged/master_bilingual_six_months.json")
    require(sha(root / "data/merged/master_bilingual_six_months.json") == load(root / "data/qa/summary.json")["input_sha256"], "QA input changed")
    labels = [dict(r, **classify(r)) for r in rows]
    groups, topics, months, totals, deltas, sample = [], [], [], [], [], []
    apps = sorted(config["apps"], key=lambda a: a["role"] != "primary")
    primary = apps[0]
    for store in STORES:
        for app in apps:
            members = [r for r in labels if r["platform"] == store and r["app_key"] == app["key"]]
            extra = dict(platform=store, app_key=app["key"], app=app["name"])
            groups.append(metrics(members, store + " | " + app["name"], extra))
            topics.extend(dict(t, **extra) for t in theme_metrics(members, store + " | " + app["name"]))
            for bucket, partial in month_buckets(config):
                part = [r for r in members if r["review_time_hk"].startswith(bucket)]
                months.append(metrics(part, store + " | " + app["name"] + " | " + bucket, dict(extra, month_hk=bucket, partial_calendar_month=partial)))
            export(root, "data/stores/" + SLUGS[store] + "_" + app["key"], members, list(labels[0]))
            for language in ("english", "chinese", "mixed"):
                for rating in (1, 3, 5):
                    row = next((r for r in members if r["analysis_language"] == language and r["rating"] == rating), None)
                    if row:
                        sample.append({k: row.get(k) for k in ("record_key", "platform", "app_key", "analysis_language", "rating", "review_time_hk", "title", "text", "rating_sentiment", "themes", "theme_labels")} | dict(fingerprint=fingerprints(row)))
        p = next(g for g in groups if g["platform"] == store and g["app_key"] == primary["key"])
        for app in apps[1:]:
            b = next(g for g in groups if g["platform"] == store and g["app_key"] == app["key"])
            valid = p["review_count"] and b["review_count"]
            deltas.append(dict(platform=store, primary=primary["name"], primary_key=primary["key"], benchmark=app["name"], benchmark_key=app["key"], primary_n=p["review_count"], benchmark_n=b["review_count"], mean_rating_difference_sc_minus_benchmark=round(p["mean_rating"]-b["mean_rating"],4) if valid else None, low_star_rate_difference_percentage_points=round(100*(p["negative_rate_rating_1_2"]-b["negative_rate_rating_1_2"]),4) if valid else None))
        for bucket, partial in month_buckets(config):
            item = dict(platform=store, month_hk=bucket, partial_calendar_month=partial, review_count=0)
            for app in apps:
                m = next(m for m in months if m["platform"] == store and m["app_key"] == app["key"] and m["month_hk"] == bucket)
                item["review_count"] += m["review_count"]
                for suffix, field in (("review_count", "review_count"), ("low_star_count", "negative_count_rating_1_2"), ("low_star_rate", "negative_rate_rating_1_2")):
                    item[app["key"] + "_" + suffix] = m[field]
            totals.append(item)
        export(root, "data/stores/" + SLUGS[store] + "_bilingual_reviews", [r for r in labels if r["platform"] == store], list(labels[0]))
    for name, value in (("comment_labels", labels), ("store_benchmarks", groups), ("themes_by_store_bank", topics), ("monthly_by_store_bank", months), ("monthly_feedback_monitoring", totals), ("benchmark_deltas", deltas), ("validation_sample", sample)):
        export(root, "data/analysis/" + name, value)
    dump(root / "manual_review.json", dict(status="pending", reviewer=None, reviewed_at=None, sample_sha256=sha(root / "data/analysis/validation_sample.json"), judgements=[dict(record_key=r["record_key"], fingerprint=r["fingerprint"], rating_assessment=None, theme_assessment=None, notes=None) for r in sample]), exclusive=True)
    dump(root / "data/analysis/summary.json", dict(included_records=len(labels), sample_count=len(sample), input_sha256=sha(root / "data/merged/master_bilingual_six_months.json"), files={p.relative_to(root).as_posix():sha(p) for folder in (root / "data/analysis", root / "data/stores") for p in folder.iterdir() if p.is_file()}), exclusive=True)
    note(root, "checkpoint_D_feedback_analysis.md", f"# Checkpoint D — analysis and reading sample\n\n{len(labels)} comments; {len(groups)} bank/store groups; {len(topics)} overlapping topic rows; {len(months)} monthly bank rows; {len(totals)} monthly chart rows; {len(deltas)} within-store benchmark comparisons. English/Chinese comments form one result. Uniform star sentiment is not text-polarity accuracy.\n\nRead all {len(sample)} selected comments and record individual source-bound notes in manual_review.json. Generated sample status is pending; this stage does not certify actual reading.")
    print(json.dumps(dict(included=len(labels), sample_count=len(sample), groups=len(groups), monthly_chart_rows=len(totals))))


def validate_review(root):
    review = load(root / "manual_review.json")
    sample = load(root / "data/analysis/validation_sample.json")
    require(review["status"] == "reviewed" and review.get("reviewer") and review.get("reviewed_at"), "Actual sample reading remains pending")
    require(review["sample_sha256"] == sha(root / "data/analysis/validation_sample.json"), "Reviewed sample changed")
    notes = {j["record_key"]: j for j in review["judgements"]}
    require(len(notes) == len(review["judgements"]) == len(sample) and set(notes) == {r["record_key"] for r in sample}, "Review IDs differ")
    for r in sample:
        j = notes[r["record_key"]]
        require(j["fingerprint"] == r["fingerprint"] and j["rating_assessment"] in {"plausible", "disagreement_noted"} and j["theme_assessment"] in {"plausible", "insufficient_text", "limitation_noted"} and isinstance(j.get("notes"), str) and len(j["notes"].strip()) > 15, "Actual per-comment reading judgments required")
    return review


def finalize(root, config):
    from verify_report import verify
    verify(root, config)
    validate_review(root)
    digest = sha(root / "report_customer_feedback.html")
    browser = load(root / "validation/browser_results.json")
    visual = load(root / "validation/visual_inspection.json")
    require(browser["passed"] and browser["report_sha256"] == visual["report_sha256"] == digest, "Checks/visual approval stale or missing")
    require(visual["status"] == "reviewed" and visual.get("reviewer") and visual.get("reviewed_at_utc") and visual.get("judgments"), "Actual screenshot inspection required")
    require(visual["screenshots"] == browser["screenshot_hashes"] and len(visual["screenshots"]) >= 5, "Screenshot bindings differ")
    require(all(sha(safe_path(root, p)) == h for p,h in visual["screenshots"].items()), "Screenshot changed")
    note(root, "checkpoint_F_final_review.md", f"# Checkpoint F — final review\n\nReport SHA-256: `{digest}`. Source, independent metrics, reading sample, browser interactions and actually inspected screenshots are bound to this delivery. Combined English/Chinese population, separate stores, and horizontal monthly monitoring chart verified. These checks do not establish semantic accuracy, complete coverage or independent human acceptance. See validation/, methodology.md and manifest.json.")
    dump(root / "manifest.json", dict(schema_version=2, status="complete", finalized_at_utc=now(), report_sha256=digest, files={p.relative_to(root).as_posix():dict(sha256=sha(p), bytes=p.stat().st_size) for p in sorted(root.rglob("*")) if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts}), exclusive=True)
    print(json.dumps(dict(status="complete", report_sha256=digest)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["init", "collect", "import", "prepare", "qa", "analyze", "review-status", "build", "verify", "browser-test", "finalize"])
    p.add_argument("--root", type=Path, required=True)
    for name in ("since", "as-of", "coverage-note"):
        p.add_argument("--" + name)
    for name in ("apps", "input", "evidence-root", "browser"):
        p.add_argument("--" + name, type=Path)
    args = p.parse_args()
    if args.command == "init":
        initialize(args)
        return
    root = args.root.resolve()
    config = config_for(root)
    if args.command == "collect":
        from collect_reviews import collect
        collect(root, config)
        checkpoint_a(root, config)
    elif args.command == "import":
        import_snapshot(root, config, args)
    elif args.command == "review-status":
        print(json.dumps(dict(status="reviewed", sample_count=len(validate_review(root)["judgements"]))))
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
    else:
        globals()[args.command](root, config)


if __name__ == "__main__":
    main()
