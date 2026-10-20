"""Produce the reproducible Checkpoint C QA package for the current English sample.

This is a derived QA export. It never edits the immutable source captures or the
master merge outputs. Run from the workspace:
  .\\.venv\\Scripts\\python.exe scripts\\checkpoint_C_qa.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MERGED = ROOT / "data/merged_2026-10-19"
OUTPUT = ROOT / "data/checkpoint_C_qa_2026-10-19"
START = datetime.fromisoformat("2026-04-19T00:00:00+08:00")
END = datetime.fromisoformat("2026-10-20T00:00:00+08:00")
BASE_FIELDS = None
QA_FIELDS = [
    "is_duplicate",
    "normalized_text_sha256",
    "normalized_text_duplicate_count",
    "is_normalized_text_duplicate",
    "word_count",
    "is_short_text_for_theme_review",
    "analysis_eligible",
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_rows(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_text(text):
    # Used only as a duplicate key: preserve original text in every export.
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).casefold()).strip()


def words(text):
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)


def values_as_csv(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list, bool)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def csv_write(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: values_as_csv(row.get(field)) for field in fields})


def audit_rows(rows):
    require(rows, "No rows supplied")
    fields = list(rows[0])
    require(all(list(row) == fields for row in rows), "Input rows do not have a stable schema")
    require({"platform", "app", "app_key", "app_id", "review_id", "record_key", "review_time_hk", "review_time_utc", "review_timestamp_seconds", "rating", "text", "language_status", "within_six_month_window", "on_or_before_cutoff", "source_url", "collected_at_utc", "raw_response_workspace_path"} <= set(fields), "Missing normalized fields")
    key_counts = Counter(row["record_key"] for row in rows)
    text_keys = Counter(hashlib.sha256(normalized_text(row["text"]).encode("utf-8")).hexdigest() for row in rows)
    result = []
    for row in rows:
        instant_hk = datetime.fromisoformat(row["review_time_hk"])
        instant_utc = datetime.fromisoformat(row["review_time_utc"])
        text_key = hashlib.sha256(normalized_text(row["text"]).encode("utf-8")).hexdigest()
        word_count = len(words(row["text"]))
        required_ok = all(row.get(field) not in (None, "") for field in ["platform", "app", "app_key", "app_id", "review_id", "record_key", "review_time_hk", "review_time_utc", "rating", "text", "language_status", "source_url", "collected_at_utc", "raw_response_workspace_path"])
        valid_date = START <= instant_hk < END and instant_hk.astimezone(instant_utc.tzinfo) == instant_utc and row["within_six_month_window"] is True and row["on_or_before_cutoff"] is True
        valid_rating = isinstance(row["rating"], int) and 1 <= row["rating"] <= 5
        app_ok = (row["app_key"], row["platform"], row["app_id"]) in {
            ("sc_mobile", "Google Play", "com.scb.breezebanking.hk"),
            ("hsbc_hk", "Google Play", "hk.com.hsbc.hsbchkmobilebanking"),
            ("sc_mobile", "Apple App Store", "445795688"),
            ("hsbc_hk", "Apple App Store", "1164066737"),
        }
        language_ok = row["language_status"] == "english"
        evidence_ok = (ROOT / row["raw_response_workspace_path"]).is_file()
        qa = dict(row)
        qa.update(
            is_duplicate=key_counts[row["record_key"]] > 1,
            normalized_text_sha256=text_key,
            normalized_text_duplicate_count=text_keys[text_key],
            is_normalized_text_duplicate=text_keys[text_key] > 1,
            word_count=word_count,
            is_short_text_for_theme_review=word_count <= 4,
            analysis_eligible=bool(required_ok and valid_date and valid_rating and app_ok and language_ok and evidence_ok and not key_counts[row["record_key"]] > 1),
        )
        qa["_checks"] = {
            "required_fields_present": required_ok, "date_window_and_timestamps_valid": valid_date,
            "rating_valid": valid_rating, "app_identity_valid": app_ok, "english_label_valid": language_ok,
            "raw_evidence_exists": evidence_ok, "duplicate_record_key": key_counts[row["record_key"]] > 1,
        }
        result.append(qa)
    return fields, result


def coverage_rows(rows):
    dimensions = Counter((r["platform"], r["app_key"], r["app"], r["review_time_hk"][:7], r["language_status"], r["rating"]) for r in rows)
    return [
        {"platform": platform, "app_key": app_key, "app": app, "month_hk": month, "language_status": language, "rating": rating, "review_count": count}
        for (platform, app_key, app, month, language, rating), count in sorted(dimensions.items())
    ]


def grouped_rows(rows, keys):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    result = []
    for group, members in sorted(groups.items()):
        item = dict(zip(keys, group))
        item.update({
            "review_count": len(members),
            "rating_mean": round(sum(r["rating"] for r in members) / len(members), 4),
            "date_min_hk": min(r["review_time_hk"] for r in members),
            "date_max_hk": max(r["review_time_hk"] for r in members),
            "short_text_count": sum(r["is_short_text_for_theme_review"] for r in members),
        })
        result.append(item)
    return result


def write_text_table(path, rows):
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    csv_write(path, rows, list(rows[0]))


def main():
    global BASE_FIELDS
    source_path = MERGED / "master_english_six_months.json"
    all_path = MERGED / "master_all_reviews.json"
    rows = read_rows(source_path)
    all_rows = read_rows(all_path)
    BASE_FIELDS, qa_rows = audit_rows(rows)
    for qa in qa_rows:
        qa.pop("_checks", None)
    require(len(rows) == 311, f"Expected 311 English six-month rows, got {len(rows)}")
    require(all(row["analysis_eligible"] for row in qa_rows), "A row failed analysis eligibility")
    require(all(row["language_status"] == "english" for row in qa_rows), "Non-English row in English sample")
    require(all(row["within_six_month_window"] is True for row in qa_rows), "Out-of-window row")
    require(qa_rows == sorted(qa_rows, key=lambda r: (-r["review_timestamp_seconds"], r["record_key"])), "Input is not sorted newest first")
    require(len({row["record_key"] for row in qa_rows}) == len(qa_rows), "Duplicate record keys")

    # Full merged dataset duplicate context, while the analysis QA remains 311 rows.
    all_key_duplicates = len(all_rows) - len({r["record_key"] for r in all_rows})
    all_text_groups = Counter(hashlib.sha256(normalized_text(r["text"]).encode("utf-8")).hexdigest() for r in all_rows)
    analysis_text_groups = Counter(row["normalized_text_sha256"] for row in qa_rows)
    missing = {field: sum(row.get(field) in (None, "") for row in rows) for field in ["platform", "app", "app_key", "app_id", "review_id", "review_time_hk", "rating", "text", "language_status", "source_url", "collected_at_utc", "raw_response_workspace_path"]}

    OUTPUT.mkdir(parents=True, exist_ok=True)
    out_fields = BASE_FIELDS + QA_FIELDS
    write_json(OUTPUT / "english_six_months_qa.json", qa_rows)
    csv_write(OUTPUT / "english_six_months_qa.csv", qa_rows, out_fields)
    write_text_table(OUTPUT / "coverage_by_app_platform.csv", grouped_rows(qa_rows, ["platform", "app_key", "app"]))
    # Group by calendar month in Hong Kong time, not by individual timestamp.
    month_rows = [{**r, "month_hk": r["review_time_hk"][:7]} for r in qa_rows]
    write_text_table(OUTPUT / "coverage_by_month.csv", grouped_rows(month_rows, ["month_hk"]))
    write_text_table(OUTPUT / "coverage_by_rating.csv", grouped_rows(qa_rows, ["rating"]))
    write_text_table(OUTPUT / "coverage_long_platform_month_language_rating.csv", coverage_rows(qa_rows))

    summary = {
        "checkpoint": "C",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_input": source_path.relative_to(ROOT).as_posix(),
        "analysis_input_sha256": sha256(source_path),
        "all_merged_input": all_path.relative_to(ROOT).as_posix(),
        "all_merged_input_sha256": sha256(all_path),
        "rows_checked": len(rows),
        "rows_analysis_eligible": sum(row["analysis_eligible"] for row in qa_rows),
        "rows_not_analysis_eligible": sum(not row["analysis_eligible"] for row in qa_rows),
        "date_window": {"start_inclusive_hk": START.isoformat(), "end_exclusive_hk": END.isoformat(), "outside_window": sum(not START <= datetime.fromisoformat(r["review_time_hk"]) < END for r in rows)},
        "missing_required_fields": missing,
        "invalid_ratings": sum(not isinstance(r["rating"], int) or not 1 <= r["rating"] <= 5 for r in rows),
        "non_english_rows": sum(r["language_status"] != "english" for r in rows),
        "invalid_app_identity": sum(not ((r["app_key"], r["platform"], r["app_id"]) in {("sc_mobile", "Google Play", "com.scb.breezebanking.hk"), ("hsbc_hk", "Google Play", "hk.com.hsbc.hsbchkmobilebanking"), ("sc_mobile", "Apple App Store", "445795688"), ("hsbc_hk", "Apple App Store", "1164066737")}) for r in rows),
        "duplicate_record_keys_analysis_sample": sum(row["is_duplicate"] for row in qa_rows),
        "duplicate_record_keys_all_merged": all_key_duplicates,
        "normalized_text_duplicate_groups_analysis_sample": sum(count > 1 for count in analysis_text_groups.values()),
        "normalized_text_duplicate_rows_analysis_sample": sum(count for count in analysis_text_groups.values() if count > 1),
        "normalized_text_duplicate_groups_all_merged": sum(count > 1 for count in all_text_groups.values()),
        "normalized_text_duplicate_rows_all_merged": sum(count for count in all_text_groups.values() if count > 1),
        "short_text_for_theme_review_rows": sum(row["is_short_text_for_theme_review"] for row in qa_rows),
        "short_text_rule": "English word count <= 4; retained for volume/rating analysis, flagged for cautious theme interpretation",
        "evidence_files_missing": sum(not (ROOT / r["raw_response_workspace_path"]).is_file() for r in rows),
        "sorted_newest_first": qa_rows == sorted(qa_rows, key=lambda r: (-r["review_timestamp_seconds"], r["record_key"])),
        "coverage": {
            "by_platform_app": grouped_rows(qa_rows, ["platform", "app_key", "app"]),
            "by_month": grouped_rows(month_rows, ["month_hk"]),
            "by_rating": grouped_rows(qa_rows, ["rating"]),
            "by_platform_app_month_language_rating": coverage_rows(qa_rows),
        },
        "interpretation": [
            "No record-key duplicates were found; no rows were dropped.",
            "Identical normalized text is a QA flag, not a deletion rule. The current English sample has 5 groups / 20 rows, mostly generic short reviews; different source IDs are retained.",
            "All 311 rows pass data-quality eligibility. This does not mean every row contains enough information for a specific theme; short texts are flagged separately.",
            "The 311 rows are suitable for descriptive counts, ratings, and source/app comparison. Sentiment/theme labels still require Checkpoint D methods and manual validation.",
        ],
        "next_checkpoint": "D — analysis: descriptive trends, documented sentiment/theme method, manually checked validation sample, and competitor comparison.",
    }
    summary["artifact_sha256"] = {}
    for path in sorted(OUTPUT.iterdir()):
        if path.is_file() and path.name != "qa_summary.json":
            summary["artifact_sha256"][path.name] = sha256(path)
    write_json(OUTPUT / "qa_summary.json", summary)
    print(json.dumps({"output": str(OUTPUT), "rows": len(qa_rows), "analysis_eligible": summary["rows_analysis_eligible"], "verification": "passed"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
