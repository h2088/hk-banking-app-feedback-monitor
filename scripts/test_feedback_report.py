"""Independent integrity checks for the offline Checkpoint E report.

Run after build_feedback_report.py. No network or third-party packages.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import unittest
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "data/checkpoint_D_analysis_2026-10-19"
REPORT = ROOT / "report_customer_feedback_2026-10-19.html"
RESULT = ANALYSIS / "report_static_test_results.json"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(name):
    with (ANALYSIS / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.assets = []
        self.links = []
        self.tables = []
        self.section_tables = {}
        self.section = None
        self.table = None
        self.row = None
        self.cell = None
        self.quote_count = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "section":
            self.section = attrs.get("id")
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag in {"script", "link", "img", "iframe", "audio", "video", "source"}:
            self.assets.extend(attrs[key] for key in ("src", "href", "srcset", "poster") if key in attrs)
        if tag == "article" and attrs.get("class") == "quote":
            self.quote_count += 1
        if tag == "table":
            self.table = []
        if tag == "tr" and self.table is not None:
            self.row = []
        if tag in {"th", "td"} and self.row is not None:
            self.cell = ""

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data

    def handle_endtag(self, tag):
        if tag in {"th", "td"} and self.cell is not None:
            self.row.append(self.cell.strip())
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
        if tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.section_tables.setdefault(self.section, []).append(self.table)
            self.table = None
        if tag == "section":
            self.section = None


class FeedbackReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = REPORT.read_text(encoding="utf-8")
        cls.data = json.loads(re.search(r"const DATA = (.*?);\nconst PAGE_SIZE", cls.html, re.S).group(1))
        cls.comments = cls.data["comments"]
        cls.raw = read_json(ROOT / "data/merged_2026-10-19/master_english_six_months.json")
        cls.labels = read_json(ANALYSIS / "comment_labels.json")
        cls.manifest = read_json(ANALYSIS / "report_build_manifest.json")
        cls.summary = read_json(ANALYSIS / "analysis_summary.json")
        cls.parser = ReportParser()
        cls.parser.feed(cls.html)

    def test_01_source_and_analysis_hashes_unchanged(self):
        self.assertEqual(hashlib.sha256(REPORT.read_bytes()).hexdigest(), self.manifest["report_sha256"])
        self.assertEqual(hashlib.sha256((ROOT / self.manifest["input"]).read_bytes()).hexdigest(), self.summary["input_sha256"])
        for name, expected in self.summary["artifact_sha256"].items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((ANALYSIS / name).read_bytes()).hexdigest(), expected)

    def test_02_all_original_comments_retained(self):
        self.assertEqual(len(self.comments), 311)
        self.assertEqual(len(self.comments), self.manifest["rows_embedded"])
        source = {row["record_key"]: row for row in self.raw}
        self.assertEqual(set(source), {row["record_key"] for row in self.comments})
        for row in self.comments:
            with self.subTest(record=row["record_key"]):
                for field in ("app_key", "review_id", "review_time_hk", "rating", "title", "text", "source_url", "raw_response_workspace_path"):
                    self.assertEqual(row[field], source[row["record_key"]][field])

    def test_03_labels_unchanged(self):
        labels = {row["record_key"]: row for row in self.labels}
        for row in self.comments:
            for field in ("rating_sentiment", "themes", "theme_labels", "short_text_for_theme_review"):
                self.assertEqual(row[field], labels[row["record_key"]][field])

    def test_04_dates_window_and_sort(self):
        dates = [datetime.fromisoformat(row["review_time_hk"]) for row in self.comments]
        self.assertEqual(dates, sorted(dates, reverse=True))
        self.assertTrue(all(datetime.fromisoformat("2026-04-19T00:00:00+08:00") <= date < datetime.fromisoformat("2026-10-20T00:00:00+08:00") for date in dates))
        self.assertEqual(dates[0].date().isoformat(), "2026-10-16")
        self.assertIn("样本最新评论：2026-10-16", self.html)

    def test_05_benchmark_and_rating_tables(self):
        tables = self.parser.section_tables["benchmark"]
        metrics = {row[0]: row[1:] for row in tables[0][1:]}
        distribution = {row[0]: row[1:] for row in tables[1][1:]}
        for index, (app, label) in enumerate((("sc_mobile", "SC Mobile"), ("hsbc_hk", "HSBC benchmark"))):
            rows = [row for row in self.raw if row["app_key"] == app]
            counts = Counter(row["rating"] for row in rows)
            self.assertEqual(int(metrics["评论数"][index]), len(rows))
            self.assertEqual(metrics["平均星级"][index], f"{sum(row['rating'] for row in rows) / len(rows):.4f}")
            for name, value in (("1–2 星比例", counts[1] + counts[2]), ("4–5 星比例", counts[4] + counts[5]), ("1 星比例", counts[1])):
                self.assertEqual(metrics[name][index], f"{value} / {len(rows)} ({value / len(rows) * 100:.2f}%)")
            self.assertEqual(distribution[label], [str(counts[rating]) for rating in range(1, 6)] + [str(len(rows))])

    def test_06_every_theme_and_denominator(self):
        displayed = {row[0]: row[1:] for row in self.parser.section_tables["themes"][0][1:]}
        self.assertEqual(len(displayed), 11)
        for theme in read_csv("themes_by_app.csv"):
            with self.subTest(app=theme["group"], theme=theme["theme"]):
                rows = [row for row in self.labels if row["app_key"] == theme["group"]]
                count = sum(theme["theme"] in row["themes"] for row in rows)
                self.assertEqual(count, int(theme["theme_mentions"]))
                index = 0 if theme["group"] == "sc_mobile" else 1
                self.assertEqual(displayed[theme["theme_label"]][index], f"{count} ({count / len(rows) * 100:.2f}%)")
        self.assertEqual(displayed["App stability / performance"], ["28 (28.57%)", "20 (9.39%)", "+19.18 pp"])

    def test_07_monthly_counts_and_rates(self):
        self.assertEqual(len(self.data["monthly"]), 7)
        self.assertEqual(sum(int(row["review_count"]) for row in self.data["monthly"]), 311)
        for month in self.data["monthly"]:
            rows = [row for row in self.raw if row["review_time_hk"].startswith(month["group"])]
            self.assertEqual(len(rows), int(month["review_count"]))
            for key, prefix in (("sc_mobile", "sc"), ("hsbc_hk", "hsbc")):
                app_rows = [row for row in rows if row["app_key"] == key]
                self.assertEqual(len(app_rows), int(month[prefix + "_review_count"]))
                self.assertAlmostEqual(sum(row["rating"] <= 2 for row in app_rows) / len(app_rows), float(month[prefix + "_negative_rate"]), places=6)

    def test_08_source_urls_and_raw_evidence_exist(self):
        expected_ids = {"sc_mobile": {"com.scb.breezebanking.hk", "445795688"}, "hsbc_hk": {"hk.com.hsbc.hsbchkmobilebanking", "1164066737"}}
        for row in self.comments:
            url = urlsplit(row["source_url"])
            self.assertEqual(url.scheme, "https")
            self.assertIn(url.hostname, {"play.google.com", "apps.apple.com"})
            self.assertTrue(any(app_id in row["source_url"] for app_id in expected_ids[row["app_key"]]))
            evidence = (ROOT / row["raw_response_workspace_path"]).resolve()
            self.assertTrue(evidence.is_relative_to(ROOT))
            self.assertTrue(evidence.is_file())

    def test_09_html_structure_and_offline_assets(self):
        self.assertEqual(len(self.parser.ids), len(set(self.parser.ids)))
        self.assertTrue(set(self.manifest["sections"]).issubset(self.parser.ids))
        self.assertEqual(self.parser.assets, [])
        self.assertFalse(re.search(r"@import|url\(\s*['\"]?https?://|\bfetch\s*\(|XMLHttpRequest|WebSocket", self.html, re.I))
        for link in self.parser.links:
            url = urlsplit(link)
            if url.scheme or link.startswith("#"):
                continue
            self.assertTrue((ROOT / unquote(url.path)).is_file(), link)
        self.assertIn('<meta charset="utf-8">', self.html)

    def test_10_privacy_and_no_platform_reporting(self):
        self.assertFalse(self.manifest["platform_split_in_metrics"])
        for row in self.comments:
            self.assertNotIn("user_display_name", row)
            self.assertNotIn("developer_reply", row)
            self.assertNotIn("platform", row)
        self.assertNotIn('id="platformFilter"', self.html)
        self.assertNotIn("platform", self.parser.section_tables["benchmark"][0][0])

    def test_11_short_text_definitions(self):
        body_short = sum(len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", row["text"])) <= 4 for row in self.raw)
        analysis_short = sum(row["short_text_for_theme_review"] for row in self.labels)
        self.assertEqual((body_short, analysis_short), (105, 83))
        self.assertEqual((self.manifest["short_body_count"], self.manifest["short_analysis_count"]), (105, 83))
        self.assertIn("仅正文计词有 105 条", self.html)
        self.assertIn("短文本标记为 83 条", self.html)

    def test_12_quote_cards_not_duplicated(self):
        quotes = read_csv("representative_quotes.csv")
        unique = []
        seen = set()
        for quote in quotes:
            if quote["review_id"] not in seen:
                unique.append(quote)
                seen.add(quote["review_id"])
        self.assertEqual(self.parser.quote_count, min(8, len(unique)))
        section = re.search(r'<section id="quotes">(.*?)</section>', self.html, re.S).group(1)
        cards = re.findall(r"<article.*?</article>", section, re.S)
        self.assertEqual(len(cards), len(set(cards)))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FeedbackReportTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    payload = {"report_sha256": hashlib.sha256(REPORT.read_bytes()).hexdigest(), "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "successful": result.wasSuccessful(), "network_requests": 0, "browser_test": "separate: test_feedback_report_browser.py"}
    RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.exit(0 if result.wasSuccessful() else 1)
