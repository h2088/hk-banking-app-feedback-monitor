"""V2: fixed historical snapshots, three banks, strictly separate store denominators.

Usage: python -B v2/scripts/pipeline.py prepare|build|verify|finalize
Reproduction: copy v2 to a new sibling directory; run prepare --reuse-input, then
read new samples, record an actual review, build, verify and browser_check.py.
"""
import argparse
import calendar
import collections
import csv
import hashlib
import html
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0, str(ROOT / "engine"))
from feedback_io import bounds, csv_write, dump, fingerprints, load, now, sha, sorted_rows, validate_row, xlsx_write
from v2_rules import THEMES, classify, metrics, normalized, theme_metrics
from source_utils import parse_rpc, nested
from apple_parser import parse_feed, entries_from_feed, entry_label

STORES = ["Google Play", "Apple App Store"]
KEYS = ["sc_mobile", "hsbc_hk", "bochk"]
NAMES = {"sc_mobile": "SC Mobile", "hsbc_hk": "HSBC HK", "bochk": "BOCHK"}
SLUG = {"Google Play": "google_play", "Apple App Store": "apple_app_store"}
BASELINE_SHA = "d6410a3e12bbd2dbcfd9bd7ef193212ab7aa1dee6ff2c669245f5ef249debeb3"
ALL_SHA = "a04bdd34eaceddb4f66b5f087689122c5f5a08015cdd0b23cff6a9adbbf4f1d7"


def export(stem, rows, fields=None):
    path = ROOT / stem
    path.parent.mkdir(parents=True, exist_ok=True)
    dump(path.with_suffix(".json"), rows)
    csv_write(path.with_suffix(".csv"), rows, fields)


def baseline_files():
    """Hash V1 files before doing any work; V2 only reads V1."""
    return {p.relative_to(PROJECT).as_posix(): sha(p) for p in PROJECT.rglob("*")
            if p.is_file() and p.parts[len(PROJECT.parts)] not in {ROOT.name, ".git", ".venv", ".agents", ".codex"}
            and "__pycache__" not in p.parts}


def import_v1():
    source = PROJECT / "data/merged_2026-10-19/master_all_reviews.json"
    base = PROJECT / "data/merged_2026-10-19/master_english_six_months.json"
    assert sha(source) == ALL_SHA and sha(base) == BASELINE_SHA, "V1 snapshot changed"
    originals = load(source)
    copies, evidence = [], {}
    for index, original in enumerate(originals):
        row = dict(original)
        row["origin_input_row"] = index
        row["snapshot_mode"] = "V1 October 19 capture, reused without refreshing"
        for field in ("raw_response_workspace_path", "raw_items_workspace_path"):
            value = row.get(field)
            if not value:
                continue
            path = (PROJECT / value).resolve()
            assert path.is_relative_to(PROJECT) and path.is_file()
            digest = sha(path)
            target = ROOT / "data/raw/imported" / (digest + path.suffix)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copyfile(path, target)
            evidence[value] = dict(sha256=digest, copied_path=target.relative_to(ROOT).as_posix())
            row["origin_" + field] = value
            row[field] = target.relative_to(ROOT).as_posix()
        copies.append(row)
    dump(ROOT / "data/input/v1_all_reviews.json", copies)
    dump(ROOT / "data/input/v1_english_baseline.json", load(base))
    dump(ROOT / "data/input/import_manifest.json", dict(source_sha256=ALL_SHA, baseline_sha256=BASELINE_SHA, evidence=evidence))
    dump(ROOT / "data/input/v1_preservation.json", baseline_files())
    return copies


