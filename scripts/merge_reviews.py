r"""Merge the two final review exports, offline, without changing source values.

Uses only Python's standard library, including a small typed XLSX writer.
Run from the workspace: .\.venv\Scripts\python.exe scripts\merge_reviews.py
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
START = datetime.fromisoformat("2026-04-19T00:00:00+08:00")
END = datetime.fromisoformat("2026-10-20T00:00:00+08:00")
SOURCES = [
    ("google_play", "Google Play", "data/google_play_2026-10-19/run_03_full_history"),
    ("apple", "Apple App Store", "data/apple_2026-10-19/run_03"),
]
APPS = {
    ("google_play", "com.scb.breezebanking.hk"): ("sc_mobile", "Standard Chartered"),
    ("google_play", "hk.com.hsbc.hsbchkmobilebanking"): ("hsbc_hk", "HSBC"),
    ("apple", "445795688"): ("sc_mobile", "Standard Chartered"),
    ("apple", "1164066737"): ("hsbc_hk", "HSBC"),
}

# The insertion order is the display order in every master table.
FIELD_INFO = {
    "platform": ("string", "统一平台名：Google Play / Apple App Store；新增字段"),
    "bank": ("string", "银行：Standard Chartered / HSBC；新增字段"),
    "app": ("string", "原始应用名称"),
    "review_time_hk": ("ISO 8601 string", "香港时间 UTC+08:00；按对应 UNIX 时间从新到老排序"),
    "rating": ("integer 1–5", "来源星级，不按评论情绪调整"),
    "title": ("string / null", "Apple 原始评论标题；Google 没有标题，留空，不编造"),
    "text": ("string", "评论正文原文；不翻译、不改写、不删除换行或表情"),
    "language_status": ("string", "english / non_english / mixed / uncertain；沿用最终语言标签"),
    "within_six_month_window": ("boolean", "香港时间 [2026-04-19 00:00, 2026-10-20 00:00)"),
    "user_display_name": ("string / null", "来源公开显示名；不据此判断身份、语言或居住地"),
    "app_key": ("string", "跨平台应用组：sc_mobile / hsbc_hk；新增字段"),
    "app_id": ("string", "Google 包名或 Apple 数字应用 ID，均按文本保存"),
    "review_id": ("string", "原始评论 ID，按文本保存；不能视作跨平台用户 ID"),
    "record_key": ("string", "平台键:app_id:review_id；新增唯一键，不按相同正文跨平台去重"),
    "review_time_utc": ("ISO 8601 string", "来源评论时间换算为 UTC，可能反映编辑时间"),
    "review_timestamp_seconds": ("number", "原始 UNIX 秒数；排序依据，保留原始整数/浮点类型"),
    "source_updated_time": ("string / null", "Apple RSS 原始 updated 及其时区；Google 留空"),
    "review_app_version": ("string / null", "评论对应的应用版本"),
    "thumbs_up": ("integer / null", "仅 Google 返回的有用/点赞数量；不与 Apple 投票字段合并"),
    "vote_sum": ("integer / null", "仅 Apple 的 im:voteSum 原始字段"),
    "vote_count": ("integer / null", "仅 Apple 的 im:voteCount 原始字段"),
    "developer_reply": ("string / null", "Google 开发者回复；Apple RSS 未提供，空值不代表未回复"),
    "reply_availability": ("string / null", "Apple: not_exposed_by_public_rss；Google 无此原始字段，留空"),
    "reply_time_hk": ("ISO 8601 string / null", "仅 Google 的开发者回复时间，香港时区"),
    "reply_time_utc": ("ISO 8601 string / null", "仅 Google 的开发者回复时间，UTC"),
    "detected_language": ("string", "保留已完成的自动/人工复核语言结果，不重新检测"),
    "language_method": ("string", "最终数据集的语言识别或人工复核方法"),
    "language_probabilities": ("object", "原始自动识别概率；CSV/XLSX 中以 JSON 文本保存"),
    "on_or_before_cutoff": ("boolean", "是否早于香港时间 2026-10-20 00:00；不声称存在 10/19 评论"),
    "source": ("string", "原始来源名：Google Play / Apple App Store RSS"),
    "storefront": ("string / null", "Apple 原始 storefront=hk；Google 无该字段，留空"),
    "request_language": ("string / null", "原始数据记录的请求语言；不能视作评论语言"),
    "request_country": ("string / null", "Google 请求地区 HK；Apple 无该原始字段，留空"),
    "source_url": ("string", "原始网站核查链接；平台可能只打开应用页而非定位单条评论"),
    "feed_review_url": ("string / null", "仅 Apple RSS 返回的评论 related 链接"),
    "collected_at_utc": ("ISO 8601 string", "原始抓取时间，不是本次合并时间"),
    "source_dataset": ("string", "来源最终数据目录，相对项目根目录；新增字段"),
    "source_json_file": ("string", "来源最终 JSON 路径，相对项目根目录；新增字段"),
    "source_row_index": ("integer", "该评论在来源 JSON 数组中的零起始索引；新增字段"),
    "raw_response_file": ("string", "保留来源原值；相对 source_dataset，不是相对合并目录"),
    "raw_response_workspace_path": ("string", "无歧义的原始 HTTP 响应路径，相对项目根目录；新增字段"),
    "raw_items_file": ("string / null", "Google 原始解码 JSON 路径，相对 source_dataset"),
    "raw_items_workspace_path": ("string / null", "Google 解码 JSON 路径，相对项目根目录；新增字段"),
    "raw_item_index": ("integer / null", "Google 解码评论数组中的零起始索引"),
    "raw_entry_index": ("integer / null", "Apple feed.entry 中的零起始索引"),
}
FIELDS = list(FIELD_INFO)
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
ET.register_namespace("", NS)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_path(root, dataset, value):
    """Return an unambiguous workspace-relative path, rejecting path escapes."""
    if value is None:
        return None
    directory = (root / dataset).resolve()
    path = (directory / value).resolve()
    require(path.is_relative_to(directory), f"Evidence path escapes source dataset: {value}")
    require(path.is_file(), f"Missing evidence file: {path}")
    return path.relative_to(root.resolve()).as_posix()


def normalize(original, source_key, platform, dataset, index, root=ROOT):
    app_id = original["app_id"]
    review_id = original["review_id"]
    require(isinstance(app_id, str) and isinstance(review_id, str), "IDs must remain strings")
    require((source_key, app_id) in APPS, f"Unexpected app ID: {app_id}")
    require(set(original) <= set(FIELDS), f"Undocumented source fields: {set(original) - set(FIELDS)}")
    app_key, bank = APPS[source_key, app_id]
    row = {field: original.get(field) for field in FIELDS}
    row.update(
        platform=platform, bank=bank, app_key=app_key,
        record_key=f"{source_key}:{app_id}:{review_id}",
        source_dataset=dataset,
        source_json_file=f"{dataset}/all_languages_fetched.json",
        source_row_index=index,
        raw_response_workspace_path=evidence_path(root, dataset, original["raw_response_file"]),
        raw_items_workspace_path=evidence_path(root, dataset, original.get("raw_items_file")),
    )
    return row


def check_row(row):
    stamp = row["review_timestamp_seconds"]
    require(type(stamp) in (int, float) and math.isfinite(stamp), "Invalid timestamp")
    instant = datetime.fromtimestamp(stamp, timezone.utc)
    require(datetime.fromisoformat(row["review_time_hk"]) == instant, "HK timestamp mismatch")
    require(datetime.fromisoformat(row["review_time_hk"]).utcoffset() == START.utcoffset(), "Not HK offset")
    require(datetime.fromisoformat(row["review_time_utc"]) == instant, "UTC timestamp mismatch")
    require(type(row["within_six_month_window"]) is bool, "Window flag must be boolean")
    require(type(row["on_or_before_cutoff"]) is bool, "Cutoff flag must be boolean")
    require(row["within_six_month_window"] == (START <= instant < END), "Window flag mismatch")
    require(row["on_or_before_cutoff"] == (instant < END), "Cutoff flag mismatch")
    require(type(row["rating"]) is int and 1 <= row["rating"] <= 5, "Invalid star rating")
    require(isinstance(row["text"], str), "Missing review body")
    require(row["language_status"] in {"english", "non_english", "mixed", "uncertain"}, "Invalid language label")


def sort_rows(rows):
    return sorted(rows, key=lambda row: (-row["review_timestamp_seconds"], row["record_key"]))


def make_subsets(rows):
    return {
        "master_all_reviews": rows,
        "master_english_all": [r for r in rows if r["language_status"] == "english" and r["on_or_before_cutoff"]],
        "master_six_months_all": [r for r in rows if r["within_six_month_window"]],
        "master_english_six_months": [r for r in rows if r["language_status"] == "english" and r["within_six_month_window"]],
    }


def scalar(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list, bool)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({key: scalar(row[key]) for key in FIELDS} for row in rows)


def column_name(number):
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def tag(name):
    return f"{{{NS}}}{name}"


def worksheet(headers, rows, data_sheet=False):
    """Explicit string cells preserve IDs and prevent formula execution."""
    sheet = ET.Element(tag("worksheet"))
    ET.SubElement(sheet, tag("dimension"), ref=f"A1:{column_name(len(headers))}{len(rows) + 1}")
    views = ET.SubElement(sheet, tag("sheetViews"))
    view = ET.SubElement(views, tag("sheetView"), workbookViewId="0")
    ET.SubElement(view, tag("pane"), ySplit="1", topLeftCell="A2", activePane="bottomLeft", state="frozen")
    widths = ET.SubElement(sheet, tag("cols"))
    for index, name in enumerate(headers, 1):
        width = 76 if name in {"text", "说明"} else 40 if name in {"title", "developer_reply"} else 27
        ET.SubElement(widths, tag("col"), min=str(index), max=str(index), width=str(width), customWidth="1")
    sheet_data = ET.SubElement(sheet, tag("sheetData"))
    for number, values in enumerate([headers, *rows], 1):
        row = ET.SubElement(sheet_data, tag("row"), r=str(number))
        for index, value in enumerate(values, 1):
            if value is None:
                continue
            cell = ET.SubElement(row, tag("c"), r=f"{column_name(index)}{number}", s="1" if number == 1 else "0")
            if isinstance(value, bool):
                cell.set("t", "b")
                ET.SubElement(cell, tag("v")).text = "1" if value else "0"
            elif isinstance(value, (int, float)):
                cell.set("t", "n")
                ET.SubElement(cell, tag("v")).text = str(value)
            else:
                cell.set("t", "inlineStr")
                text = scalar(value)
                require(len(text) <= 32767, "Text exceeds XLSX cell limit; no truncation permitted")
                require(all(ord(c) >= 32 or c in "\t\n\r" for c in text), "Invalid XML control character")
                inline = ET.SubElement(cell, tag("is"))
                ET.SubElement(inline, tag("t"), {"{http://www.w3.org/XML/1998/namespace}space": "preserve"}).text = text
    if data_sheet:
        ET.SubElement(sheet, tag("autoFilter"), ref=f"A1:{column_name(len(headers))}{len(rows) + 1}")
    # XML parsers normalize literal CR to LF; a character reference preserves CR.
    return ET.tostring(sheet, encoding="utf-8", xml_declaration=True).replace(b"\r", b"&#13;")


def write_xlsx(path, subsets, stats):
    summary_headers = ["平台", "应用", "全部已抓取", "英文全部", "近六月全部", "近六月英文"]
    summary_rows = [[r[k] for k in ["platform", "app", "all_fetched", "english_all", "six_months_all", "english_six_months"]] for r in stats]
    summary_rows += [
        ["合计", "两个应用 / 两个平台", *[len(subsets[k]) for k in subsets]],
        [],
        ["时间窗口", "2026-04-19 00:00 至 2026-10-20 00:00（后者不含），香港 UTC+08"],
        ["建议分析表", "近六月英文；英文全部含更早记录，全部评论含非英文"],
        ["排序", "所有评论表按 review_timestamp_seconds 从新到老"],
        ["Apple 范围", "香港公开 RSS，每应用 500 条，不是完整历史；缺少开发者回复"],
        ["Google 范围", "本次香港区、英文请求参数下接口返回的记录，不保证覆盖所有商店展示"],
        ["记录含义", "评论条数，不是独立客户人数；日期可能反映编辑时间"],
        ["原文与安全", "XLSX 文本单元格不执行公式；CSV 保留原值，请按文本导入用户内容列"],
        ["原始证据", "raw_response_workspace_path 相对 D:/7-Short project 项目根目录"],
        ["语言标签", "继承最终数据标签及人工修正；历史自动分类仍可能有误"],
    ]
    sheets = [("汇总说明", summary_headers, summary_rows, False)]
    for name, key in [("全部评论", "master_all_reviews"), ("英文全部", "master_english_all"),
                      ("近六月全部", "master_six_months_all"), ("近六月英文", "master_english_six_months")]:
        sheets.append((name, FIELDS, [[r[k] for k in FIELDS] for r in subsets[key]], True))
    sheets.append(("字段说明", ["字段", "数据类型", "说明"], [[k, *v] for k, v in FIELD_INFO.items()], True))
    types_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
    relationships_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    content_types = ET.Element("Types", xmlns=types_ns)
    for extension, kind in [("rels", "application/vnd.openxmlformats-package.relationships+xml"), ("xml", "application/xml")]:
        ET.SubElement(content_types, "Default", Extension=extension, ContentType=kind)
    parts = [("/xl/workbook.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"),
             ("/xl/styles.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml")]
    parts += [(f"/xl/worksheets/sheet{i}.xml", "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml") for i in range(1, len(sheets) + 1)]
    for part, kind in parts:
        ET.SubElement(content_types, "Override", PartName=part, ContentType=kind)
    root_rels = ET.Element("Relationships", xmlns=relationships_ns)
    ET.SubElement(root_rels, "Relationship", Id="rId1", Type=f"{REL}/officeDocument", Target="xl/workbook.xml")
    workbook = ET.Element(tag("workbook"))
    book_sheets = ET.SubElement(workbook, tag("sheets"))
    book_rels = ET.Element("Relationships", xmlns=relationships_ns)
    for i, (name, _, _, _) in enumerate(sheets, 1):
        ET.SubElement(book_sheets, tag("sheet"), name=name, sheetId=str(i), attrib={f"{{{REL}}}id": f"rId{i}"})
        ET.SubElement(book_rels, "Relationship", Id=f"rId{i}", Type=f"{REL}/worksheet", Target=f"worksheets/sheet{i}.xml")
    ET.SubElement(book_rels, "Relationship", Id="styles", Type=f"{REL}/styles", Target="styles.xml")
    styles = f'''<styleSheet xmlns="{NS}"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'''
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        for name, element in [("[Content_Types].xml", content_types), ("_rels/.rels", root_rels),
                              ("xl/workbook.xml", workbook), ("xl/_rels/workbook.xml.rels", book_rels)]:
            archive.writestr(name, ET.tostring(element, encoding="utf-8", xml_declaration=True))
        archive.writestr("xl/styles.xml", styles)
        for i, (_, headers, rows, filtered) in enumerate(sheets, 1):
            archive.writestr(f"xl/worksheets/sheet{i}.xml", worksheet(headers, rows, filtered))


def verify_outputs(output, subsets):
    result = {}
    for name, rows in subsets.items():
        require(load_json(output / f"{name}.json") == rows, f"JSON round-trip failed: {name}")
        with (output / f"{name}.csv").open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            require(reader.fieldnames == FIELDS, f"CSV schema mismatch: {name}")
            csv_rows = list(reader)
        require(csv_rows == [{k: scalar(r[k]) for k in FIELDS} for r in rows], f"CSV value mismatch: {name}")
        result[name] = {"rows": len(rows), "sorted_newest_first": rows == sort_rows(rows), "csv_json_round_trip": True}
        require(result[name]["sorted_newest_first"], f"Unsorted output: {name}")
    with ZipFile(output / "reviews_master.xlsx") as archive:
        require(archive.testzip() is None, "XLSX ZIP integrity failure")
        for name in archive.namelist():
            if name.endswith((".xml", ".rels")):
                require(not list(ET.fromstring(archive.read(name)).iter(tag("f"))), "Formula found in XLSX")
        for i, (name, rows) in enumerate(subsets.items(), 2):
            sheet = ET.fromstring(archive.read(f"xl/worksheets/sheet{i}.xml"))
            sheet_rows = sheet.find(tag("sheetData")).findall(tag("row"))
            require(len(sheet_rows) == len(rows) + 1, f"XLSX row count mismatch: {name}")
            for xml_row, original in zip(sheet_rows[1:], rows):
                values = {cell.attrib["r"]: cell for cell in xml_row}
                for index, field in enumerate(FIELDS, 1):
                    expected = original[field]
                    cell = values.get(f"{column_name(index)}{xml_row.attrib['r']}")
                    if expected is None:
                        require(cell is None, f"XLSX null mismatch: {field}")
                        continue
                    require(cell is not None, f"Missing XLSX cell: {field}")
                    kind = cell.attrib["t"]
                    if isinstance(expected, bool):
                        require(kind == "b" and cell.findtext(tag("v")) == ("1" if expected else "0"), f"XLSX bool mismatch: {field}")
                    elif isinstance(expected, (int, float)):
                        require(kind == "n" and float(cell.findtext(tag("v"))) == expected, f"XLSX number mismatch: {field}")
                    else:
                        actual = cell.find(f"{tag('is')}/{tag('t')}").text or ""
                        require(kind == "inlineStr" and actual == scalar(expected), f"XLSX text mismatch: {field}")
            result[name]["xlsx_typed_cell_round_trip"] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "data/merged_2026-10-19")
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT) and output != ROOT, "Output must be a subdirectory of the project")
    require(not output.exists() or not any(output.iterdir()), "Output directory is nonempty; choose a new --output directory")
    rows, originals, inputs, statistics = [], {}, [], []
    for source_key, platform, dataset in SOURCES:
        path = ROOT / dataset / "all_languages_fetched.json"
        source_rows = load_json(path)
        require(isinstance(source_rows, list), "Input must be a JSON array")
        inputs.append({"platform": platform, "file": path.relative_to(ROOT).as_posix(), "sha256": sha256(path), "rows": len(source_rows)})
        current = [normalize(r, source_key, platform, dataset, i) for i, r in enumerate(source_rows)]
        for row, original in zip(current, source_rows):
            check_row(row)
            key = row["record_key"]
            require(key not in originals, f"Duplicate platform/app/review key: {key}; not silently dropped")
            require(all(row[k] == v and type(row[k]) is type(v) for k, v in original.items()), f"Source field changed: {key}")
            originals[key] = original
        for subset_file, subset_name in [("english_as_of_2026-10-19.json", "master_english_all"), ("english_six_months.json", "master_english_six_months")]:
            expected = {f"{source_key}:{r['app_id']}:{r['review_id']}": r for r in load_json(ROOT / dataset / subset_file)}
            actual = {r["record_key"]: originals[r["record_key"]] for r in make_subsets(current)[subset_name]}
            require(actual == expected, f"Final source English export mismatch: {dataset}/{subset_file}")
        for app_key in ("sc_mobile", "hsbc_hk"):
            app_rows = [r for r in current if r["app_key"] == app_key]
            parts = make_subsets(sort_rows(app_rows))
            statistics.append({"platform": platform, "app": app_rows[0]["app"], "app_key": app_key,
                               **{key: len(parts[name]) for key, name in zip(["all_fetched", "english_all", "six_months_all", "english_six_months"], parts)}})
        rows.extend(current)
    rows = sort_rows(rows)
    subsets = make_subsets(rows)
    output.mkdir(parents=True, exist_ok=True)
    for name, items in subsets.items():
        dump_json(output / f"{name}.json", items)
        write_csv(output / f"{name}.csv", items)
    write_xlsx(output / "reviews_master.xlsx", subsets, statistics)
    verification = verify_outputs(output, subsets)
    for source in inputs:
        require(sha256(ROOT / source["file"]) == source["sha256"], "Source changed during merge")
    report = {
        "merged_at_utc": datetime.now(timezone.utc).isoformat(),
        "window_start_inclusive_hk": START.isoformat(), "window_end_exclusive_hk": END.isoformat(),
        "sort": "review_timestamp_seconds descending; record_key ascending for ties",
        "unique_key": "platform key + app_id + review_id", "field_count": len(FIELDS),
        "input_files": inputs, "statistics": statistics, "exports": verification,
        "language_status_all": dict(Counter(r["language_status"] for r in rows)),
        "latest_review_hk": rows[0]["review_time_hk"], "earliest_review_hk": rows[-1]["review_time_hk"],
        "duplicate_keys": 0, "dropped_rows": 0, "source_fields_preserved": True,
        "source_language_labels_and_manual_corrections_preserved": True,
        "english_subsets_match_both_final_source_exports": True,
        "all_evidence_paths_exist": True, "input_hashes_unchanged_after_merge": True,
        "xlsx_no_formulas": True,
        "coverage_caveats": ["Apple 香港公开 RSS 每应用 500 条，不是完整历史", "Google 是本次地区/语言/排序接口返回范围，不保证全部商店展示", "评论日期可能反映编辑时间；评论数不是客户数", "英文标签沿用最终结果，历史自动识别可能有误", "CSV 原样保存用户文本；在电子表格中应按文本导入，推荐直接使用已设文本类型的 XLSX"],
    }
    report["artifact_hashes_sha256"] = {p.name: sha256(p) for p in sorted(output.iterdir()) if p.suffix in {".csv", ".json", ".xlsx"}}
    dump_json(output / "merge_report.json", report)
    dictionary = "# 合并评论总表字段说明\n\n所有 45 列均在 Excel、CSV 和 JSON 中一致排列。原始字段逐值、逐类型保留在 JSON 中；来源没有的字段补 null。CSV 使用 UTF-8 BOM，空值为留空，对象和布尔值以 JSON 文本保存。XLSX 明确保存文本、数值和布尔类型，ID 是文本。\n\n| 字段 | JSON 类型 | 说明 |\n|---|---|---|\n"
    dictionary = dictionary.replace("45 列", f"{len(FIELDS)} 列")
    dictionary += "".join(f"| {key} | {kind} | {description} |\n" for key, (kind, description) in FIELD_INFO.items())
    (output / "data_dictionary.md").write_text(dictionary, encoding="utf-8")
    readme = """# Google Play + Apple 合并评论总表

