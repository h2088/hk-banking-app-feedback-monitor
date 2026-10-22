"""Independent data/hash/HTML verification, using data-derived expectations."""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from zipfile import ZipFile

from feedback_io import bounds, dump, load, require, safe_path, sha, sorted_rows, validate_row
from theme_rules import THEMES


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.assets, self.links, self.tables = [], [], [], {}
        self.table, self.row, self.cell = None, None, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag in {"script", "link", "img", "iframe", "audio", "video", "source"}:
            self.assets.extend(attrs[k] for k in ("src", "href", "srcset") if k in attrs)
        if tag == "table":
            self.table = attrs.get("id")
            self.tables[self.table] = []
        if tag == "tr" and self.table:
            self.row = []
        if tag in {"td", "th"} and self.row is not None:
            self.cell = ""

    def handle_data(self, value):
        if self.cell is not None:
            self.cell += value

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(self.cell)
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.tables[self.table].append(self.row)
            self.row = None
        if tag == "table":
            self.table = None


def verify(root, config):
    report = root / "report_customer_feedback.html"
    manifest = load(root / "build_manifest.json")
    analysis = load(root / "data/analysis/summary.json")
    rows = load(root / "data/merged/master_english_six_months.json")
    labels = load(root / "data/analysis/comment_labels.json")
    document = report.read_text(encoding="utf-8")
    parser = Parser()
    parser.feed(document)
    payload = json.loads(re.search(r"const DATA = (.*?);\nconst PAGE_SIZE", document, re.S).group(1))
    checks = []
    def check(name, function):
        try:
            function()
            checks.append({"name": name, "passed": True})
        except Exception as error:
            checks.append({"name": name, "passed": False, "detail": str(error)})

    def hashes():
        require(sha(report) == manifest["report_sha256"], "Report hash mismatch")
        require(sha(root / "config.json") == manifest["config_sha256"], "Config changed since build")
        require(sha(root / "manual_review.json") == manifest["manual_review_sha256"], "Review changed since build")
        require(sha(root / "data/analysis/summary.json") == manifest["analysis_summary_sha256"], "Summary changed since build")
        merge = load(root / "data/merged/merge_manifest.json")
        require(sha(root / "source_records.json") == merge["source_sha256"], "Source changed")
        require(sha(root / "config.json") == merge["config_sha256"], "Config changed since merge")
        for directory, item in (("merged", merge), ("qa", load(root / "data/qa/summary.json")), ("analysis", analysis)):
            for name, digest in item["artifact_sha256"].items():
                require(sha(root / "data" / directory / name) == digest, "Artifact changed: " + directory + "/" + name)
        require(sha(root / "data/merged/master_english_six_months.json") == manifest["input_sha256"] == analysis["input_sha256"], "Input changed")
        collection = load(root / "collection_summary.json")
        if collection["status"] == "imported":
            for name, digest in collection["raw_evidence_sha256"].items():
                require(sha(safe_path(root, name)) == digest, "Imported evidence changed")
        else:
            for path in (root / "data/raw").rglob("*.http.json"):
                meta = load(path)
                if "sha256" in meta:
                    body = path.with_name(path.name.removesuffix(".http.json") + ".body")
                    require(sha(body) == meta["sha256"], "HTTP body changed")
    check("immutable input artifacts and raw hashes", hashes)

    def originals():
        source = {r["record_key"]: r for r in load(root / "source_records.json")}
        comments = payload["comments"]
        require(len(rows) == len(labels) == len(comments) == manifest["rows"], "Count mismatch")
        require([r["record_key"] for r in comments] == [r["record_key"] for r in rows], "Embedded record set/order mismatch")
        for row, rendered, label in zip(rows, comments, labels):
            validate_row(row, config, root, require_english=True)
            for field in ("record_key", "app_key", "review_id", "review_time_hk", "title", "text", "rating", "source_url", "raw_response_workspace_path"):
                require(row.get(field) == rendered.get(field) == source[row["record_key"]].get(field), "Original source mismatch: " + field)
            for field in ("themes", "rating_sentiment", "theme_labels", "short_text_for_theme_review"):
                require(label[field] == rendered[field], "Label mismatch: " + field)
            require(not {"user_display_name", "developer_reply", "platform"} & set(rendered), "Unneeded personal/source fields embedded")
        require(rows == sorted_rows(rows), "Not newest-first")
    check("original comments labels dates and privacy", originals)

    def csv_and_xlsx():
        with (root / "data/merged/master_english_six_months.csv").open(encoding="utf-8-sig", newline="") as handle:
            csv_rows = list(csv.DictReader(handle))
        require(len(csv_rows) == len(rows), "CSV count mismatch")
        for a, b in zip(rows, csv_rows):
            for field in ("record_key", "text", "review_time_hk", "review_id"):
                require(a[field] == b[field], "CSV original mismatch")
            require((a.get("title") or "") == b["title"] and a["rating"] == int(b["rating"]), "CSV title/rating mismatch")
        with ZipFile(root / "data/merged/reviews_master.xlsx") as archive:
            require(archive.testzip() is None, "Corrupt XLSX")
            require("xl/workbook.xml" in archive.namelist(), "Workbook missing")
            require(all(b"<f>" not in archive.read(name) for name in archive.namelist() if name.startswith("xl/worksheets/")), "Formula injected into XLSX")
    check("CSV and typed workbook integrity", csv_and_xlsx)

    def benchmark():
        displayed = {r[0]: r[1:] for r in parser.tables["benchmarkTable"][1:]}
        distribution = {r[0]: r[1:] for r in parser.tables["ratingTable"][1:]}
        apps = sorted(config["apps"], key=lambda a: a["role"] != "primary")
        for index, app in enumerate(apps):
            part = [r for r in rows if r["app_key"] == app["key"]]
            n = len(part)
            require(displayed["评论数"][index] == str(n), "Displayed app count")
            require(displayed["平均星级"][index] == (f"{sum(r['rating'] for r in part)/n:.4f}" if n else "无样本"), "Displayed mean")
            counts = Counter(r["rating"] for r in part)
            for name, count in (("1–2 星比例", counts[1]+counts[2]), ("4–5 星比例", counts[4]+counts[5]), ("1 星比例", counts[1])):
                expected = f"{count} / {n} ({count/n*100:.2f}%)" if n else "0 / 0（无样本）"
                require(displayed[name][index] == expected, "Displayed denominator/rate")
            require(distribution[app["name"]] == [str(counts[i]) for i in range(1,6)] + [str(n)], "Star distribution")
    check("independent benchmark arithmetic", benchmark)

    def themes():
        displayed = {r[0]: r[1:] for r in parser.tables["themeTable"][1:]}
        require(len(displayed) == len(THEMES), "Theme count mismatch")
        apps = sorted(config["apps"], key=lambda a: a["role"] != "primary")
        for key, (name, _) in THEMES.items():
            rates = []
            for index, app in enumerate(apps):
                part = [r for r in labels if r["app_key"] == app["key"]]
                n, count = len(part), sum(key in r["themes"] for r in part)
                rates.append(count/n if n else None)
                require(displayed[name][index] == (f"{count} / {n} ({count/n*100:.2f}%)" if n else "0 / 0（无样本）"), "Theme count/denominator")
            require(displayed[name][2] == (f"{(rates[0]-rates[1])*100:+.2f} pp" if None not in rates else "无可比样本"), "Theme gap")
    check("every theme and denominator", themes)

    def monthly():
        require(sum(m["review_count"] for m in payload["monthly"]) == len(rows), "Monthly total")
        for month in payload["monthly"]:
            part = [r for r in rows if r["review_time_hk"].startswith(month["month"])]
            require(month["review_count"] == len(part), "Monthly count")
            for app in config["apps"]:
                ap = [r for r in part if r["app_key"] == app["key"]]
                item = month["apps"][app["key"]]
                require(item["review_count"] == len(ap), "App monthly count")
                rate = round(sum(r["rating"] <= 2 for r in ap)/len(ap),6) if ap else None
                require(item["negative_rate_rating_1_2"] == rate, "App monthly low-star rate")
    check("monthly volume and app low-star rates", monthly)

    def structure():
        require(len(parser.ids) == len(set(parser.ids)), "Duplicate HTML ID")
        require(not parser.assets and not re.search(r"\bfetch\s*\(|XMLHttpRequest|WebSocket|@import|url\(\s*['\"]?https?://", document), "External asset/request")
        require('id="platformFilter"' not in document, "Unexpected platform split")
        for link in parser.links:
            url = urlsplit(link)
            if not url.scheme and url.path:
                require(safe_path(root, unquote(url.path)).is_file(), "Missing HTML relative link")
        require(config["since"] in document and config["as_of"] in document, "Window not displayed")
        if rows:
            require("样本最新评论：" + rows[0]["review_time_hk"][:10] in document, "Latest observation mislabeled")
    check("offline structure links and declared scope", structure)
    result = {"successful": all(c["passed"] for c in checks), "checks_run": len(checks),
              "report_sha256": sha(report), "checks": checks, "network_requests": 0}
    dump(root / "static_test_results.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    require(result["successful"], "Report verification failed; see static_test_results.json")
    return result
