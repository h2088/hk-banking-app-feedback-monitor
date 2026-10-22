"""Maintainer helper: extract unchanged, reusable code from the originating project.

Only the named pure rules, parsers, language helper, and XLSX primitives are
extracted. No customer data, dates, manual judgements, or app counts are bundled.
This mechanical extraction never edits the source project.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path


def extract(path, names, imports, output):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    blocks, found = [], set()
    for node in tree.body:
        assigned = {target.id for target in getattr(node, "targets", []) if isinstance(target, ast.Name)}
        key = getattr(node, "name", None)
        if key in names or assigned & names:
            blocks.append(ast.get_source_segment(source, node))
            found.update(({key} if key else assigned) & names)
    if found != names:
        raise ValueError(f"Missing {names - found} in {path}")
    output.write_text(imports + "\n\n" + "\n\n\n".join(blocks) + "\n", encoding="utf-8")
    return {"source": path.name, "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "output": output.name, "selected_symbols": sorted(names)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    args = parser.parse_args()
    dest = Path(__file__).parent
    records = []
    specs = [
        ("analyze_feedback_overall.py", {"THEMES", "POSITIVE", "NEGATIVE", "POSITIVE_RE", "NEGATIVE_RE", "THEME_RE",
            "normalized", "word_count", "explicit_sentiment", "text_sentiment", "theme_hits", "classify", "ratio", "metrics", "grouped", "theme_metrics"},
         '"""Original English banking-feedback rules. See references/methods.md for limits."""\nimport re\nimport unicodedata\nfrom collections import Counter, OrderedDict, defaultdict', "theme_rules.py"),
        ("collect_apple.py", {"entries_from_feed", "parse_feed", "entry_label"},
         '"""Public Apple JSON/Atom parsing, extracted without source-specific configuration."""\nimport json\nfrom xml.etree import ElementTree', "apple_parser.py"),
        ("collect_google_play.py", {"nested", "parse_rpc", "language"},
         '"""Google RPC parser and deterministic English detection; langdetect loads lazily."""\nimport json\nimport re', "source_utils.py"),
        ("merge_reviews.py", {"require", "scalar", "column_name", "tag", "worksheet"},
         '"""Typed XLSX worksheet primitives; inline strings do not execute formulas."""\nimport json\nimport math\nfrom xml.etree import ElementTree as ET\nNS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"\nET.register_namespace("", NS)', "xlsx_core.py"),
    ]
    for filename, names, imports, output in specs:
        records.append(extract(args.project / "scripts" / filename, names, imports, dest / output))
    # Keep replay and verification standard-library-only; fresh collection needs
    # langdetect, loaded only when new text actually needs classification.
    utility = dest / "source_utils.py"
    source = utility.read_text(encoding="utf-8")
    source = source.replace('    """Conservative English subset; uncertain short text remains available."""',
        '    """Conservative English subset; uncertain short text remains available."""\n'
        '    from langdetect import DetectorFactory, detect_langs\n'
        '    from langdetect.lang_detect_exception import LangDetectException\n'
        '    DetectorFactory.seed = 0')
    utility.write_text(source, encoding="utf-8")
    # Reuse the tested visual foundation, without embedding the historical report.
    report = (args.project / "report_customer_feedback_2026-10-19.html").read_text(encoding="utf-8")
    import re
    css = re.search(r"<style>(.*?)</style>", report, re.S).group(1)
    (dest.parent / "assets" / "report.css").write_text(css + "\n", encoding="utf-8")
    (dest.parent / "references" / "resource_provenance.json").write_text(
        json.dumps({"origin": "SC Mobile / HSBC project, 2026-10-19", "extractions": records,
                    "note": "Selected rules/parsers only; no historical reviews or manual labels included."},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