def prepare(reuse=False):
    config = load(ROOT / "config.json")
    assert config["schema_version"] == 2 and config["platform_split"] is True
    assert [a["key"] for a in config["apps"]] == KEYS
    old = load(ROOT / "data/input/v1_all_reviews.json") if reuse else import_v1()
    new = load(ROOT / "data/bochk_collection/source_records.json")
    source = sorted_rows(old + [dict(r, snapshot_mode="BOCHK October 22 capture filtered to V1 dates") for r in new])
    start, end = bounds(config)
    overrides = load(ROOT / "language_overrides.json") if (ROOT / "language_overrides.json").exists() else []
    by_key = {r["record_key"]: r for r in source}
    assert len(by_key) == len(source), "Duplicate IDs"
    for correction in overrides:
        row = by_key[correction["record_key"]]
        assert row.get("title") == correction["expected_title"] and row["text"] == correction["expected_text"]
        assert correction["reviewer"] and correction["reason"] and correction["reviewed_at"]
        row["origin_language_status"] = row["language_status"]
        row["language_status"] = correction["status"]
        row["detected_language"] = correction["language"]
        row["language_method"] = "agent_review_exact_source_text"
    english, exclusions, queue = [], [], []
    for row in source:
        validate_row(row, config, ROOT)
        inside = start.timestamp() <= row["review_timestamp_seconds"] < end.timestamp()
        row["within_six_month_window"] = inside
        row["on_or_before_cutoff"] = row["review_timestamp_seconds"] < end.timestamp()
        if inside and row["language_status"] == "english":
            english.append(row)
        else:
            exclusions.append({k: row.get(k) for k in ("record_key", "platform", "app_key", "review_time_hk", "language_status")} | {"exclusion_reason": "outside_date_window" if not inside else "language_" + row["language_status"]})
        if row["app_key"] == "bochk" and inside and row["language_status"] != "english":
            queue.append({k: row.get(k) for k in ("record_key", "platform", "title", "text", "rating", "language_status", "detected_language", "language_method")})
    baseline = load(ROOT / "data/input/v1_english_baseline.json")
    original = {r["record_key"]: fingerprints(r) for r in baseline}
    recovered = {r["record_key"]: fingerprints(r) for r in english if r["app_key"] != "bochk"}
    assert original == recovered and len(original) == 311, "SC/HSBC baseline not reproduced"
    export("data/merged/master_all_reviews", source)
    export("data/merged/master_english_six_months", english)
    export("data/qa/exclusions", exclusions)
    dump(ROOT / "data/qa/bochk_language_review_queue.json", queue)
    labeled = [dict(row, **classify(row)) for row in english]
    export("data/analysis/comment_labels", labeled)
    groups, themes, monthly, coverage, samples = [], [], [], [], []
    for platform in STORES:
        for key in KEYS:
            rows = [r for r in labeled if r["platform"] == platform and r["app_key"] == key]
            extra = dict(platform=platform, app_key=key, app=NAMES[key])
            groups.append(metrics(rows, platform + " | " + NAMES[key], extra))
            themes.extend([dict(t, **extra) for t in theme_metrics(rows, platform + " | " + NAMES[key])])
            all_group = [r for r in source if r["platform"] == platform and r["app_key"] == key]
            in_window = [r for r in all_group if r["within_six_month_window"]]
            coverage.append(dict(**extra, fetched_all_dates_languages=len(all_group), within_window_all_languages=len(in_window), english_in_window=len(rows),
                window_language_status_counts=dict(collections.Counter(r["language_status"] for r in in_window)),
                earliest_fetched_hk=min((r["review_time_hk"] for r in all_group), default=None),
                latest_fetched_hk=max((r["review_time_hk"] for r in all_group), default=None),
                earliest_english_in_window_hk=min((r["review_time_hk"] for r in rows), default=None),
                latest_english_in_window_hk=max((r["review_time_hk"] for r in rows), default=None),
                collected_at_utc_min=min((r["collected_at_utc"] for r in all_group), default=None),
                collected_at_utc_max=max((r["collected_at_utc"] for r in all_group), default=None),
                reached_before_window=any(r["review_timestamp_seconds"] < start.timestamp() for r in all_group)))
            export("data/stores/" + SLUG[platform] + "_" + key, rows, list(labeled[0]) if labeled else None)
            for month in range(4, 11):
                bucket = f"2026-{month:02}"
                members = [r for r in rows if r["review_time_hk"].startswith(bucket)]
                monthly.append(metrics(members, platform + " | " + NAMES[key] + " | " + bucket, extra | {"month_hk": bucket, "partial_calendar_month": month in {4, 10}}))
            for rating in range(1, 6):
                chosen = next((r for r in rows if r["rating"] == rating), None)
                if chosen:
                    samples.append({k: chosen.get(k) for k in ("record_key", "platform", "app_key", "rating", "review_time_hk", "title", "text", "rating_sentiment", "text_sentiment_rule", "themes", "theme_labels")} | {"fingerprint": fingerprints(chosen)})
    for platform in STORES:
        export("data/stores/" + SLUG[platform] + "_english_reviews", [r for r in labeled if r["platform"] == platform], list(labeled[0]) if labeled else None)
    comparisons = []
    theme_deltas = []
    for store in STORES:
        primary = next(g for g in groups if g["platform"] == store and g["app_key"] == "sc_mobile")
        for benchmark in KEYS[1:]:
            other = next(g for g in groups if g["platform"] == store and g["app_key"] == benchmark)
            comparisons.append(dict(platform=store, primary="SC Mobile", benchmark=NAMES[benchmark], primary_n=primary["review_count"], benchmark_n=other["review_count"],
                mean_rating_difference_sc_minus_benchmark=round(primary["mean_rating"] - other["mean_rating"], 4) if primary["review_count"] and other["review_count"] else None,
                low_star_rate_difference_percentage_points=round((primary["negative_rate_rating_1_2"] - other["negative_rate_rating_1_2"]) * 100, 4) if primary["review_count"] and other["review_count"] else None))
            for theme in THEMES:
                p = next(t for t in themes if t["platform"] == store and t["app_key"] == "sc_mobile" and t["theme"] == theme)
                b = next(t for t in themes if t["platform"] == store and t["app_key"] == benchmark and t["theme"] == theme)
                theme_deltas.append(dict(platform=store, benchmark=NAMES[benchmark], theme=theme, theme_label=p["theme_label"], sc_mentions=p["theme_mentions"], benchmark_mentions=b["theme_mentions"], sc_n=p["review_count"], benchmark_n=b["review_count"], mention_rate_difference_percentage_points=round(100 * (p["theme_mention_rate"] - b["theme_mention_rate"]), 4) if p["review_count"] and b["review_count"] else None))
    for name, values in (("store_benchmarks", groups), ("themes_by_store_bank", themes), ("monthly_by_store_bank", monthly), ("benchmark_deltas", comparisons), ("theme_deltas", theme_deltas)):
        export("data/analysis/" + name, values)
    export("data/qa/coverage", coverage)
    dump(ROOT / "data/analysis/validation_sample.json", samples)
    repeats = collections.defaultdict(list)
    for row in english:
        repeats[normalized(row["text"])].append(row["record_key"])
    repeats = [dict(normalized_text=t, record_keys=ids, count=len(ids)) for t, ids in repeats.items() if len(ids) > 1]
    dump(ROOT / "data/qa/repeated_text_groups.json", repeats)
    summary = dict(prepared_at_utc=now(), window_start_inclusive_hk=start.isoformat(), window_end_exclusive_hk=end.isoformat(),
        all_fetched_records=len(source), window_all_languages=sum(r["within_six_month_window"] for r in source), english_window_records=len(english),
        baseline_records_preserved=311, bochk_english_added=sum(r["app_key"] == "bochk" for r in english),
        repeated_text_groups=len(repeats), repeated_text_records=sum(r["count"] for r in repeats),
        short_comment_title_plus_body_count=sum(r["short_text_for_theme_review"] for r in labeled),
        unclassified_count=sum(not r["themes"] for r in labeled), validation_sample_count=len(samples), coverage=coverage)
    dump(ROOT / "data/qa/qa_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=True), flush=True)


def review_status():
    review = load(ROOT / "manual_review.json")
    samples = load(ROOT / "data/analysis/validation_sample.json")
    assert review["status"] == "reviewed" and "agent" in review["reviewer"].lower()
    assert review["sample_sha256"] == sha(ROOT / "data/analysis/validation_sample.json")
    notes = {r["record_key"]: r for r in review["reviews"]}
    assert set(notes) == {r["record_key"] for r in samples}
    for row in samples:
        note = notes[row["record_key"]]
        assert note["fingerprint"] == row["fingerprint"]
        assert note["rating_assessment"] in {"plausible", "disagreement_noted"}
        assert note["theme_assessment"] in {"plausible", "insufficient_text", "limitation_noted"}
        assert len(note["notes"]) > 20
    return review


def pct(x):
    return "N/A" if x is None else f"{100*x:.1f}%"


def table(headers, rows):
    return "| " + " | ".join(headers) + " |\n|" + "|".join("---" for h in headers) + "|\n" + "\n".join("| " + " | ".join(str(c) for c in row) + " |" for row in rows) + "\n"


def build():
    review_status()
    config = load(ROOT / "config.json")
    summary = load(ROOT / "data/qa/qa_summary.json")
    rows = load(ROOT / "data/analysis/comment_labels.json")
    groups = load(ROOT / "data/analysis/store_benchmarks.json")
    themes = load(ROOT / "data/analysis/themes_by_store_bank.json")
    monthly = load(ROOT / "data/analysis/monthly_by_store_bank.json")
    deltas = load(ROOT / "data/analysis/benchmark_deltas.json")
    coverage = load(ROOT / "data/qa/coverage.json")
    # This is the only report payload: customer names and developer replies are absent.
    fields = ["record_key", "platform", "app_key", "app", "rating", "title", "text", "review_time_hk", "review_timestamp_seconds", "source_url", "rating_sentiment", "themes", "theme_labels"]
    payload = dict(config=config, summary=summary, groups=groups, themes=themes, monthly=monthly, deltas=deltas, coverage=coverage,
                   rows=[{k: r.get(k) for k in fields} for r in rows], theme_names={k: v[0] for k, v in THEMES.items()})
    template = (ROOT / "assets/report.html").read_text(encoding="utf-8")
    embedded = json.dumps(payload, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    (ROOT / "report_customer_feedback_v2.html").write_text(template.replace("__PAYLOAD__", embedded), encoding="utf-8")
    workbook = ROOT / "data/reviews_v2.xlsx"
    if workbook.exists():
        workbook.unlink()  # Generated V2 artifact only; never touches original evidence.
    xlsx_write(workbook, {"Google Play reviews": [r for r in rows if r["platform"] == STORES[0]], "Apple App Store reviews": [r for r in rows if r["platform"] == STORES[1]],
        "Store benchmarks": groups, "Benchmark deltas": deltas, "Themes by store and bank": themes, "Theme benchmark deltas": load(ROOT / "data/analysis/theme_deltas.json"), "Monthly by store and bank": monthly, "Coverage and capture dates": coverage})
    write_docs(config, summary, groups, themes, deltas, coverage)
    print(json.dumps(dict(report_sha256=sha(ROOT / "report_customer_feedback_v2.html"), workbook_sha256=sha(workbook), records=len(rows)), ensure_ascii=True))


def write_docs(config, summary, groups, themes, deltas, coverage):
    findings = []
    for store in STORES:
        findings.append("## " + store + "\n\n" + table(["Bank", "English reviews", "Sample mean / 5", "1-2 star reviews", "1-2 star share"],
            [[g["app"], g["review_count"], f"{g['mean_rating']:.2f}" if g["mean_rating"] is not None else "N/A", g["negative_count_rating_1_2"], pct(g["negative_rate_rating_1_2"])] for g in groups if g["platform"] == store]))
        for d in deltas:
            if d["platform"] == store:
                findings.append(f"SC minus {d['benchmark']}: {d['mean_rating_difference_sc_minus_benchmark']:+.2f} stars; {d['low_star_rate_difference_percentage_points']:+.1f} percentage points in the low-star share.\n")
        focus = sorted([t for t in themes if t["platform"] == store and t["app_key"] == "sc_mobile"], key=lambda t: (-t["theme_negative_count"], -t["theme_mentions"]))[:3]
        findings.append("Most frequent SC topics among low-star records: " + "; ".join(f"{t['theme_label']} ({t['theme_negative_count']} low-star records; {t['theme_mentions']} total mentions)" for t in focus) + ". Topics overlap; they are screening priorities, not confirmed defects.\n")
    findings_text = "\n".join(findings)
    common = ("Observation window: 19 April to 19 October 2026 inclusive, Hong Kong time. "
        "SC and HSBC retain the 19 October V1 capture; BOCHK was captured on 22 October and filtered to the same review dates. "
        "A later BOCHK capture cannot reconstruct deleted or edited reviews as they appeared on 19 October. "
        "Public endpoints provide a bounded, request-specific sample, not every customer or all historical reviews.\n")
    source_note = ("BOCHK Google Play: 600 unique records from three 200-record pages; collection stopped after two pages entirely before the window. "
        "Apple: 500 unique records from ten 50-record pages. The page-11 boundary request returned HTTP 400; that failed response and metadata are retained. "
        "The ten accepted pages are usable; there is no claim of exhaustive Apple history. Per-group earliest dates and whether the capture reaches before the window are in coverage.csv.\n")
    method = ("The customer comment body is `text`. Apple `title` is retained separately and included with the body for theme matching and search. "
        "Developer replies are excluded. Comments are never translated or rewritten. The English subset uses deterministic script/short-word checks and langdetect 1.0.9 (seed 0, threshold 0.80), "
        "plus separately recorded exact-text agent language corrections. Existing SC/HSBC language decisions are frozen.\n\n"
        "Rating sentiment is a proxy: 1-2 stars negative, 3 neutral, 4-5 positive. Text lexicon sentiment is supplemental and can disagree. "
        "Eleven transparent keyword themes are multi-label mentions, including positive mentions. V2 adds explicit face/facial recognition, HKID scan and ID/email checking patterns to the access theme, and suggest/consider/combine wording to feature requests; see scripts/v2_rules.py. Raw V1 comments stay unchanged; derived themes are recomputed. A first matched theme is not a severity ranking. "
        "Broad terms such as service, notification, account, ads and FX can overmatch. The rules do not reliably handle sarcasm, negation or root causes.\n\n"
        "Each metric uses one bank within one store. Low-star share = 1-2 star records / all English records for that bank and store. "
        "Theme mention share = records mentioning a theme / all records in that bank/store; theme low-star share uses theme mentions as its denominator. "
        "Monthly means and shares are recomputed within bank/store/month. April and October are partial calendar months. Empty groups are N/A. "
        "Differences are SC minus the named benchmark; rate differences are percentage points. Store-level sample means are not the stores' headline lifetime ratings.\n\n"
        "Different review IDs with repeated wording remain separate; observations are review records, not unique customers. "
        "No statistical significance, incident severity, causal diagnosis, customer-population satisfaction or issue incidence is established. "
        "The reading check is performed by a Codex agent and is not an independent human annotation accuracy study.\n")
    docs = {
        "README.md": f"# Hong Kong Banking App Feedback Monitor - V2\n\nManager-ready English report with separate Google Play and Apple App Store comparisons of SC Mobile against HSBC HK and BOCHK.\n\nOpen [the offline report](report_customer_feedback_v2.html). Read [the executive brief](executive_summary.md), [methodology](methodology.md) and [handover](handover.md). The Excel workbook is [data/reviews_v2.xlsx](data/reviews_v2.xlsx); its two review sheets are separated by store.\n\n{common}\nAccepted English records: **{summary['english_window_records']}** ({summary['baseline_records_preserved']} unchanged SC/HSBC records plus {summary['bochk_english_added']} BOCHK records). Full fetched source records, including excluded dates/languages: {summary['all_fetched_records']}.\n\n## What changed\n\n| Manager request | V2 delivery |\n|---|---|\n| Change it into English | Report, controls, methods, checkpoints and handover in English; source comments preserved verbatim |\n| Separate stores | Six bank/store groups; separate metric, theme, monthly and review views; two Excel review sheets and six CSV slices |\n| Add BOC HK | Verified BOCHK retail app from Bank of China (Hong Kong) Limited; independent HSBC and BOCHK benchmark deltas in each store |\n\nV1 remains intact. The original installed Skill and its CLI still support the original two-bank combined-store scope. V2 uses `scripts/pipeline.py`, with a frozen copy of its collection, classification and export helpers in `engine/`; do not use `engine/run_feedback.py` for V2.\n\nSee [reproduction.md](reproduction.md) to rerun locally. No server, API key or CDN is needed to read the report.\n",
        "executive_summary.md": "# Executive brief - V2\n\n" + common + "\n" + findings_text + "\n## Recommended follow-up\n\nPrioritise SC low-star stability, access and navigation examples in the relevant store. Validate the reported journey against support tickets, device/OS details and telemetry before treating it as a confirmed incident. Compare the same journey and store with each benchmark; retain both positive and negative examples. Review the exact comments through the report filters and source links. Small bank/store samples and collection differences limit rankings.\n\n" + source_note,
        "methodology.md": "# Methodology and limits\n\n" + common + "\n" + method + "\n## Collection and app identities\n\n" + table(["Bank", "Google package", "Apple ID"], [[a["name"], a["google_id"], a["apple_id"]] for a in config["apps"]]) + "\nApple search/lookup identifies BOCHK as published by Bank of China (Hong Kong) Limited; Google search and listing use the matching retail description and developer. BoC Pay+, BOCHK iGTB, BOCHK Brunei and mainland Bank of China are excluded. Identity response captures are retained.\n\n" + source_note,
        "plan.md": "# V2 revision plan - completed\n\n" + common + "\n1. A - verify official BOCHK retail identities and map the three manager requirements.\n2. B - reuse the immutable SC/HSBC snapshot; collect BOCHK with raw HTTP evidence.\n3. C - preserve the 311 baseline records; validate source IDs, exact text, timestamps, dates, languages and six-store-group coverage.\n4. D - classify rating sentiment and multi-label themes; calculate both benchmarks strictly within each store; actually read stratified samples.\n5. E - build an English offline report and a workbook with separate store review sheets; exercise controls and pagination in a real browser.\n6. F - verify artifacts and V1 preservation, inspect screenshots and produce a SHA-256 manifest.\n\nSee checkpoint_A_source_feasibility.md through checkpoint_F_final_review.md for evidence.\n",
        "checkpoint_A_source_feasibility.md": "# Checkpoint A - source feasibility\n\nV2 changes the comparison unit from bank-only to bank within store, and adds one benchmark. " + common + "\n" + source_note + "\nVerified retail IDs are recorded in config.json. Identity evidence is under data/bochk_collection/identity and per-store listing responses. The Apple page-11 HTTP error is preserved; it does not invalidate pages 1-10 or prove complete history.\n",
        "checkpoint_B_data_collection.md": "# Checkpoint B - data collection\n\n" + common + "\n" + source_note + f"\nSaved {summary['all_fetched_records']} all-date/all-language records, including the original 5,278 and 1,100 BOCHK records. Rows are newest first, with record_key as a deterministic tie-breaker. Original HTTP bodies, request parameters, timestamps and hashes are retained. Imported evidence files are copied by content hash with origin paths in an import manifest.\n",
        "checkpoint_C_data_qa.md": "# Checkpoint C - data quality\n\n" + f"The original 311 English SC/HSBC IDs and content fingerprints are preserved exactly. V2 contains {summary['english_window_records']} English in-window records, {summary['bochk_english_added']} from BOCHK. " + common + f"\nThere are {summary['repeated_text_groups']} repeated-text groups covering {summary['repeated_text_records']} records; distinct IDs are retained. There are {summary['short_comment_title_plus_body_count']} short analysis texts and {summary['unclassified_count']} records without a keyword theme. These are not silently removed. Exclusions, language decisions and per-store coverage are saved in data/qa.\n\n" + table(["Store", "Bank", "Fetched", "In-window all languages", "English"], [[c["platform"], c["app"], c["fetched_all_dates_languages"], c["within_window_all_languages"], c["english_in_window"]] for c in coverage]),
        "checkpoint_D_customer_feedback_analysis.md": "# Checkpoint D - customer feedback analysis\n\n" + findings_text + f"\nThere are six bank/store metrics, 66 theme rows, 42 monthly rows and four SC-versus-benchmark comparisons. The reading sample contains {summary['validation_sample_count']} observed bank/store/rating strata. Per-comment judgments and source fingerprints are in manual_review.json.\n\n" + method,
        "checkpoint_E_build_test.md": "# Checkpoint E - build and browser tests\n\nThe English report embeds only the English-window review payload, contains no external scripts/styles and displays exact customer text using safe text nodes. Store selection switches metrics, themes, monthly tables, examples and review results together. Other filters affect the review browser only, as labelled. Pagination is 25 records per page.\n\nVerification evidence is in validation/static_results.json and validation/browser_results.json. The delivered report SHA-256 must match both. Screenshots are in screenshots/. A failed check is not completion; see checkpoint_F_final_review.md for the final gate.\n",
        "handover.md": "# V2 handover\n\nOpen report_customer_feedback_v2.html locally. Select Google Play or Apple App Store, compare all three banks, then filter comments by bank, rating sentiment, rating, topic or search term. Comments are sorted newest first. Google links include reviewId; Apple generally opens the app review listing, so match the exact title, body, rating and date. Store websites may have changed since capture.\n\n" + common + "\n" + source_note + "\nThe report and executive brief are for managers; data/reviews_v2.xlsx has separate review sheets for each store. JSON is authoritative for typed values; CSV is UTF-8 with BOM and preserves exact comments. Prefer the typed XLSX for spreadsheet review of untrusted text. All fetched records, exclusions, per-comment labels, group metrics and source evidence remain available.\n\nNo social-media monitoring, automatic alerts, deployment or scheduled job is included. No message or report has been sent to the manager. V1 and its installed Skill remain unchanged.\n",
        "reproduction.md": "# Reproduce V2\n\nUse Python 3.10+; collection dependencies are in requirements-collection.txt. The saved-input pipeline is offline and uses the Python standard library.\n\nCopy this entire v2 directory to a new sibling directory before reprocessing. Do not rerun collection in an existing batch. In the copied directory, run:\n\n```powershell\n& '..\\.venv\\Scripts\\python.exe' -B scripts/pipeline.py prepare --reuse-input\n# Read data/analysis/validation_sample.json; write actual judgments in manual_review.json.\n& '..\\.venv\\Scripts\\python.exe' -B scripts/pipeline.py build\n& '..\\.venv\\Scripts\\python.exe' -B scripts/pipeline.py verify\n& '..\\.venv\\Scripts\\python.exe' -B scripts/browser_check.py\n# Inspect screenshots before writing the visual inspection record.\n& '..\\.venv\\Scripts\\python.exe' -B scripts/pipeline.py finalize\n```\n\nReusing the unchanged input, configuration and rules reproduces the metrics; capture timestamps, build/check times, ZIP metadata and integrity manifests can differ. A fresh network collection is a new observation and need not reproduce historical counts. collect_bochk.py is a bounded, BOCHK-only collector; SC/HSBC refresh requires an explicitly new batch and a revised capture plan. Frozen helper code in engine/ is reused; its original two-app CLI is not the V2 entry point.\n"
    }
    for name, text in docs.items():
        (ROOT / name).write_text(text, encoding="utf-8")
    (ROOT / "requirements-collection.txt").write_text("google-play-scraper==1.2.7\nlangdetect==1.0.9\n", encoding="utf-8")


def verify():
    config = load(ROOT / "config.json")
    rows = load(ROOT / "data/merged/master_english_six_months.json")
    source = load(ROOT / "data/merged/master_all_reviews.json")
    groups = load(ROOT / "data/analysis/store_benchmarks.json")
    labels = load(ROOT / "data/analysis/comment_labels.json")
    checks = []
    def check(name, condition, detail=None):
        checks.append(dict(name=name, passed=bool(condition), detail=detail))
        assert condition, name
    check("Stable newest-first ordering and unique source IDs", rows == sorted_rows(rows) and len({r["record_key"] for r in source}) == len(source))
    for row in rows:
        validate_row(row, config, ROOT, require_english=True)
    check("All English IDs, times, date bounds and raw paths valid", True, len(rows))
    baseline = load(ROOT / "data/input/v1_english_baseline.json")
    check("All 311 V1 English source contents preserved", {r["record_key"]: fingerprints(r) for r in baseline} == {r["record_key"]: fingerprints(r) for r in rows if r["app_key"] != "bochk"})
    # Independently decode raw HTTP evidence for every included comment.
    raw_cache = {}
    for row in rows:
        path = ROOT / row["raw_response_workspace_path"]
        key = str(path)
        if key not in raw_cache:
            raw_cache[key] = parse_rpc(path.read_text(encoding="utf-8"))[0] if row["platform"] == STORES[0] else dict(entries_from_feed(parse_feed(path.read_text(encoding="utf-8"))))
        items = raw_cache[key]
        if row["platform"] == STORES[0]:
            item = items[row["raw_item_index"]]
            check_values = (nested(item, [0]), nested(item, [4]), nested(item, [2]), nested(item, [5, 0]))
            assert check_values == (row["review_id"], row["text"], row["rating"], row["review_timestamp_seconds"]), row["record_key"]
        else:
            entry = items[row["raw_entry_index"]]
            assert (entry["id"]["label"], entry_label(entry, "title"), entry_label(entry, "content"), int(entry["im:rating"]["label"]), datetime.fromisoformat(entry["updated"]["label"]).timestamp()) == (row["review_id"], row["title"], row["text"], row["rating"], row["review_timestamp_seconds"])
    check("Every included review agrees with its raw HTTP ID, text, rating and timestamp", True, len(rows))
    for group in groups:
        members = [r for r in rows if r["platform"] == group["platform"] and r["app_key"] == group["app_key"]]
        n = len(members)
        assert group["review_count"] == n
        assert group["mean_rating"] == (round(sum(r["rating"] for r in members)/n, 4) if n else None)
        assert group["negative_rate_rating_1_2"] == (round(sum(r["rating"] <= 2 for r in members)/n, 6) if n else None)
    check("Six bank/store denominators independently recomputed", len(groups) == 6 and sum(g["review_count"] for g in groups) == len(rows))
    themes = load(ROOT / "data/analysis/themes_by_store_bank.json")
    for theme in themes:
        members = [r for r in labels if r["platform"] == theme["platform"] and r["app_key"] == theme["app_key"]]
        hits = [r for r in members if theme["theme"] in r["themes"]]
        assert len(hits) == theme["theme_mentions"] and len(members) == theme["review_count"]
        assert theme["theme_mention_rate"] == (round(len(hits)/len(members), 6) if members else None)
        assert theme["theme_negative_count"] == sum(r["rating"] <= 2 for r in hits)
    check("All 66 theme rates use correct store/bank denominator", len(themes) == 66)
    monthly = load(ROOT / "data/analysis/monthly_by_store_bank.json")
    for bucket in monthly:
        members = [r for r in rows if r["platform"] == bucket["platform"] and r["app_key"] == bucket["app_key"] and r["review_time_hk"].startswith(bucket["month_hk"])]
        assert bucket["review_count"] == len(members)
        assert bucket["negative_count_rating_1_2"] == sum(r["rating"] <= 2 for r in members)
        assert bucket["negative_rate_rating_1_2"] == (round(sum(r["rating"] <= 2 for r in members)/len(members), 6) if members else None)
    check("42 monthly groups include zero-count states and partial-month flags", len(monthly) == 42 and sum(m["review_count"] for m in monthly) == len(rows))
    with (ROOT / "data/merged/master_english_six_months.csv").open(encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    check("CSV retains JSON row order and exact source text", [r["record_key"] for r in csv_rows] == [r["record_key"] for r in rows] and all(c["text"] == j["text"] and c["title"] == (j.get("title") or "") for c,j in zip(csv_rows,rows)))
    with ZipFile(ROOT / "data/reviews_v2.xlsx") as archive:
        workbook = archive.read("xl/workbook.xml").decode()
        strings = "".join(archive.read(n).decode() for n in archive.namelist() if n.startswith("xl/worksheets/"))
        check("Typed Excel has separate store sheets and no formula cells", "Google Play reviews" in workbook and "Apple App Store reviews" in workbook and "<f>" not in strings)
    review_status()
    check("Actual agent reading notes bound to all stratified sample fingerprints", True)
    preserved = load(ROOT / "data/input/v1_preservation.json")
    changed = [name for name,digest in preserved.items() if not (PROJECT/name).exists() or sha(PROJECT/name) != digest]
    check("V1 files remain unchanged", not changed, dict(files_checked=len(preserved), changed=changed))
    document = (ROOT / "report_customer_feedback_v2.html").read_text(encoding="utf-8")
    check("Self-contained English report; no remote assets or private reply fields", '<html lang="en">' in document and 'src="http' not in document and 'href="https://fonts' not in document and '"developer_reply":' not in document and '"user_display_name":' not in document)
    dump(ROOT / "validation/static_results.json", dict(checked_at_utc=now(), passed=True, report_sha256=sha(ROOT / "report_customer_feedback_v2.html"), checks=checks))
    print(json.dumps(dict(passed=True, checks=len(checks), raw_verified_reviews=len(rows)), ensure_ascii=True))


def finalize():
    review_status()
    digest = sha(ROOT / "report_customer_feedback_v2.html")
    static = load(ROOT / "validation/static_results.json")
    browser = load(ROOT / "validation/browser_results.json")
    visual = load(ROOT / "validation/visual_inspection.json")
    assert static["passed"] and browser["passed"] and static["report_sha256"] == browser["report_sha256"] == digest
    assert visual["status"] == "reviewed" and visual["report_sha256"] == digest and "agent" in visual["reviewer"].lower()
    for path, expected in visual["screenshots"].items():
        assert sha(ROOT / path) == expected
    protected = load(ROOT / "data/input/v1_preservation.json")
    assert all((PROJECT / path).exists() and sha(PROJECT / path) == expected for path, expected in protected.items())
    text = f"# Checkpoint F - final review\n\nV2 is complete for the agreed scope: English delivery, separate store comparisons and BOCHK plus HSBC benchmarks, using the original 19 April-19 October window.\n\nDelivered report SHA-256: `{digest}`.\n\nStatic checks: {len(static['checks'])} passed. Real-browser assertions: {browser['assertions']} passed. All included comments were checked against their saved raw HTTP evidence; the 311 V1 English comments are unchanged. {len(protected)} original project files were verified unchanged.\n\nThe actual agent reading record is manual_review.json. The actual screenshot inspection record is validation/visual_inspection.json. These are agent checks, not independent human accuracy evaluation.\n\nBOCHK Apple pages 1-10 yielded 500 records; the page-11 request returned HTTP 400. The boundary failure is retained and explained, and does not establish exhaustive history. V1 and BOCHK have different capture dates. No deployment or manager communication was performed.\n\nThe complete artifact integrity manifest is manifest.json.\n"
    (ROOT / "checkpoint_F_final_review.md").write_text(text, encoding="utf-8")
    files = {p.relative_to(ROOT).as_posix(): dict(sha256=sha(p), bytes=p.stat().st_size) for p in sorted(ROOT.rglob("*")) if p.is_file() and p.name != "manifest.json" and "__pycache__" not in p.parts}
    dump(ROOT / "manifest.json", dict(schema_version=2, finalized_at_utc=now(), report_sha256=digest, files=files, limitations="Manifest excludes itself; hashes establish file integrity, not representativeness or accuracy."))
    print(json.dumps(dict(status="complete", report_sha256=digest, manifest_files=len(files)), ensure_ascii=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare", "build", "verify", "finalize"])
    parser.add_argument("--reuse-input", action="store_true")
    args = parser.parse_args()
    prepare(args.reuse_input) if args.stage == "prepare" else globals()[args.stage]()
