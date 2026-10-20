"""Collect public Google Play reviews with raw evidence and explicit time zones.

The library supplies the public RPC request format and field map. HTTP, retrying,
pagination, timestamp handling, preservation and validation are explicit here;
the library's high-level reviews() function silently catches errors, so it is
deliberately not used.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import ssl
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from google_play_scraper.constants.element import ElementSpecs
from google_play_scraper.constants.request import Formats
from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException


HK = timezone(timedelta(hours=8))
DetectorFactory.seed = 0
APPS = {
    "sc_mobile": ("SC Mobile Hong Kong", "com.scb.breezebanking.hk", "en-US"),
    "hsbc_hk": ("HSBC HK Mobile Banking", "hk.com.hsbc.hsbchkmobilebanking", "en"),
}
FIELDS = [
    "app", "app_id", "review_id", "review_time_hk", "review_time_utc",
    "review_timestamp_seconds", "rating", "text", "user_display_name",
    "thumbs_up", "review_app_version", "developer_reply", "reply_time_hk",
    "reply_time_utc", "detected_language", "language_status", "language_method",
    "language_probabilities", "within_six_month_window", "on_or_before_cutoff",
    "source", "request_language", "request_country", "source_url",
    "collected_at_utc", "raw_response_file", "raw_items_file", "raw_item_index",
]


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def nested(value, indexes, default=None):
    try:
        for index in indexes:
            value = value[index]
        return value
    except (IndexError, TypeError, KeyError):
        return default


def timestamps(seconds):
    if not isinstance(seconds, (int, float)):
        return None, None
    utc = datetime.fromtimestamp(seconds, timezone.utc)
    return utc.isoformat(), utc.astimezone(HK).isoformat()


def language(text):
    """Conservative English subset; uncertain short text remains available."""
    cjk = bool(re.search(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]", text))
    words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text)
    if not text.strip():
        return "und", "uncertain", "empty", {}
    if cjk:
        return "mixed" if len(words) >= 3 else "zh/ja/ko", "mixed" if len(words) >= 3 else "non_english", "script_check", {}
    short_english = {
        "good", "great", "excellent", "nice", "bad", "terrible", "awful", "amazing",
        "app", "apps", "very", "easy", "use", "to", "the", "best", "worst", "slow",
        "useless", "helpful", "convenient", "awesome", "perfect", "useful", "user",
        "friendly", "super", "really", "fast", "love", "it", "not", "working",
    }
    if words and len(words) <= 4 and all(w.lower() in short_english for w in words):
        return "en", "english", "short_english_word_list", {"en": None}
    if len("".join(words)) < 10 and not re.search(r"[^\x00-\x7f]", text):
        return "und", "uncertain", "short_text", {}
    try:
        probabilities = {item.lang: round(item.prob, 6) for item in detect_langs(text)}
    except LangDetectException:
        return "und", "uncertain", "langdetect_no_features", {}
    best = max(probabilities, key=probabilities.get)
    if best == "en" and probabilities[best] >= 0.80:
        status = "english"
    elif best != "en" and probabilities[best] >= 0.80:
        status = "non_english"
    else:
        status = "uncertain"
    return best, status, "langdetect_1.0.9_seed_0", probabilities


def http_capture(url, body, stem, extra_headers=None):
    """Save every received body (including errors), request and SHA-256."""
    stem.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}
    if extra_headers:
        headers.update(extra_headers)
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded;charset=UTF-8"
    last_error = None
    for attempt in range(1, 4):
        current = stem if attempt == 1 else stem.with_name(stem.name + f"_attempt{attempt}")
        request = Request(url, data=body, headers=headers)
        metadata = {
            "requested_url": url, "method": "POST" if body is not None else "GET",
            "request_headers": headers, "request_body": body.decode() if body else None,
            "started_at_utc": datetime.now(timezone.utc).isoformat(), "attempt": attempt,
        }
        try:
            # Explicit verified context: the scraper package changes the global default.
            with urlopen(request, timeout=35, context=ssl.create_default_context()) as response:
                payload = response.read()
                metadata.update(status=response.status, final_url=response.url,
                                response_headers=dict(response.headers.items()))
            current.with_suffix(".body").write_bytes(payload)
            metadata.update(bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
            dump(current.with_suffix(".http.json"), metadata)
            text = payload.decode("utf-8")
            if "com.google.play.gateway.proto.PlayGatewayError" in text:
                raise RuntimeError("Google Play returned PlayGatewayError")
            return text, current.with_suffix(".body"), metadata
        except Exception as error:
            last_error = error
            metadata["error"] = f"{type(error).__name__}: {error}"
            if isinstance(error, HTTPError):
                payload = error.read()
                current.with_suffix(".body").write_bytes(payload)
                metadata.update(status=error.code, bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
            dump(current.with_suffix(".http.json"), metadata)
            if isinstance(error, HTTPError) and error.code in (401, 403, 404):
                break
            if attempt < 3:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Request failed: {url}: {last_error}") from last_error


def parse_rpc(text):
    payload = text.split("\n", 1)[1].strip() if text.startswith(")]}'") else text.strip()
    try:
        frames = json.loads(payload)
    except json.JSONDecodeError:
        frames = []
        for line in payload.splitlines():
            if line.startswith("["):
                frames.extend(json.loads(line))
    frame = next((f for f in frames if isinstance(f, list) and len(f) > 2 and f[1] == "oCPfdb"), None)
    if frame is None or not isinstance(frame[2], str):
        raise ValueError("No oCPfdb review frame; response preserved for inspection")
    decoded = json.loads(frame[2])
    items = decoded[0] or [] if decoded else []
    token = nested(decoded, [-2, -1])
    return items, token if isinstance(token, str) and token else None, decoded


def normalize(item, app_key, request_lang, response_path, items_path, index, metadata, start, end):
    name, app_id, _ = APPS[app_key]
    # Read UNIX seconds directly; never depend on the execution host's timezone.
    seconds = nested(item, [5, 0])
    review_utc, review_hk = timestamps(seconds)
    reply_utc, reply_hk = timestamps(nested(item, [7, 2, 0]))
    extracted = {key: spec.extract_content(item) for key, spec in ElementSpecs.Review.items()
                 if key not in ("at", "repliedAt")}
    text = extracted.get("content") or ""
    detected, status, method, probabilities = language(text)
    identifier = extracted.get("reviewId")
    instant = datetime.fromtimestamp(seconds, timezone.utc) if review_utc else None
    return dict(zip(FIELDS, [
        name, app_id, identifier, review_hk, review_utc, seconds, extracted.get("score"),
        text, extracted.get("userName"), extracted.get("thumbsUpCount"),
        extracted.get("reviewCreatedVersion"), extracted.get("replyContent"), reply_hk,
        reply_utc, detected, status, method, probabilities,
        bool(instant and start <= instant < end), bool(instant and instant < end),
        "Google Play", request_lang, "HK",
        "https://play.google.com/store/apps/details?" + urlencode({"id": app_id, "hl": request_lang, "gl": "HK", "reviewId": identifier or ""}),
        metadata["started_at_utc"], response_path.as_posix(), items_path.as_posix(), index,
    ]))


def crawl(args):
    root = Path(args.output)
    app_root = root / args.app
    app_root.mkdir(parents=True, exist_ok=True)
    name, app_id, default_lang = APPS[args.app]
    lang = args.lang or default_lang
    start = datetime.fromisoformat(args.since).replace(tzinfo=HK)
    end = datetime.fromisoformat(args.as_of).replace(tzinfo=HK) + timedelta(days=1)
    summary = {
        "app": name, "app_id": app_id, "request_language": lang, "request_country": "HK",
        "sort": "NEWEST (RPC sort=2)", "start_inclusive_hk": start.isoformat(),
        "end_exclusive_hk": end.isoformat(), "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "pages": [], "errors": [], "stop_reason": None,
        "scope": "all_accessible_history" if args.all_history else "six_month_window_with_page_overflow",
    }
    dump(app_root / "crawl_summary.json", summary)
    page_url = "https://play.google.com/store/apps/details?" + urlencode({"id": app_id, "hl": lang, "gl": "HK"})
    try:
        page, _, _ = http_capture(page_url, None, app_root / "raw" / "store_listing")
        ld_items = []
        for match in re.finditer(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', page, re.S):
            ld_items.append(json.loads(html.unescape(match.group(1))))
        dump(app_root / "listing_metadata.json", {"source_url": page_url, "json_ld": ld_items})
    except Exception as error:
        summary["errors"].append("Listing snapshot: " + str(error))
    token = None
    tokens = set()
    seen = set()
    older_pages = 0
    duplicates = 0
    output = app_root / "reviews_fetched.jsonl"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite an existing crawl: {output}")
    try:
        with output.open("w", encoding="utf-8") as stream:
            for page_number in range(1, args.max_pages + 1):
                url = Formats.Reviews.build(lang=lang, country="hk")
                body = Formats.Reviews.build_body(app_id, 2, args.batch_size, "null", "null", token)
                text, response_path, metadata = http_capture(url, body, app_root / "raw" / f"page_{page_number:04d}")
                items, new_token, decoded = parse_rpc(text)
                items_path = app_root / "raw" / f"page_{page_number:04d}.decoded.json"
                dump(items_path, decoded)
                records = []
                for index, item in enumerate(items):
                    row = normalize(item, args.app, lang, response_path.relative_to(root), items_path.relative_to(root), index, metadata, start, end)
                    if not row["review_id"]:
                        raise ValueError(f"Missing review ID on page {page_number}, index {index}")
                    if row["review_id"] in seen:
                        duplicates += 1
                        continue
                    seen.add(row["review_id"])
                    records.append(row)
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                dates = sorted(r["review_time_hk"] for r in records if r["review_time_hk"])
                information = {
                    "page": page_number, "returned": len(items), "new_unique": len(records),
                    "earliest_hk": dates[0] if dates else None, "latest_hk": dates[-1] if dates else None,
                    "within_window": sum(r["within_six_month_window"] for r in records),
                    "english_in_window": sum(r["within_six_month_window"] and r["language_status"] == "english" for r in records),
                    "has_next_token": bool(new_token),
                }
                summary["pages"].append(information)
                dump(app_root / "crawl_summary.json", summary)
                print(json.dumps({"app": args.app, "total_unique": len(seen), **information}), flush=True)
                all_instants = [nested(item, [5, 0]) for item in items]
                all_dated = bool(all_instants) and all(isinstance(x, (float, int)) for x in all_instants)
                older_pages = older_pages + 1 if all_dated and max(all_instants) < start.timestamp() else 0
                if not new_token:
                    summary["stop_reason"] = "endpoint_exhausted_no_next_token"
                    break
                if new_token in tokens:
                    summary["stop_reason"] = "repeated_pagination_token"
                    break
                if not records:
                    summary["stop_reason"] = "no_new_unique_records"
                    break
                if older_pages >= 2 and not args.all_history:
                    summary["stop_reason"] = "two_pages_entirely_before_requested_window"
                    break
                tokens.add(new_token)
                token = new_token
                time.sleep(args.pause)
            else:
                summary["stop_reason"] = "max_pages_safety_limit"
    except Exception as error:
        summary["errors"].append(f"{type(error).__name__}: {error}")
        summary["stop_reason"] = "request_or_parse_failure"
        raise
    finally:
        summary.update(unique_fetched=len(seen), duplicate_occurrences=duplicates, finished_at_utc=datetime.now(timezone.utc).isoformat())
        dump(app_root / "crawl_summary.json", summary)


def write_csv(path, rows):
    # UTF-8 BOM makes the file directly readable in Excel on Windows.
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value for key, value in row.items()})


def export(args):
    root = Path(args.output)
    rows = []
    summaries = []
    for key in APPS:
        source = root / key / "reviews_fetched.jsonl"
        if source.exists():
            rows.extend(json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line)
            summaries.append(json.loads((root / key / "crawl_summary.json").read_text(encoding="utf-8")))
    override_path = Path(__file__).with_name("language_overrides.json")
    overrides = json.loads(override_path.read_text(encoding="utf-8")) if override_path.exists() else {}
    applied = []
    for row in rows:
        override = overrides.get(row["review_id"])
        if override:
            if override["app_id"] != row["app_id"] or override["expected_text"] != row["text"]:
                raise ValueError("Language override does not match preserved text: " + row["review_id"])
            applied.append({"review_id": row["review_id"], "app": row["app"], "text": row["text"],
                            "previous_language": row["detected_language"], "previous_status": row["language_status"],
                            "new_language": override["language"], "new_status": override["status"], "reason": override["reason"]})
            row.update(detected_language=override["language"], language_status=override["status"], language_method="manual_review_2026-10-19")
    dump(root / "manual_language_review.json", applied)
    rows.sort(key=lambda r: (r["review_timestamp_seconds"] or 0, r["app_id"], r["review_id"]), reverse=True)
    english = [r for r in rows if r["on_or_before_cutoff"] and r["language_status"] == "english"]
    window = [r for r in english if r["within_six_month_window"]]
    other = [r for r in rows if r["on_or_before_cutoff"] and r["language_status"] != "english"]
    for filename, subset in [("all_languages_fetched", rows), ("english_as_of_2026-10-19", english), ("english_six_months", window), ("other_languages_or_uncertain", other)]:
        write_csv(root / (filename + ".csv"), subset)
        dump(root / (filename + ".json"), subset)
    statistics = []
    for key, (name, app_id, _) in APPS.items():
        part = [r for r in rows if r["app_id"] == app_id]
        valid = [r for r in part if r["within_six_month_window"]]
        en = [r for r in valid if r["language_status"] == "english"]
        statistics.append({
            "app": name, "fetched_unique": len(part), "all_languages_in_window": len(valid),
            "all_languages_latest_hk": part[0]["review_time_hk"] if part else None,
            "all_languages_earliest_hk": part[-1]["review_time_hk"] if part else None,
            "english_fetched_as_of": sum(r["on_or_before_cutoff"] and r["language_status"] == "english" for r in part),
            "english_in_window": len(en), "other_or_uncertain_in_window": len(valid) - len(en),
            "english_by_month": dict(sorted(Counter(r["review_time_hk"][:7] for r in en).items())),
            "language_status_in_window": dict(Counter(r["language_status"] for r in valid)),
            "english_latest_hk": en[0]["review_time_hk"] if en else None,
            "english_earliest_hk": en[-1]["review_time_hk"] if en else None,
            "with_developer_reply": sum(bool(r["developer_reply"]) for r in en),
            "with_app_version": sum(bool(r["review_app_version"]) for r in en),
        })
    verification = {"record_count": len(rows), "errors": [], "raw_bodies_verified": 0,
                    "review_pages_decoded_from_original_http": 0, "records_traced_to_raw": 0}
    decoded_cache = {}
    for row in rows:
        path = row["raw_items_file"]
        if path not in decoded_cache:
            decoded_cache[path] = json.loads((root / path).read_text(encoding="utf-8"))
            original = (root / row["raw_response_file"]).read_text(encoding="utf-8")
            _, _, original_decoded = parse_rpc(original)
            if original_decoded != decoded_cache[path]:
                verification["errors"].append("Decoded payload differs from original HTTP: " + path)
            else:
                verification["review_pages_decoded_from_original_http"] += 1
        item = decoded_cache[path][0][row["raw_item_index"]]
        expected_utc, expected_hk = timestamps(nested(item, [5, 0]))
        if (item[0] != row["review_id"] or item[4] != row["text"]
                or nested(item, [5, 0]) != row["review_timestamp_seconds"]
                or item[2] != row["rating"] or expected_utc != row["review_time_utc"]
                or expected_hk != row["review_time_hk"]):
            verification["errors"].append("Raw evidence mismatch: " + row["review_id"])
        else:
            verification["records_traced_to_raw"] += 1
    for metadata_path in root.glob("*/raw/*.http.json"):
        meta = json.loads(metadata_path.read_text(encoding="utf-8"))
        body_path = metadata_path.with_name(metadata_path.name.removesuffix(".http.json") + ".body")
        if "sha256" in meta:
            if hashlib.sha256(body_path.read_bytes()).hexdigest() != meta["sha256"]:
                verification["errors"].append("SHA-256 mismatch: " + str(body_path))
            else:
                verification["raw_bodies_verified"] += 1
    keys = [(r["app_id"], r["review_id"]) for r in rows]
    verification["unique_app_review_ids"] = len(keys) == len(set(keys))
    verification["newest_first"] = all((rows[i]["review_timestamp_seconds"] or 0) >= (rows[i+1]["review_timestamp_seconds"] or 0) for i in range(len(rows)-1))
    verification["english_export_respects_cutoff"] = all(r["on_or_before_cutoff"] for r in english)
    verification["missing_dates"] = sum(not r["review_time_hk"] for r in rows)
    verification["invalid_ratings"] = sum(r["rating"] not in range(1, 6) for r in rows)
    dump(root / "verification.json", verification)
    report = {"as_of_hk": args.as_of, "since_hk": args.since, "statistics": statistics, "crawls": summaries,
              "manual_language_corrections": len(applied), "verification": verification}
    dump(root / "collection_report.json", report)
    build_viewer(root, english, report)
    write_notes(root, report, len(rows), len(window), len(english))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if verification["errors"] or not verification["unique_app_review_ids"] or not verification["newest_first"]:
        raise RuntimeError("Verification failed; inspect verification.json")


def write_notes(root, report, total, window, english):
    lines = [
        "# Google Play review collection / 评论抓取结果", "",
        f"Cutoff: {report['as_of_hk']} 23:59:59.999999, Hong Kong (UTC+08:00).",
        f"Requested window: {report['since_hk']} through {report['as_of_hk']} inclusive.", "",
        f"Unique fetched records: {total}; English in requested window: {window}; English including fetched older page overflow: {english}.", "",
        "## Files", "",
        "- `review_browser.html`: offline searchable English review viewer, newest first.",
        "- `english_six_months.csv` / `.json`: English subset in the requested six-month window.",
        "- `english_as_of_2026-10-19.csv` / `.json`: English including any older records returned on boundary pages; this is NOT all-time history.",
        "- `all_languages_fetched.csv` / `.json`: every unique returned record, including non-English, uncertain and boundary overflow.",
        "- `other_languages_or_uncertain.csv` / `.json`: records excluded from the English subset, retained for manual language review.",
        "- Each app's `raw/*.body`: original HTTP response bytes; `.http.json`: request, timestamp, headers, SHA-256.",
        "- `raw/page_*.decoded.json`: decoded RPC payload, preserving every original review array and pagination token.",
        "- `collection_report.json`, `verification.json`: counts, stopping reason, coverage and evidence checks.", "",
        "## Interpretation / 核查方式", "",
        "All CSV/JSON exports are sorted by the returned review timestamp, descending. CSV is UTF-8 with BOM for Excel.",
        "Open a source link, select newest reviews, and compare the exact text, public display name, star rating and date. Review-specific links are best effort: Google may show the app page instead of focusing a review.",
        "`hl` selects request language, not verified author language or residence. Both apps use `gl=HK`; English detection is a separate, fallible step.",
        "English selection uses deterministic langdetect (confidence >=0.80), a documented short-English word list, and script checks. Ambiguous and mixed-language records remain in the other/all files.",
        "Recent excluded records were manually reviewed; 18 clear English short-text misclassifications are corrected via scripts/language_overrides.json. Every correction checks the exact app ID and unchanged text. Applied corrections and reasons are saved in manual_language_review.json. Historical labels outside the six-month window remain primarily automatic.",
        "Per-page English counts in crawl_summary.json and language labels in reviews_fetched.jsonl are preliminary automatic labels captured during downloading. Final corrected counts and labels are in collection_report.json and the exported CSV/JSON files.",
        "Text is preserved exactly as returned by Google; this script does not translate, summarize or invent comments. Google's own localization behavior cannot be ruled out from text alone.",
        "Review time is Google's returned review timestamp and may reflect an edited review; original first-post time is not independently established. Developer replies have separate timestamps.",
        "2026-10-19 is an upper bound, not a claimed newest observed review date. Missing dates/months are not assumed to have zero feedback.",
        "This collection records what this public endpoint returned for this locale and sort, not a guarantee of every Google Play review. Listing aggregate rating counts are not collected text-review counts.",
        "The final partial boundary pages are preserved. Default crawling stops after two pages entirely older than the requested window. With --all-history it continues until endpoint exhaustion, a repeated token, an error, or the recorded safety limit. See each crawl's scope and stop_reason.",
        "Raw responses include public display names/avatar URLs returned by Google. No private account data or identity inference is requested.", "",
    ]
    (root / "README.md").write_text("\n".join(lines), encoding="utf-8")


def build_viewer(root, rows, report):
    # Escaped embedded JSON and textContent keep third-party review text inert.
    payload = json.dumps({"reviews": rows, "report": report}, ensure_ascii=False).replace("<", "\\u003c")
    template = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Google Play 原文评论核查</title><style>
body{font:15px/1.6 system-ui,sans-serif;margin:24px auto;padding:0 22px;max-width:1250px;background:#f5f7fa;color:#182334}h1{font-size:25px;margin-bottom:8px}.note{color:#526176}select,input,button{font:inherit;padding:7px 10px;border:1px solid #bdc9d8;border-radius:6px;background:white}input[type=search]{width:min(440px,80%)}.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:20px 0}article{background:white;border:1px solid #d7e0eb;border-radius:9px;padding:18px;margin:12px 0}.meta{color:#526176;font-size:13px}.text{white-space:pre-wrap;overflow-wrap:anywhere;font-size:16px;margin:12px 0}.reply{border-left:3px solid #c7d7e9;padding-left:12px;white-space:pre-wrap}.stars{color:#825400}.summary{background:#e9f0f8;padding:14px;border-radius:8px}a{color:#1456a0}.pager{display:flex;gap:14px;align-items:center;margin:20px 0}code{overflow-wrap:anywhere}</style>
<h1>Google Play 英文评论原文核查</h1><p class="note">截至 2026/10/19（香港时间），按接口返回的评论时间从新到老。正文没有经本脚本翻译或改写。英语识别可能出错，全部语言与待确认记录另存于 CSV/JSON。</p>
<div id="summary" class="summary"></div><div class="controls"><select id="app"><option value="">两个应用</option><option>SC Mobile Hong Kong</option><option>HSBC HK Mobile Banking</option></select><input id="search" type="search" placeholder="搜索英文原文、用户名或评论 ID"><label><input id="window" type="checkbox" checked>仅 2026/04/19–2026/10/19</label><select id="rating"><option value="">全部星级</option><option value="1">1 星</option><option value="2">2 星</option><option value="3">3 星</option><option value="4">4 星</option><option value="5">5 星</option></select></div>
<div class="pager"><button id="prev">上一页</button><span id="count"></span><button id="next">下一页</button></div><main id="reviews"></main><p class="note">原始 HTTP 响应、请求参数与哈希见同目录每个应用的 raw 文件夹。页面不联网；“Google Play 核查”链接需要网络。网页当前显示可能受语言、地区、设备和评论编辑/删除影响。</p>
<script id="data" type="application/json">__PAYLOAD__</script><script>
const data=JSON.parse(document.getElementById('data').textContent),$=id=>document.getElementById(id);let page=0,filtered=[];const size=50;
$('summary').textContent=data.report.statistics.map(s=>`${s.app}：共取回 ${s.fetched_unique} 条，六个月内 ${s.all_languages_in_window} 条，其中英文 ${s.english_in_window} 条；最新英文 ${s.english_latest_hk||'未取得'}`).join(' ｜ ');
function element(tag,text,className){const e=document.createElement(tag);e.textContent=text;if(className)e.className=className;return e}
function render(){const q=$('search').value.toLowerCase();filtered=data.reviews.filter(r=>(!$('app').value||r.app===$('app').value)&&(!$('window').checked||r.within_six_month_window)&&(!$('rating').value||r.rating==Number($('rating').value))&&(!q||[r.text,r.user_display_name,r.review_id].join(' ').toLowerCase().includes(q)));const pages=Math.max(1,Math.ceil(filtered.length/size));page=Math.max(0,Math.min(page,pages-1));$('count').textContent=`${filtered.length} 条匹配 · 第 ${page+1}/${pages} 页 · 每页 ${size} 条`;$('prev').disabled=page===0;$('next').disabled=page>=pages-1;const container=$('reviews');container.replaceChildren();for(const r of filtered.slice(page*size,(page+1)*size)){const a=element('article','');a.append(element('strong',r.app+' · '+r.review_time_hk.replace('T',' ')));a.append(element('div',`${'★'.repeat(r.rating||0)} (${r.rating}/5) · ${r.user_display_name||''} · 有用 ${r.thumbs_up??''} · 版本 ${r.review_app_version||'未提供'}`,'meta stars'));a.append(element('p',r.text,'text'));if(r.developer_reply)a.append(element('div','开发者回复 '+(r.reply_time_hk||'')+'\n'+r.developer_reply,'reply'));a.append(element('div','Review ID: '+r.review_id,'meta'));const link=element('a','Google Play 核查 ↗');link.href=r.source_url;link.target='_blank';link.rel='noopener noreferrer';a.append(link);a.append(element('div',`证据：${r.raw_items_file}，数组索引 ${r.raw_item_index}；语言判断 ${r.language_method}`,'meta'));container.append(a)}}
for(const id of ['app','search','window','rating'])$(id).addEventListener(id==='search'?'input':'change',()=>{page=0;render()});$('prev').onclick=()=>{page--;render();window.scrollTo(0,0)};$('next').onclick=()=>{page++;render();window.scrollTo(0,0)};render();
</script></html>'''
    # A literal newline inside a JS quoted string must stay escaped in the HTML.
    template = template.replace("+'\n'+r.developer_reply", "+'\\n'+r.developer_reply")
    (root / "review_browser.html").write_text(template.replace("__PAYLOAD__", payload), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["crawl", "export"])
    parser.add_argument("--app", choices=list(APPS))
    parser.add_argument("--lang", help="Override English request locale, e.g. en or en-US")
    parser.add_argument("--all-history", action="store_true", help="Continue beyond the six-month window to measure accessible history")
    parser.add_argument("--output", required=True)
    parser.add_argument("--as-of", default="2026-10-19")
    parser.add_argument("--since", default="2026-04-19")
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--pause", type=float, default=0.8)
    args = parser.parse_args()
    if args.mode == "crawl":
        if not args.app:
            parser.error("crawl requires --app")
        crawl(args)
    else:
        export(args)


if __name__ == "__main__":
    main()
