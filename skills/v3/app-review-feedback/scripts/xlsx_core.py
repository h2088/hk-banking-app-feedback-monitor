"""Typed XLSX worksheet primitives; inline strings do not execute formulas."""
import json
import math
from xml.etree import ElementTree as ET
NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
ET.register_namespace("", NS)

def require(condition, message):
    if not condition:
        raise ValueError(message)


def scalar(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list, bool)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


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