首选打开 `reviews_master.xlsx`：含汇总说明、全部评论、英文全部、近六月全部、近六月英文、字段说明六个工作表。所有评论表均有标题筛选、首行冻结和正文自动换行。每行是一条评论，不是一个独立用户。

| 文件（均有 CSV 和 JSON） | 范围 | 条数 |
|---|---|---:|
"""
    for name, description in [("master_all_reviews", "全部已抓取记录，含所有语言及更早记录"), ("master_english_all", "英文、截至 2026/10/19，含更早记录"), ("master_six_months_all", "近六个月，所有语言"), ("master_english_six_months", "近六个月英文，建议用于当前项目分析")]:
        readme += f"| `{name}` | {description} | {len(subsets[name]):,} |\n"
    readme += "\n## 应用和平台计数\n\n| 平台 | 应用 | 全部 | 英文全部 | 近六月全部 | 近六月英文 |\n|---|---|---:|---:|---:|---:|\n"
    for r in statistics:
        readme += f"| {r['platform']} | {r['app']} | {r['all_fetched']} | {r['english_all']} | {r['six_months_all']} | {r['english_six_months']} |\n"
    readme += r"""
## 口径与核查

- 时间窗：香港时间 **2026/04/19 00:00（含）至 2026/10/20 00:00（不含）**。按数值时间戳倒序；同秒按唯一键升序。不代表最新一条恰好发布于 10/19。
- 仅使用 Google `run_03_full_history` 和 Apple `run_03` 两份最终数据，不混入试抓、中间版本或其他地区。原始采集文件未修改，也没有重新抓取或重新做语言识别。
- 按 `record_key = 平台键:app_id:review_id` 检查唯一性，不按相同正文跨平台合并，不做跨平台用户身份推断。Apple 标题与正文分开；来源星级、换行、拼写、表情及已人工修正的语言标签均保留。
- `source_json_file` + `source_row_index` 定位原始导出记录；`raw_response_workspace_path` 从项目根目录定位 HTTP 原始响应。`raw_response_file` 原值仍相对 `source_dataset`。不要将其误作相对本合并目录。
- `source_url` 可用于网站核查；`raw_item_index` / `raw_entry_index` 用于原始响应内核查。网站展示可能更新、排序不同或无法直接定位单条。
- Apple 香港 RSS 每应用仅取得 10 页、共 500 条；并非完整历史。Google 也只代表本次请求参数下返回的公开记录。不能据此把没抓到的时间段解释为没有评论。
- Apple RSS 不暴露开发者回复，空值不代表银行从未回复。Google 点赞与 Apple 投票分别保存，不直接视作相同指标。
- 英文子集严格匹配此前两个平台的最终英文导出；历史语言分类主要自动完成，仍有误判可能。评论日期可能是编辑时间。
- 推荐直接使用 XLSX：所有用户文本均为文本单元格，不执行公式。CSV 为保留原文没有加防公式前缀；若用 Excel 导入 CSV，请将评论、标题、显示名等用户内容列设为文本。JSON 保留完整类型和 null/空字符串区别，适合后续分析程序。
- `merge_report.json` 记录输入/输出 SHA-256、计数和检查结果。导出后逐值验证全部 JSON/CSV、XLSX 每个数据单元格、日期窗口、排序、唯一键、证据文件存在性及原始字段未改动。

重新生成到新目录（仅标准库，无需联网或安装）：

```powershell
.\.venv\Scripts\python.exe scripts\merge_reviews.py --output data\merged_2026-10-19_rerun
```

脚本拒绝覆盖非空输出目录。
"""
    (output / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps({"output": str(output), "rows": {k: len(v) for k, v in subsets.items()}, "fields": len(FIELDS), "verification": "passed"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
