"""Offline regression tests for field preservation and typed spreadsheet output."""

import csv
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import merge_reviews as merge


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dataset = "data/source"
        (self.root / self.dataset).mkdir(parents=True)
        (self.root / self.dataset / "page.body").write_bytes(b"fixture")
        self.original = {
            "source": "Google Play", "app": "SC Mobile Hong Kong",
            "app_id": "com.scb.breezebanking.hk", "review_id": "000012345678901234567890",
            "review_time_hk": "2026-10-16T09:25:03+08:00",
            "review_time_utc": "2026-10-16T01:25:03+00:00",
            "review_timestamp_seconds": 1792113903, "rating": 1,
            "text": '=not_a_formula\r\n原文 "test", 🙂\t',
            "user_display_name": "+Not a formula", "language_status": "english",
            "language_probabilities": {"en": 0.999},
            "within_six_month_window": True, "on_or_before_cutoff": True,
            "raw_response_file": "page.body",
        }

    def row(self):
        return merge.normalize(self.original, "google_play", "Google Play", self.dataset, 0, self.root)

    def test_original_fields_and_provenance_unchanged(self):
        before = deepcopy(self.original)
        row = self.row()
        self.assertEqual(self.original, before)
        for key, value in before.items():
            self.assertEqual(row[key], value)
            self.assertIs(type(row[key]), type(value))
        self.assertIsNone(row["title"])
        self.assertEqual(row["raw_response_workspace_path"], "data/source/page.body")
        self.assertEqual(row["source_row_index"], 0)
        merge.check_row(row)

    def test_evidence_paths_cannot_escape_source(self):
        (self.root / "outside.body").write_bytes(b"outside")
        with self.assertRaisesRegex(ValueError, "escapes"):
            merge.evidence_path(self.root, self.dataset, "../../outside.body")

    def test_missing_evidence_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing evidence"):
            merge.evidence_path(self.root, self.dataset, "missing.body")

    def test_numeric_ids_rejected(self):
        self.original["review_id"] = 123
        with self.assertRaisesRegex(ValueError, "strings"):
            self.row()

    def test_undocumented_source_fields_not_silently_lost(self):
        self.original["unexpected_new_source_field"] = "keep me"
        with self.assertRaisesRegex(ValueError, "Undocumented"):
            self.row()

    def test_time_boundaries_and_false_flags(self):
        for moment, in_window, before_cutoff in [
            ("2026-04-18T23:59:59+08:00", False, True),
            ("2026-04-19T00:00:00+08:00", True, True),
            ("2026-10-19T23:59:59+08:00", True, True),
            ("2026-10-20T00:00:00+08:00", False, False),
        ]:
            row = self.row()
            instant = merge.datetime.fromisoformat(moment)
            row.update(review_time_hk=moment, review_time_utc=instant.astimezone(merge.timezone.utc).isoformat(),
                       review_timestamp_seconds=int(instant.timestamp()),
                       within_six_month_window=in_window, on_or_before_cutoff=before_cutoff)
            merge.check_row(row)
            row["within_six_month_window"] = not in_window
            with self.assertRaisesRegex(ValueError, "Window flag"):
                merge.check_row(row)

    def test_sorting_subsets_and_identical_text_kept_across_platforms(self):
        google = self.row()
        apple = dict(google, record_key="apple:445795688:123", platform="Apple App Store", app_id="445795688")
        old = dict(google, record_key="google_play:old:old", review_timestamp_seconds=1, within_six_month_window=False)
        non_english = dict(google, record_key="google_play:other:other", language_status="mixed")
        rows = merge.sort_rows([old, google, apple, non_english])
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[-1], old)
        subsets = merge.make_subsets(rows)
        self.assertEqual(len(subsets["master_english_six_months"]), 2)
        self.assertEqual(len(subsets["master_english_all"]), 3)
        self.assertEqual(len(subsets["master_six_months_all"]), 3)

    def test_csv_json_xlsx_typed_round_trip_and_formula_safety(self):
        row = self.row()
        subsets = merge.make_subsets([row])
        for name, rows in subsets.items():
            merge.dump_json(self.root / f"{name}.json", rows)
            merge.write_csv(self.root / f"{name}.csv", rows)
        merge.write_xlsx(self.root / "reviews_master.xlsx", subsets, [])
        results = merge.verify_outputs(self.root, subsets)
        self.assertTrue(all(r["xlsx_typed_cell_round_trip"] for r in results.values()))
        with ZipFile(self.root / "reviews_master.xlsx") as archive:
            xml = ET.fromstring(archive.read("xl/worksheets/sheet2.xml"))
            self.assertFalse(list(xml.iter(merge.tag("f"))))
        with (self.root / "master_all_reviews.csv").open(encoding="utf-8-sig", newline="") as handle:
            csv_row = list(csv.DictReader(handle))[0]
        self.assertEqual(csv_row["review_id"], self.original["review_id"])
        self.assertEqual(csv_row["text"], self.original["text"])

    def test_excel_column_names(self):
        self.assertEqual([merge.column_name(n) for n in [1, 26, 27, 45, 52, 53, 703]], ["A", "Z", "AA", "AS", "AZ", "BA", "AAA"])


if __name__ == "__main__":
    unittest.main()
