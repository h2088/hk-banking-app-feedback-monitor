"""Common storage/configuration and typed exports for independent review batches."""
from __future__ import annotations

import calendar
import csv
import hashlib
import json
import math
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED

from xlsx_core import NS, worksheet

HK = timezone(timedelta(hours=8))
SKILL = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def dump(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_path(root, value):
    require(isinstance(value, str) and value, "Empty evidence path")
    require(not Path(value).is_absolute() and not re.match(r"^[A-Za-z]:", value), "Relative path required")
    path = (root / value).resolve()
    require(path.is_relative_to(root.resolve()), f"Path leaves batch: {value}")
    return path


def now():
    return datetime.now(timezone.utc).isoformat()


def bounds(config):
    start = datetime.combine(date.fromisoformat(config["since"]), time.min, HK)
    end = datetime.combine(date.fromisoformat(config["as_of"]) + timedelta(days=1), time.min, HK)
    require(start < end, "since must not follow as_of")
    return start, end


def six_months_before(day):
    month = day.year * 12 + day.month - 1 - 6
    year, index = divmod(month, 12)
    return date(year, index + 1, min(day.day, calendar.monthrange(year, index + 1)[1]))


def config_for(root):
    config = load(root / "config.json")
    require(config.get("schema_version") == 1, "Unsupported config version")
    require(config.get("country") == "HK" and config.get("timezone") == "Asia/Hong_Kong", "Collector supports HK only")
    require(config.get("language") == "english" and config.get("platform_split") is False, "This engine implements English, overall reporting")
    apps = config["apps"]
    require(len(apps) == 2 and {a["role"] for a in apps} == {"primary", "benchmark"}, "Exactly one primary and one benchmark required")
    require(len({a["key"] for a in apps}) == 2, "Duplicate app keys")
    for app in apps:
        require(re.fullmatch(r"[a-z][a-z0-9_]*", app["key"]), "Invalid app key")
        require(re.fullmatch(r"[a-zA-Z0-9_.]+", app["google_id"]), "Invalid Google package")
        require(re.fullmatch(r"[0-9]+", app["apple_id"]), "Apple ID must be a numeric string")
        require(re.fullmatch(r"[a-z0-9-]+", app["apple_slug"]), "Invalid Apple slug")
        require(bool(app["name"]) and bool(app["bank"]), "App name and bank required")
    require(len({a["google_id"] for a in apps}) == 2 and len({a["apple_id"] for a in apps}) == 2, "Distinct app IDs required")
    require(1 <= config["google_max_pages"] <= 500 and 1 <= config["apple_max_pages"] <= 10, "Invalid page safety limit")
    require(0.5 <= config["pause_seconds"] <= 30, "Pause must be 0.5–30 seconds")
    bounds(config)
    return config


def csv_write(path, rows, fields=None):
    if fields is None:
        fields = list(dict.fromkeys(key for row in rows for key in row))
    def scalar(value):
        if value is None:
            return ""
        if isinstance(value, (dict, list, bool)):
            return json.dumps(value, ensure_ascii=False)
        return value
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: scalar(row.get(key)) for key in fields} for row in rows)


