"""Independent arithmetic, immutable artifacts and exact raw-source verification."""
import csv
import json
import re
from datetime import datetime
from zipfile import ZipFile
from xml.etree import ElementTree as ET
from feedback_io import bounds, dump, fingerprints, load, now, require, safe_path, sha, sorted_rows, validate_row
from apple_parser import parse_feed, entries_from_feed, entry_label
from source_utils import parse_rpc, nested
from run_feedback import STORES, guard, month_buckets, validate_review


def verify(root, config):
    guard(root)
    checks = []

    def check(name, condition):
        require(condition, name)
        checks.append(dict(name=name, passed=True))

    finalized = (root / "manifest.json").exists()
    if finalized:
        manifest = load(root / "manifest.json")
        check("Finalized file hashes (read-only recheck)", all(sha(safe_path(root, name)) == info["sha256"] for name,info in manifest["files"].items()))

    report = root / "report_customer_feedback.html"
    document = report.read_text(encoding="utf-8")
    payload = json.loads(re.search(r'<script id="reportData" type="application/json">(.*?)</script>', document, re.S).group(1))
    build = load(root / "build_manifest.json")
    check("Exact build hashes", all(sha(root / name) == build[key] for name,key in (("report_customer_feedback.html","report_sha256"),("config.json","config_sha256"),("manual_review.json","manual_review_sha256"),("data/analysis/summary.json","analysis_sha256"),("data/reviews_master.xlsx","workbook_sha256"))))
    for name, digest in load(root / "data/analysis/summary.json")["files"].items():
        require(sha(safe_path(root, name)) == digest, "Analysis artifact changed: " + name)
    collection = load(root / "collection_summary.json")
    if collection["status"] == "imported":
        check("Imported raw hashes", all(sha(safe_path(root, p)) == h for p,h in collection["raw_evidence_sha256"].items()))
    else:
        check("Successful bounded capture", collection["status"] == "collected")
        for path in (root / "data/raw").rglob("*.http.json"):
            meta = load(path)
            if "sha256" in meta:
                require(sha(path.with_name(path.name.removesuffix(".http.json") + ".body")) == meta["sha256"], "Captured raw changed")
    rows = load(root / "data/analysis/comment_labels.json")
    source = {r["record_key"]:r for r in reversed(load(root / "source_records.json"))}
    start, end = bounds(config)
    check("Unique IDs and newest-first order", len({r["record_key"] for r in rows}) == len(rows) and rows == sorted_rows(rows))
    cache = {}
    for row, embedded in zip(rows, payload["rows"]):
        validate_row(row, config, root)
        require(start.timestamp() <= row["review_timestamp_seconds"] < end.timestamp() and row["analysis_language"] in {"english","chinese","mixed"} and row["text"].strip(), "Invalid included subset")
        require(fingerprints(row) == fingerprints(source[row["record_key"]]), "Original input changed")
        for field in embedded:
            require(row.get(field) == embedded[field], "Embedded source/label differs: " + field)
        require(not {"user_display_name", "developer_reply", "analysis_language"} & set(embedded), "Unneeded source/language metadata embedded")
        path = safe_path(root, row["raw_response_workspace_path"])
        if path not in cache:
            cache[path] = parse_rpc(path.read_text(encoding="utf-8"))[0] if row["platform"] == STORES[0] else dict(entries_from_feed(parse_feed(path.read_text(encoding="utf-8"))))
        if row["platform"] == STORES[0]:
            item = cache[path][row["raw_item_index"]]
            actual = (nested(item,[0]), nested(item,[4]), nested(item,[2]), nested(item,[5,0]))
            expected = (row["review_id"],row["text"],row["rating"],row["review_timestamp_seconds"])
        else:
            item = cache[path][row["raw_entry_index"]]
            actual = (item["id"]["label"],entry_label(item,"title"),entry_label(item,"content"),int(item["im:rating"]["label"]),datetime.fromisoformat(item["updated"]["label"]).timestamp())
            expected = (row["review_id"],row["title"],row["text"],row["rating"],row["review_timestamp_seconds"])
        require(actual == expected, "Raw evidence mismatch: " + row["record_key"])
    check("Every embedded original matches input and exact raw HTTP", len(rows) == len(payload["rows"]) == payload["summary"]["included_records"])
    for key, filename in (("groups","store_benchmarks"),("themes","themes_by_store_bank"),("monthly","monthly_by_store_bank"),("monthly_totals","monthly_feedback_monitoring"),("deltas","benchmark_deltas")):
        check("Embedded " + key + " equals saved analysis", payload[key] == load(root / ("data/analysis/"+filename+".json")) and all("language_scope" not in r for r in payload[key]))

    def group_check(g, members):
        n, low = len(members), sum(r["rating"] <= 2 for r in members)
        require(g["review_count"] == n and g["negative_count_rating_1_2"] == low, "Combined denominator/count")
        require(g["negative_rate_rating_1_2"] == (round(low/n,6) if n else None), "Combined rate")
        require(g["mean_rating"] == (round(sum(r["rating"] for r in members)/n,4) if n else None), "Combined mean")

    for g in payload["groups"]:
        group_check(g, [r for r in rows if r["platform"] == g["platform"] and r["app_key"] == g["app_key"]])
    check("Bank/store metrics independently recomputed", len(payload["groups"]) == 2*len(config["apps"]))
    for t in payload["themes"]:
        members = [r for r in rows if r["platform"] == t["platform"] and r["app_key"] == t["app_key"]]
        hits = [r for r in members if t["theme"] in r["themes"]]
        require(t["review_count"] == len(members) and t["theme_mentions"] == len(hits) and t["theme_negative_count"] == sum(r["rating"]<=2 for r in hits), "Topic counts")
        require(t["theme_mention_rate"] == (round(len(hits)/len(members),6) if members else None), "Topic denominator")
    check("Overlapping topic denominators", len(payload["themes"]) == 2*len(config["apps"])*len(payload["theme_names"]))
    for m in payload["monthly"]:
        group_check(m, [r for r in rows if r["platform"] == m["platform"] and r["app_key"] == m["app_key"] and r["review_time_hk"].startswith(m["month_hk"])])
        require(dict(month_buckets(config))[m["month_hk"]] == m["partial_calendar_month"], "Partial month marker")
    for m in payload["monthly_totals"]:
        members = [r for r in rows if r["platform"] == m["platform"] and r["review_time_hk"].startswith(m["month_hk"])]
        require(m["review_count"] == len(members), "Chart total")
        for app in config["apps"]:
            part = [r for r in members if r["app_key"] == app["key"]]
            low = sum(r["rating"]<=2 for r in part)
            require(m[app["key"]+"_review_count"] == len(part) and m[app["key"]+"_low_star_count"] == low and m[app["key"]+"_low_star_rate"] == (round(low/len(part),6) if part else None), "Chart bank count/rate")
    check("Dynamic months include empty/partial buckets", len(payload["monthly"]) == len(month_buckets(config))*2*len(config["apps"]) and len(payload["monthly_totals"]) == len(month_buckets(config))*2 and sum(m["review_count"] for m in payload["monthly_totals"]) == len(rows))
    for d in payload["deltas"]:
        p = next(g for g in payload["groups"] if g["platform"] == d["platform"] and g["app_key"] == d["primary_key"])
        b = next(g for g in payload["groups"] if g["platform"] == d["platform"] and g["app_key"] == d["benchmark_key"])
        valid = p["review_count"] and b["review_count"]
        require(d["low_star_rate_difference_percentage_points"] == (round(100*(p["negative_rate_rating_1_2"]-b["negative_rate_rating_1_2"]),4) if valid else None), "Benchmark low-star gap")
        require(d["mean_rating_difference_sc_minus_benchmark"] == (round(p["mean_rating"]-b["mean_rating"],4) if valid else None), "Benchmark mean gap")
    check("All within-store benchmark differences", len(payload["deltas"]) == 2*(len(config["apps"])-1))
    with (root / "data/merged/master_bilingual_six_months.csv").open(encoding="utf-8-sig",newline="") as f:
        exported = list(csv.DictReader(f))
    check("CSV Unicode originals and order", len(exported) == len(rows) and all(c["record_key"] == r["record_key"] and c["text"] == r["text"] and c["title"] == (r.get("title") or "") for c,r in zip(exported,rows)))
    with ZipFile(root / "data/reviews_master.xlsx") as z:
        ns = {"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        names = [n.attrib["name"] for n in ET.fromstring(z.read("xl/workbook.xml")).findall("m:sheets/m:sheet",ns)]
        counts = [len(ET.fromstring(z.read(f"xl/worksheets/sheet{i}.xml")).findall("m:sheetData/m:row",ns))-1 for i in range(1,9)]
        expected_counts = [sum(r["platform"] == s for r in rows) for s in STORES] + [len(payload[k]) for k in ("groups","deltas","themes","monthly","monthly_totals","coverage")]
        check("Typed workbook counts and separate stores", names[:2] == ["Google Play reviews","Apple App Store reviews"] and counts == expected_counts and all(b"<f>" not in z.read(n) for n in z.namelist() if n.startswith("xl/worksheets/")))
    validate_review(root)
    check("Actual source-bound reading judgments", True)
    check("English combined offline report and monthly chart", '<html lang="en">' in document and 'id="languageFilter"' not in document and 'id="monthlyChart"' in document and not re.search(r'<(?:script|img)[^>]+src=|<link[^>]+href=|\bfetch\s*\(|XMLHttpRequest|WebSocket',document) and config["since"] in document and config["as_of"] in document)
    result = dict(passed=True, checked_at_utc=now(), report_sha256=sha(report), raw_verified_reviews=len(rows), checks=checks)
    # A completed batch is immutable; report a new audit to stdout only.
    if not finalized:
        dump(root / "validation/static_results.json", result)
    print(json.dumps(dict(passed=True, checks=len(checks), raw_verified_reviews=len(rows))))
    return result
