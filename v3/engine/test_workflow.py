"""Offline behavioral tests. Synthetic data stays in an explicitly named test root.

Optional --project-root reads the original case without changing it. No network,
no automatic annotation of real comments, and no production browser-result stubs.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import run_feedback as workflow
from apple_parser import entry_label, entries_from_feed, parse_feed
from build_report import build
from feedback_io import HK, SKILL, bounds, config_for, dump, load, require, sha, validate_row
from source_utils import parse_rpc
from verify_report import verify


def must_fail(function, contains):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            function()
    except (ValueError, KeyError) as error:
        require(contains.lower() in str(error).lower(), f"Unexpected failure: {error}")
    else:
        raise AssertionError("Invalid input was accepted: " + contains)


def init(root, apps=None):
    with contextlib.redirect_stdout(io.StringIO()):
        workflow.initialize(SimpleNamespace(root=root, apps=apps, since="2026-09-01", as_of="2026-09-30"))
    return config_for(root)


def synthetic_row(config, index, app_index, day, rating, text, english=True):
    app = config["apps"][app_index]
    instant = datetime.fromisoformat(day + "T12:00:00+08:00")
    return {"platform": "Google Play", "app": app["name"], "app_key": app["key"], "bank": app["bank"],
        "app_id": app["google_id"], "review_id": str(index), "record_key": f"google_play:{app['google_id']}:{index}",
        "title": None, "text": text, "rating": rating, "review_time_hk": instant.isoformat(),
        "review_time_utc": instant.astimezone(timezone.utc).isoformat(),
        "review_timestamp_seconds": instant.timestamp(), "source_url": "https://play.google.com/store/apps/details?id=" + app["google_id"],
        "collected_at_utc": "2026-10-19T00:00:00+00:00", "raw_response_workspace_path": "synthetic_evidence.txt",
        "language_status": "english" if english else "non_english", "language_method": "synthetic_fixture_only",
        "detected_language": "en" if english else "zh"}


def synthetic_checks(root):
    apps = copy.deepcopy(load(SKILL / "assets/apps.json"))
    for index, app in enumerate(apps):
        app.update(key="test_" + str(index), name="Synthetic " + str(index), bank="TEST ONLY",
            google_id=f"example.synthetic{index}", apple_id=str(9000000000 + index))
    dump(root / "test_apps.json", apps)
    batch = root / "synthetic_batch"
    config = init(batch, root / "test_apps.json")
    # This file is deliberately NOT a genuine app-store response.
    workflow.text_file(batch / "synthetic_evidence.txt", "SYNTHETIC TEST FIXTURE ONLY; never publish as a customer review.\n")
    body = '=TEST </script><img src=x onerror=alert(1)> transfer issue'
    rows = [synthetic_row(config, *values) for values in [
        (1, 0, "2026-09-01", 5, body), (2, 0, "2026-09-30", 4, "Easy to use"),
        (3, 1, "2026-09-20", 1, "Cannot login crash"), (4, 1, "2026-09-10", 2, body),
        (5, 0, "2026-08-31", 1, "Outside before"), (6, 0, "2026-10-01", 1, "Outside after"),
        (7, 0, "2026-09-05", 1, "Not English", False)]]
    for row in rows:
        validate_row(row, config, batch)
    bad = copy.deepcopy(rows[0]); bad["app_id"] = "wrong.package"
    must_fail(lambda: validate_row(bad, config, batch), "App ID mismatch")
    bad = copy.deepcopy(rows[0]); bad["review_time_hk"] = "2026-09-01T11:00:00+08:00"
    must_fail(lambda: validate_row(bad, config, batch), "HK time mismatch")
    bad = copy.deepcopy(rows[0]); bad["raw_response_workspace_path"] = "../not_allowed"
    must_fail(lambda: validate_row(bad, config, batch), "Path leaves")
    bad = copy.deepcopy(rows[0]); bad["raw_response_workspace_path"] = "not_present.body"
    must_fail(lambda: validate_row(bad, config, batch), "Raw response missing")
    dump(batch / "source_records.json", rows)
    dump(batch / "collection_summary.json", {"status": "imported", "raw_evidence_sha256": {"synthetic_evidence.txt": sha(batch / "synthetic_evidence.txt")},
        "limitations": "SYNTHETIC TEST FIXTURE, NOT CUSTOMER DATA"})
    workflow.prepare(batch, config); workflow.qa(batch, config); workflow.analyze(batch, config)
    selected = load(batch / "data/merged/master_english_six_months.json")
    require([r["review_id"] for r in selected] == ["2", "3", "4", "1"], "Window/language/order failed")
    qa = load(batch / "data/qa/summary.json")
    require(qa["repeated_text_rows"] == 2 and qa["rows"] == 4, "Repeated text was dropped")
    metrics = load(batch / "data/analysis/overall_benchmark.json")
    require([r["mean_rating"] for r in metrics] == [4.5, 1.5], "App configuration/means failed")
    must_fail(lambda: workflow.validate_review(batch), "pending")
    # ONLY synthetic fixture annotations; this branch never reads real reviews.
    review = load(batch / "manual_review.json")
    review.update(status="reviewed", reviewer="SYNTHETIC TEST ONLY", reviewed_at="2026-10-19")
    for item in review["judgements"]:
        item.update(rating_assessment="plausible", theme_assessment="limitation_noted",
            notes="Synthetic test annotation; not an actual customer review or a real reading record.")
    dump(batch / "manual_review.json", review)
    workflow.validate_review(batch)
    build(batch, config)
    with contextlib.redirect_stdout(io.StringIO()):
        require(verify(batch, config)["successful"], "Synthetic report failed")
    report = (batch / "report_customer_feedback.html").read_text(encoding="utf-8")
    require("低于 benchmark" in report and "-100.00" in report, "Old narrative was retained")
    require("SYNTHETIC TEST FIXTURE" in report and body not in report, "Unsafe text embedding")
    with ZipFile(batch / "data/merged/reviews_master.xlsx") as archive:
        ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        cells = sheet.findall(".//s:c", ns)
        found = [c for c in cells if c.findtext("s:is/s:t", namespaces=ns) == body]
        require(len(found) == 2 and all(c.attrib["t"] == "inlineStr" for c in found), "Formula-like text lost its type")
    raw = batch / "synthetic_evidence.txt"
    original = raw.read_bytes(); raw.write_bytes(original + b"TAMPERED")
    must_fail(lambda: verify(batch, config), "verification failed")
    raw.write_bytes(original)
    with contextlib.redirect_stdout(io.StringIO()):
        verify(batch, config)
    must_fail(lambda: workflow.prepare(batch, config), "already exists")
    require(not (batch / "final_manifest.json").exists(), "Unverified fixture was finalized")
    return {"synthetic_rows": len(rows), "selected_rows": len(selected), "invalid_input_cases": 4,
        "pending_review_blocked": True, "raw_tampering_detected": True, "fresh_names_dates_counts_and_reversed_narrative": True}


def original_case(root, project):
    originals = load(project / "data/merged_2026-10-19/master_english_six_months.json")
    parsed, formats = {}, set()
    for row in originals:
        path = project / row["raw_response_workspace_path"]
        if path not in parsed:
            text = path.read_text(encoding="utf-8")
            if row["platform"] == "Google Play":
                parsed[path] = parse_rpc(text)[0]; formats.add("google_rpc")
            else:
                parsed[path] = dict(entries_from_feed(parse_feed(text)))
                formats.add("apple_json" if text.lstrip().startswith("{") else "apple_atom")
        if row["platform"] == "Google Play":
            item = parsed[path][row["raw_item_index"]]
            require((item[0], item[4], item[2], item[5][0]) == (row["review_id"], row["text"], row["rating"], row["review_timestamp_seconds"]), "Google raw mismatch")
        else:
            item = parsed[path][row["raw_entry_index"]]
            require((item["id"]["label"], entry_label(item, "content"), int(item["im:rating"]["label"]), entry_label(item, "title")) ==
                (row["review_id"], row["text"], row["rating"], row["title"]), "Apple raw mismatch")
            require(datetime.fromisoformat(item["updated"]["label"]).timestamp() == row["review_timestamp_seconds"], "Apple raw time mismatch")
    batch = root / "real_changed_window"
    config = init(batch)
    workflow.import_snapshot(batch, config, SimpleNamespace(input=project / "data/merged_2026-10-19/master_english_six_months.json",
        evidence_root=project, coverage_note="Offline maintenance test; original English subset only; no fresh collection."))
    workflow.prepare(batch, config); workflow.qa(batch, config); workflow.analyze(batch, config)
    selected = load(batch / "data/merged/master_english_six_months.json")
    expected = [r["record_key"] for r in originals if "2026-09-01" <= r["review_time_hk"][:10] <= "2026-09-30"]
    require([r["record_key"] for r in selected] == expected, "Changed real window mismatch")
    require(0 < len(selected) < len(originals), "Changed window had no effect")
    require(load(batch / "manual_review.json")["status"] == "pending", "Real manual status was carried over")
    return {"raw_records_checked": len(originals), "raw_files_parsed": len(parsed), "formats": sorted(formats),
        "changed_window_rows": len(selected), "real_review_still_pending": True}


def atom_check():
    # Handwritten protocol fixture; no review text is presented as real.
    text = '''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:im="http://itunes.apple.com/rss">
      <entry><id>TEST</id><title>Fixture</title><content type="html">HTML</content><content type="text">Plain</content><im:rating>2</im:rating></entry></feed>'''
    entries = entries_from_feed(parse_feed(text))
    require(len(entries) == 1 and entry_label(entries[0][1], "content") == "Plain", "Atom text selection failed")
    return {"atom_fixture_text_preferred": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    root = args.work_root.resolve()
    require(not root.exists(), "Maintenance test needs a new scratch directory")
    root.mkdir(parents=True)
    result = {"successful": True, "network_requests": 0, "synthetic": synthetic_checks(root), "parser": atom_check()}
    if args.project_root:
        result["historical_case"] = original_case(root, args.project_root.resolve())
    dump(root / "test_results.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