def xlsx_write(path, sheets):
    """Small standard-library workbook with typed cells and formula-safe strings."""
    relations = "http://schemas.openxmlformats.org/package/2006/relationships"
    office_rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    workbook = ET.Element(f"{{{NS}}}workbook")
    sheet_list = ET.SubElement(workbook, f"{{{NS}}}sheets")
    rels = ET.Element("Relationships", xmlns=relations)
    types = ET.Element("Types", xmlns="http://schemas.openxmlformats.org/package/2006/content-types")
    ET.SubElement(types, "Default", Extension="rels", ContentType="application/vnd.openxmlformats-package.relationships+xml")
    ET.SubElement(types, "Default", Extension="xml", ContentType="application/xml")
    ET.SubElement(types, "Override", PartName="/xl/workbook.xml", ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml")
    root_rels = ET.Element("Relationships", xmlns=relations)
    ET.SubElement(root_rels, "Relationship", Id="rId1", Type=office_rel + "/officeDocument", Target="xl/workbook.xml")
    ET.SubElement(rels, "Relationship", Id="styles", Type=office_rel + "/styles", Target="styles.xml")
    ET.SubElement(types, "Override", PartName="/xl/styles.xml", ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml")
    with ZipFile(path, "x", ZIP_DEFLATED) as archive:
        styles = ('<?xml version="1.0" encoding="utf-8"?><styleSheet xmlns="' + NS + '">'
            '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs>'
            '<cellXfs count="2"><xf fontId="0" fillId="0" borderId="0" xfId="0"/><xf fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')
        archive.writestr("xl/styles.xml", styles)
        for i, (name, rows) in enumerate(sheets.items(), 1):
            fields = list(dict.fromkeys(key for row in rows for key in row)) or ["no_records"]
            ET.SubElement(sheet_list, f"{{{NS}}}sheet", name=name[:31], sheetId=str(i), attrib={f"{{{office_rel}}}id": f"rId{i}"})
            ET.SubElement(rels, "Relationship", Id=f"rId{i}", Type=office_rel + "/worksheet", Target=f"worksheets/sheet{i}.xml")
            ET.SubElement(types, "Override", PartName=f"/xl/worksheets/sheet{i}.xml", ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml")
            archive.writestr(f"xl/worksheets/sheet{i}.xml", worksheet(fields, [[r.get(key) for key in fields] for r in rows], data_sheet=True))
        for name, node in {"[Content_Types].xml": types, "_rels/.rels": root_rels,
                           "xl/workbook.xml": workbook, "xl/_rels/workbook.xml.rels": rels}.items():
            archive.writestr(name, ET.tostring(node, encoding="utf-8", xml_declaration=True))


def app_for(config, app_key):
    return next(app for app in config["apps"] if app["key"] == app_key)


def validate_row(row, config, root, require_english=False):
    fields = ["app", "app_key", "app_id", "review_id", "record_key", "text", "review_time_hk", "review_time_utc",
              "source_url", "language_status", "collected_at_utc", "raw_response_workspace_path"]
    require(all(row.get(k) not in (None, "") for k in fields), f"Missing required field in {row.get('record_key')}")
    app = app_for(config, row["app_key"])
    platform = row["platform"]
    require(platform in {"Google Play", "Apple App Store"}, "Unknown platform")
    source = "google_play" if platform == "Google Play" else "apple"
    require(isinstance(row["review_id"], str) and isinstance(row["app_id"], str), "IDs must be strings")
    require(row["app_id"] == app["google_id" if source == "google_play" else "apple_id"], "App ID mismatch")
    require(row["record_key"] == f"{source}:{row['app_id']}:{row['review_id']}", "Record key mismatch")
    require(type(row["rating"]) is int and 1 <= row["rating"] <= 5, "Rating must be integer 1–5")
    require(isinstance(row["text"], str), "Body must be source text")
    seconds = row["review_timestamp_seconds"]
    require(type(seconds) in (float, int) and math.isfinite(seconds), "Invalid Unix timestamp")
    instant = datetime.fromtimestamp(seconds, timezone.utc)
    require(datetime.fromisoformat(row["review_time_hk"]) == instant and datetime.fromisoformat(row["review_time_hk"]).utcoffset() == timedelta(hours=8), "HK time mismatch")
    require(datetime.fromisoformat(row["review_time_utc"]) == instant, "UTC time mismatch")
    require(row["language_status"] in {"english", "non_english", "mixed", "uncertain"}, "Invalid language label")
    from urllib.parse import parse_qs, urlsplit
    url = urlsplit(row["source_url"])
    require(url.scheme == "https", "Source must be HTTPS")
    if source == "google_play":
        require(url.hostname == "play.google.com" and parse_qs(url.query).get("id") == [app["google_id"]], "Google source ID mismatch")
    else:
        require(url.hostname == "apps.apple.com" and re.search(r"/id" + re.escape(app["apple_id"]) + r"(?:/|$)", url.path), "Apple source ID mismatch")
    require(safe_path(root, row["raw_response_workspace_path"]).is_file(), "Raw response missing")
    if require_english:
        start, end = bounds(config)
        require(start <= instant < end and row["language_status"] == "english", "Wrong English/window subset")
    return source


def sorted_rows(rows):
    return sorted(rows, key=lambda row: (-row["review_timestamp_seconds"], row["record_key"]))


def fingerprints(row):
    return hashlib.sha256(json.dumps({k: row.get(k) for k in ("record_key", "title", "text", "rating", "review_time_hk")},
        ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
