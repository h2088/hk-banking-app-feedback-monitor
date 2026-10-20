"""Offline Checkpoint F audit. Writes only its own derived review result.

Run test_feedback_report.py first. Browser results are reused only when their
report hash still matches. This is not a live source or classifier evaluation.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MERGED = ROOT / "data/merged_2026-10-19"
QA = ROOT / "data/checkpoint_C_qa_2026-10-19"
ANALYSIS = ROOT / "data/checkpoint_D_analysis_2026-10-19"
OUTPUT = ROOT / "data/checkpoint_F_review_2026-10-19/final_review_results.json"
REPORT = ROOT / "report_customer_feedback_2026-10-19.html"
DOCUMENTS = [
    "plan.md", "checkpoint_A_source_feasibility.md",
    "checkpoint_B_data_collection.md", "checkpoint_C_data_qa.md",
    "checkpoint_D_customer_feedback_analysis.md", "checkpoint_E_build_test.md",
    "checkpoint_F_final_review.md", "handover.md",
]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def local_path(path, base=ROOT):
    require(not re.match(r"^[A-Za-z]:", path), f"Absolute drive path: {path}")
    require(not Path(path).is_absolute(), f"Absolute path: {path}")
    target = (base / path).resolve()
    require(target.is_relative_to(ROOT), f"Path outside package: {path}")
    return target


def main():
    # The result path is created before auditing document links that reference it.
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "checkpoint": "F",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "report_sha256": sha256(REPORT),
        "scope": "English customer reviews; SC Mobile vs HSBC; overall app-level",
        "network_requests": 0,
        "checks": [],
        "verified_hashes": {},
        "facts": {},
    }

    def check(name, function):
        try:
            detail = function()
            result["checks"].append({"name": name, "passed": True, "detail": detail})
        except Exception as error:
            result["checks"].append({"name": name, "passed": False, "detail": str(error)})

    def verify_hashes(base, expected):
        for name, digest in expected.items():
            path = local_path(name, base)
            actual = sha256(path)
            require(actual == digest, f"Hash mismatch: {path.relative_to(ROOT)}")
            result["verified_hashes"][path.relative_to(ROOT).as_posix()] = actual
        return {"files_verified": len(expected)}

    merge = read_json(MERGED / "merge_report.json")
    qa = read_json(QA / "qa_summary.json")
    analysis = read_json(ANALYSIS / "analysis_summary.json")
    rows = read_json(MERGED / "master_english_six_months.json")
    labels = read_json(ANALYSIS / "comment_labels.json")
    check("final source export hashes", lambda: verify_hashes(
        ROOT, {item["file"]: item["sha256"] for item in merge["input_files"]}))
    check("merged artifact hashes", lambda: verify_hashes(MERGED, merge["artifact_hashes_sha256"]))
    check("QA artifact hashes", lambda: verify_hashes(QA, qa["artifact_sha256"]))
    check("analysis artifact hashes", lambda: verify_hashes(ANALYSIS, analysis["artifact_sha256"]))

    def verify_tests():
        manifest = read_json(ANALYSIS / "report_build_manifest.json")
        static = read_json(ANALYSIS / "report_static_test_results.json")
        browser = read_json(ANALYSIS / "report_browser_test_results.json")
        digest = result["report_sha256"]
        require(all(item["report_sha256"] == digest for item in (manifest, static, browser)),
                "Report changed since build/static/browser test")
        require(static["successful"] and static["tests_run"] == 12
                and static["failures"] == 0 and static["errors"] == 0, "Static test failure")
        require(browser["checks_run"] == browser["passed"] == len(browser["checks"]) == 1398
                and not browser["failed"] and all(item["passed"] for item in browser["checks"])
                and browser["browser_exit_code"] == 0, "Browser assertion failure")
        require(sha256(local_path(manifest["input"])) == manifest["input_sha256"]
                == analysis["input_sha256"] == qa["analysis_input_sha256"], "Input mismatch")
        return {"static_tests": 12, "browser_assertions": 1398,
                "browser_rerun_in_F": False, "reason": "Unchanged tested HTML hash"}

    check("build and test evidence matches delivered HTML", verify_tests)

    def verify_csv_and_facts():
        with (MERGED / "master_english_six_months.csv").open(encoding="utf-8-sig", newline="") as handle:
            csv_rows = list(csv.DictReader(handle))
        require(len(rows) == len(csv_rows) == len(labels) == 311, "Row count mismatch")
        require([row["record_key"] for row in csv_rows] == [row["record_key"] for row in rows],
                "CSV/JSON key order mismatch")
        for row, csv_row in zip(rows, csv_rows):
            for field in ("text", "review_time_hk", "app_key", "review_id", "source_url"):
                require(str(row[field]) == csv_row[field], f"CSV value mismatch: {field}")
            require((row["title"] or "") == csv_row["title"], "CSV title mismatch")
            require(row["rating"] == int(csv_row["rating"]), "CSV rating mismatch")
        all_rows = read_json(MERGED / "master_all_reviews.json")
        require(len(all_rows) == 5278, "All-language sample size mismatch")
        require(max(row["review_time_hk"] for row in all_rows)[:10] == "2026-10-17", "All-language latest date")
        require(max(row["review_time_hk"] for row in rows)[:10] == "2026-10-16", "English latest date")
        counts = Counter(row["app_key"] for row in rows)
        require(counts == {"sc_mobile": 98, "hsbc_hk": 213}, "App sample sizes")
        facts = result["facts"]
        facts.update({"english_rows": len(rows), "all_language_rows": len(all_rows),
                      "english_latest_hk": "2026-10-16", "all_language_latest_hk": "2026-10-17",
                      "start_inclusive_hk": qa["date_window"]["start_inclusive_hk"],
                      "end_exclusive_hk": qa["date_window"]["end_exclusive_hk"], "apps": {}})
        for app, count in counts.items():
            app_rows = [row for row in rows if row["app_key"] == app]
            low = sum(row["rating"] <= 2 for row in app_rows)
            facts["apps"][app] = {"reviews": count,
                "mean_rating": round(sum(row["rating"] for row in app_rows) / count, 4),
                "low_star_count": low, "low_star_percent": round(100 * low / count, 2)}
        return {"csv_json_rows_matched": len(rows), "facts": facts}

    check("CSV JSON and final coverage facts", verify_csv_and_facts)

    def verify_provenance():
        sources = {item["file"]: read_json(local_path(item["file"])) for item in merge["input_files"]}
        evidence = set()
        for row in rows:
            original = sources[row["source_json_file"]][row["source_row_index"]]
            for field in ("app_id", "review_id", "review_time_hk", "rating", "text", "title"):
                require(row.get(field) == original.get(field), f"Source field mismatch: {field}")
            path = local_path(row["raw_response_workspace_path"])
            require(path.is_file(), f"Missing raw response: {path.relative_to(ROOT)}")
            evidence.add(path.relative_to(ROOT).as_posix())
            if row.get("raw_items_workspace_path"):
                require(local_path(row["raw_items_workspace_path"]).is_file(), "Missing decoded evidence")
        result["raw_evidence_sha256_at_review"] = {name: sha256(local_path(name)) for name in sorted(evidence)}
        return {"rows_traced_to_source_export": len(rows), "unique_raw_responses": len(evidence),
                "note": "Raw response hashes recorded now; not an independent live-source verification"}

    check("row provenance and saved raw evidence", verify_provenance)

    def verify_markdown():
        links = 0
        for name in DOCUMENTS:
            text = (ROOT / name).read_text(encoding="utf-8")
            for match in re.finditer(r"\[[^\]]+\]\((?:<([^>]+)>|([^\)]+))\)", text):
                link = match.group(1) or match.group(2)
                require(not re.match(r"^/?[A-Za-z]:", link), f"Nonportable link in {name}: {link}")
                url = urlsplit(link)
                if url.scheme or not url.path:
                    continue
                path = local_path(unquote(url.path), (ROOT / name).parent)
                require(path == OUTPUT or path.exists(), f"Missing link in {name}: {link}")
                links += 1
        return {"documents": len(DOCUMENTS), "local_links_checked": links,
                "method": "Static path resolution; not a relocated-folder browser test"}

    check("delivery document relative links", verify_markdown)

    def verify_theme_document():
        document = (ROOT / "checkpoint_D_customer_feedback_analysis.md").read_text(encoding="utf-8")
        with (ANALYSIS / "themes_by_app.csv").open(encoding="utf-8-sig", newline="") as handle:
            themes = list(csv.DictReader(handle))
        grouped = {}
        for theme in themes:
            grouped.setdefault(theme["theme_label"], {})[theme["group"]] = theme
        require(len(grouped) == 11, "Expected 11 themes")
        for name, values in grouped.items():
            sc, hsbc = values["sc_mobile"], values["hsbc_hk"]
            line = next((line for line in document.splitlines() if line.startswith("| " + name + " |")), "")
            cells = [cell.strip().replace("**", "") for cell in line.strip("|").split("|")]
            expected = [name, sc["theme_mentions"], f"{int(sc['theme_mentions']) / 98 * 100:.2f}%",
                        hsbc["theme_mentions"], f"{int(hsbc['theme_mentions']) / 213 * 100:.2f}%",
                        f"{(int(sc['theme_mentions']) / 98 - int(hsbc['theme_mentions']) / 213) * 100:+.2f} pp"]
            require(cells == expected, f"Checkpoint D table mismatch: {name}")
        return {"theme_rows_checked": 11}

    check("all theme values in narrative match analysis", verify_theme_document)

    result["checks_run"] = len(result["checks"])
    result["failed"] = [item for item in result["checks"] if not item["passed"]]
    result["successful"] = not result["failed"]
    result["limits"] = ["No recrawl or live source-page validation", "No new classifier accuracy evaluation",
                        "Browser result reused by identical report hash; Edge desktop only",
                        "Relative-link checks are static, not a full folder-relocation runtime test"]
    result["delivery_file_sha256_at_review"] = {
        name: sha256(ROOT / name) for name in DOCUMENTS + [
            "report_customer_feedback_2026-10-19.html", "scripts/final_review_feedback.py",
            "data/checkpoint_D_analysis_2026-10-19/report_build_manifest.json",
            "data/checkpoint_D_analysis_2026-10-19/report_static_test_results.json",
            "data/checkpoint_D_analysis_2026-10-19/report_browser_test_results.json",
        ]
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("checkpoint", "successful", "checks_run", "failed", "report_sha256")}, indent=2))
    sys.exit(0 if result["successful"] else 1)


if __name__ == "__main__":
    main()
