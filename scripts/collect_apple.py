"""Apple App Store public-feed collection, with original HTTP evidence.

Only public, unauthenticated endpoints are used. Storefront is HK; UI language
does not establish the language of a review. Raw responses remain unchanged.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from xml.etree import ElementTree

from collect_google_play import HK, dump, http_capture, language


PROBES = [
    ("apple_lookup_initial_ids", "https://itunes.apple.com/lookup?id=445795688,1164066737&country=hk"),
    ("apple_search_sc", "https://itunes.apple.com/search?term=SC%20Mobile%20Hong%20Kong&country=hk&entity=software&limit=10"),
    ("apple_search_hsbc", "https://itunes.apple.com/search?term=HSBC%20HK%20Mobile%20Banking&country=hk&entity=software&limit=10"),
    ("sc_official_mobile_page", "https://www.sc.com/hk/bank-with-us/sc-mobile/"),
    ("sc_rss_initial_id", "https://itunes.apple.com/hk/rss/customerreviews/page=1/id=445795688/sortBy=mostRecent/json?l=en"),
    ("hsbc_rss_initial_id", "https://itunes.apple.com/hk/rss/customerreviews/page=1/id=1164066737/sortBy=mostRecent/json?l=en"),
]

FEED_VARIANTS = [
    (f"{key}_{variant}", url)
    for key, appid, slug in [("sc_mobile", "445795688", "sc-mobile-hong-kong"), ("hsbc_hk", "1164066737", "hsbc-hk-mobile-banking")]
    for variant, url in [
        ("json_no_query", f"https://itunes.apple.com/hk/rss/customerreviews/page=1/id={appid}/sortBy=mostRecent/json"),
        ("xml_no_query", f"https://itunes.apple.com/hk/rss/customerreviews/page=1/id={appid}/sortBy=mostRecent/xml"),
        ("json_lowercase", f"https://itunes.apple.com/hk/rss/customerreviews/page=1/id={appid}/sortby=mostrecent/json"),
        ("json_compact", f"https://itunes.apple.com/hk/rss/customerreviews/id={appid}/sortBy=mostRecent/json"),
        ("web_english", f"https://apps.apple.com/hk/app/{slug}/id{appid}?l=en-GB"),
        ("web_reviews", f"https://apps.apple.com/hk/app/{slug}/id{appid}?l=en-GB&see-all=reviews"),
        ("legacy_reviews", f"https://itunes.apple.com/hk/customer-reviews/id{appid}?displayable-kind=11"),
    ]
]

RSS_RECHECK = [
    (f"{key}_{variant}", url)
    for key, appid in [("sc_mobile", "445795688"), ("hsbc_hk", "1164066737")]
    for variant, url in [
        ("en_gb", f"https://itunes.apple.com/hk/rss/customerreviews/page=1/id={appid}/sortBy=mostRecent/json?l=en-GB"),
        ("en_us", f"https://itunes.apple.com/hk/rss/customerreviews/page=1/id={appid}/sortBy=mostRecent/json?l=en-US"),
        ("page2", f"https://itunes.apple.com/hk/rss/customerreviews/page=2/id={appid}/sortBy=mostRecent/json"),
        ("reviews_first", f"https://itunes.apple.com/hk/rss/customerreviews/id={appid}/sortBy=mostRecent/page=1/json"),
        ("query_country", f"https://itunes.apple.com/rss/customerreviews/page=1/id={appid}/sortBy=mostRecent/json?cc=hk"),
        ("legacy_contents", f"https://itunes.apple.com/WebObjects/MZStore.woa/wa/viewContentsUserReviews?id={appid}&pageNumber=0&sortOrdering=4&type=Purple+Software&displayable-kind=11&cc=hk"),
    ]
]

RSS_LIMIT = [(key + "_page11", f"https://itunes.apple.com/hk/rss/customerreviews/page=11/id={appid}/sortBy=mostRecent/json?l={lang}")
             for key, appid, lang in [("sc_mobile", "445795688", "en-GB"), ("hsbc_hk", "1164066737", "en-US")]]

HEADER_PROFILES = {
    "python": {"User-Agent": "Python-urllib/3.13"},
    "browser": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
    "storefront": {"User-Agent": "iTunes/12.13.3 (Windows; Microsoft Windows 10 x64 Professional Edition (Build 19045); x64)", "X-Apple-Store-Front": "143463-2,32", "Accept-Language": "en-HK,en;q=0.9"},
}

APPS = {
    "sc_mobile": ("SC Mobile Hong Kong", "445795688", "sc-mobile-hong-kong"),
    "hsbc_hk": ("HSBC HK Mobile Banking", "1164066737", "hsbc-hk-mobile-banking"),
}
FIELDS = ["source", "storefront", "app", "app_id", "review_id", "review_time_hk",
          "review_time_utc", "source_updated_time", "review_timestamp_seconds", "title",
          "text", "rating", "user_display_name", "review_app_version", "vote_sum", "vote_count",
          "developer_reply", "reply_availability", "detected_language", "language_status",
          "language_method", "language_probabilities", "within_six_month_window", "on_or_before_cutoff",
          "source_url", "feed_review_url", "collected_at_utc", "raw_response_file", "raw_entry_index"]


def entries_from_feed(decoded):
    entries = decoded.get("feed", {}).get("entry", [])
    if isinstance(entries, dict):
        entries = [entries]
    return [(index, entry) for index, entry in enumerate(entries) if "im:rating" in entry]


def parse_feed(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        root = ElementTree.fromstring(text)
        def key(tag):
            if tag.startswith("{http://itunes.apple.com/rss}"):
                return "im:" + tag.split("}", 1)[1]
            return tag.split("}", 1)[-1]
        def convert(element):
            result = {"attributes": dict(element.attrib)} if element.attrib else {}
            if len(element) == 0:
                result["label"] = element.text or ""
            else:
                for child in element:
                    name = key(child.tag)
                    value = convert(child)
                    if name in ("entry", "link"):
                        result.setdefault(name, []).append(value)
                    elif name in result:
                        old = result[name]
                        result[name] = old + [value] if isinstance(old, list) else [old, value]
                    else:
                        result[name] = value
            return result
        if key(root.tag) != "feed":
            raise ValueError("Response is neither a JSON feed nor an Atom feed")
        return {"feed": convert(root)}


def entry_label(entry, key, default=""):
    value = entry.get(key, {})
    if isinstance(value, list):
        # Atom can include both text and HTML content; preserve the text version.
        value = next((part for part in value if part.get("attributes", {}).get("type") == "text"), value[0])
    return value.get("label", default)


def parse_entry(entry, args, path, index, meta):
    name, appid, slug = APPS[args.app]
    updated = entry.get("updated", {}).get("label")
    instant = datetime.fromisoformat(updated)
    if instant.tzinfo is None:
        raise ValueError("Source timestamp lacks a UTC offset")
    start = datetime.fromisoformat(args.since).replace(tzinfo=HK)
    end = datetime.fromisoformat(args.as_of).replace(tzinfo=HK) + timedelta(days=1)
    title = entry_label(entry, "title")
    text = entry_label(entry, "content")
    detected, status, method, probabilities = language(title + "\n" + text)
    identifier = entry["id"]["label"]
    links = entry.get("link", [])
    links = [links] if isinstance(links, dict) else links
    feed_url = next((link.get("attributes", {}).get("href") for link in links), None)
    def integer(field):
        value = entry.get(field, {}).get("label")
        return int(value) if value is not None else None
    return dict(zip(FIELDS, [
        "Apple App Store RSS", "hk", name, appid, identifier, instant.astimezone(HK).isoformat(),
        instant.astimezone(timezone.utc).isoformat(), updated, instant.timestamp(), title, text,
        integer("im:rating"), entry.get("author", {}).get("name", {}).get("label"),
        entry.get("im:version", {}).get("label"), integer("im:voteSum"), integer("im:voteCount"),
        None, "not_exposed_by_public_rss", detected, status, method, probabilities,
        start <= instant < end, instant < end,
        f"https://apps.apple.com/hk/app/{slug}/id{appid}?l=en-GB&see-all=reviews&platform=iphone",
        feed_url, meta["started_at_utc"], path.relative_to(Path(args.output)).as_posix(), index,
    ]))


def crawl(args):
    root = Path(args.output)
    app_root = root / args.app
    name, appid, _ = APPS[args.app]
    output = app_root / "reviews_fetched.jsonl"
    if output.exists() and not args.resume:
        raise FileExistsError(f"Refusing to overwrite existing crawl: {output}")
    app_root.mkdir(parents=True, exist_ok=True)
    summary = {"app": name, "app_id": appid, "storefront": "hk", "sort": "mostRecent",
               "request_profile": "browser", "language_filter": "post_collection_title_and_body",
               "request_language": "en-GB" if args.app == "sc_mobile" else "en-US",
               "started_at_utc": datetime.now(timezone.utc).isoformat(), "pages": [], "errors": [],
               "stop_reason": None, "duplicate_occurrences": 0, "unique_fetched": 0,
               "since_hk": args.since, "as_of_hk": args.as_of}
    if args.resume:
        summary = json.loads((app_root / "crawl_summary.json").read_text(encoding="utf-8"))
        summary["repair_started_at_utc"] = datetime.now(timezone.utc).isoformat()
        summary["stop_reason"] = None
        if summary.get("errors"):
            summary.setdefault("historical_resolved_errors", []).extend(summary["errors"])
            summary["errors"] = []
    repair_id = datetime.now(timezone.utc).strftime("%H%M%S%f")
    dump(app_root / "crawl_summary.json", summary)
    seen = {json.loads(line)["review_id"] for line in output.read_text(encoding="utf-8").splitlines() if line} if args.resume else set()
    try:
        # Metadata is verified independently from review entries.
        if not args.resume:
            lookup_url = f"https://itunes.apple.com/lookup?id={appid}&country=hk"
            lookup, _, _ = http_capture(lookup_url, None, app_root / "raw" / "lookup", HEADER_PROFILES["browser"])
            dump(app_root / "listing_metadata.json", json.loads(lookup))
        pages = list(summary.get("unresolved_empty_pages", [])) if args.resume else range(1, args.max_pages + 1)
        with output.open("a" if args.resume else "w", encoding="utf-8") as stream:
            for page_number in pages:
                feed_language = summary["request_language"]
                base = f"https://itunes.apple.com/hk/rss/customerreviews/page={page_number}/id={appid}/sortBy=mostRecent/json"
                candidates = [base + f"?l={feed_language}",
                              base + ("?l=en-US" if feed_language == "en-GB" else "?l=en-GB"),
                              base + "?l=en", base,
                              f"https://itunes.apple.com/hk/rss/customerreviews/id={appid}/sortBy=mostRecent/page={page_number}/json?l={feed_language}",
                              base + f"?l={feed_language}&limit=50"]
                if args.resume:
                    xml_base = base.removesuffix("/json") + "/xml"
                    candidates = [xml_base + "?l=en-GB", xml_base + "?l=en-US", xml_base + "?l=en", xml_base,
                                  base + "?l=zh-Hant", base + "?l=zh-Hant-HK", base + "?l=zh-HK",
                                  base + "?l=en-GB&urlDesc=/customerreviews/page=" + str(page_number-1) + f"/id={appid}/sortBy=mostRecent/json",
                                  base + "?l=en-US&urlDesc=/customerreviews/page=" + str(page_number-1) + f"/id={appid}/sortBy=mostRecent/json"]
                for attempt, url in enumerate(candidates, 1):
                    variant = f"repair{repair_id}_" if args.resume else "variant"
                    stem = app_root / "raw" / f"page_{page_number:02d}_{variant}{attempt}"
                    body, path, meta = http_capture(url, None, stem, HEADER_PROFILES["browser"])
                    decoded = parse_feed(body)
                    entries = entries_from_feed(decoded)
                    if entries:
                        break
                    time.sleep(0.6)
                new = []
                for index, entry in entries:
                    row = parse_entry(entry, args, path, index, meta)
                    if row["review_id"] in seen:
                        summary["duplicate_occurrences"] += 1
                        continue
                    seen.add(row["review_id"])
                    new.append(row)
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                links = {link.get("attributes", {}).get("rel"): link.get("attributes", {}).get("href") for link in decoded.get("feed", {}).get("link", [])}
                last_match = re.search(r"page=(\d+)", links.get("last") or "")
                last_page = int(last_match.group(1)) if last_match else None
                times = sorted(row["review_time_hk"] for row in new)
                info = {"page": page_number, "returned": len(entries), "new_unique": len(new),
                        "earliest_hk": times[0] if times else None, "latest_hk": times[-1] if times else None,
                        "in_six_month_window": sum(row["within_six_month_window"] for row in new),
                        "english_in_window_preliminary": sum(row["within_six_month_window"] and row["language_status"] == "english" for row in new),
                        "advertised_last_page": last_page, "feed_next_url": links.get("next")}
                summary["pages"].append(info)
                if entries and page_number in summary.get("unresolved_empty_pages", []):
                    summary["unresolved_empty_pages"].remove(page_number)
                summary["unique_fetched"] = len(seen)
                dump(app_root / "crawl_summary.json", summary)
                print(json.dumps({"app": args.app, "total_unique": len(seen), **info}, ensure_ascii=True), flush=True)
                if not entries:
                    summary.setdefault("unresolved_empty_pages", []).append(page_number)
                    # Do not let an empty intermediate response hide later pages.
                    if page_number < 10:
                        continue
                    summary["stop_reason"] = "page_ten_reached_with_empty_pages_not_complete"
                    break
                if not new:
                    if args.resume:
                        continue
                    summary["stop_reason"] = "repeated_records_no_new_ids"
                    break
                if last_page is not None and page_number >= last_page:
                    summary["stop_reason"] = "public_feed_last_advertised_page_not_all_time_completeness"
                    break
                if not links.get("next"):
                    summary["stop_reason"] = "feed_no_next_link"
                    break
                time.sleep(0.9)
            else:
                summary["stop_reason"] = "repair_pass_finished" if args.resume else "max_pages_safety_limit"
    except Exception as error:
        summary["errors"].append(f"{type(error).__name__}: {error}")
        summary["stop_reason"] = "request_or_parse_failure"
        raise
    finally:
        summary.update(unique_fetched=len(seen), finished_at_utc=datetime.now(timezone.utc).isoformat())
        dump(app_root / "crawl_summary.json", summary)


def export(args):
    root = Path(args.output)
    rows, summaries = [], []
    for key in APPS:
        source = root / key / "reviews_fetched.jsonl"
        if source.exists():
            rows.extend(json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line)
            summaries.append(json.loads((root / key / "crawl_summary.json").read_text(encoding="utf-8")))
    override_path = Path(__file__).with_name("apple_language_overrides.json")
    overrides = json.loads(override_path.read_text(encoding="utf-8")) if override_path.exists() else {}
    applied = []
    for row in rows:
        override = overrides.get(row["review_id"])
        if override:
            if row["app_id"] != override["app_id"] or row["title"] != override["expected_title"] or row["text"] != override["expected_text"]:
                raise ValueError("Language override differs from preserved source: " + row["review_id"])
            applied.append({"review_id": row["review_id"], "app": row["app"], "previous_status": row["language_status"], **override})
            row.update(detected_language=override["language"], language_status=override["status"], language_method="manual_review_2026-10-19")
    dump(root / "manual_language_review.json", applied)
    rows.sort(key=lambda row: (row["review_timestamp_seconds"], row["app_id"], row["review_id"]), reverse=True)
    english = [r for r in rows if r["on_or_before_cutoff"] and r["language_status"] == "english"]
    window = [r for r in english if r["within_six_month_window"]]
    subsets = {"all_languages_fetched": rows, "english_as_of_2026-10-19": english,
               "english_six_months": window,
               "other_languages_or_uncertain": [r for r in rows if r["on_or_before_cutoff"] and r["language_status"] != "english"]}
    for filename, subset in subsets.items():
        dump(root / (filename + ".json"), subset)
        with (root / (filename + ".csv")).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows({key: json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value for key, value in row.items()} for row in subset)
    statistics = []
    for _, (name, appid, _) in APPS.items():
        part = [r for r in rows if r["app_id"] == appid]
        valid = [r for r in part if r["within_six_month_window"]]
        en = [r for r in valid if r["language_status"] == "english"]
        statistics.append({"app": name, "app_id": appid, "fetched_unique": len(part),
                           "all_languages_in_window": len(valid), "english_in_window": len(en),
                           "english_fetched_as_of": sum(r["language_status"] == "english" and r["on_or_before_cutoff"] for r in part),
                           "all_languages_latest_hk": part[0]["review_time_hk"] if part else None,
                           "all_languages_earliest_hk": part[-1]["review_time_hk"] if part else None,
                           "english_latest_hk": en[0]["review_time_hk"] if en else None,
                           "english_earliest_hk": en[-1]["review_time_hk"] if en else None,
                           "english_by_month": dict(sorted(Counter(r["review_time_hk"][:7] for r in en).items())),
                           "language_status_in_window": dict(Counter(r["language_status"] for r in valid)),
                           "oldest_fetched_precedes_window": bool(part and part[-1]["review_time_hk"][:10] < args.since)})
    verification = {"record_count": len(rows), "records_traced_to_original_http": 0,
                    "raw_bodies_verified": 0, "errors": []}
    cache = {}
    for row in rows:
        filename = row["raw_response_file"]
        if filename not in cache:
            cache[filename] = parse_feed((root / filename).read_text(encoding="utf-8"))
        entries = cache[filename]["feed"]["entry"]
        if isinstance(entries, dict):
            entries = [entries]
        entry = entries[row["raw_entry_index"]]
        updated = datetime.fromisoformat(entry["updated"]["label"])
        if (entry["id"]["label"] != row["review_id"] or entry_label(entry, "content") != row["text"]
                or entry_label(entry, "title") != row["title"] or int(entry["im:rating"]["label"]) != row["rating"]
                or updated.timestamp() != row["review_timestamp_seconds"]
                or updated.astimezone(HK).isoformat() != row["review_time_hk"]):
            verification["errors"].append("Raw mismatch: " + row["review_id"])
        else:
            verification["records_traced_to_original_http"] += 1
    for path in root.glob("*/raw/*.http.json"):
        meta = json.loads(path.read_text(encoding="utf-8"))
        if "sha256" in meta:
            payload_path = path.with_name(path.name.removesuffix(".http.json") + ".body")
            if hashlib.sha256(payload_path.read_bytes()).hexdigest() != meta["sha256"]:
                verification["errors"].append("SHA-256 mismatch: " + str(path))
            else:
                verification["raw_bodies_verified"] += 1
    ids = [(r["app_id"], r["review_id"]) for r in rows]
    verification.update(unique_app_review_ids=len(ids) == len(set(ids)),
                        newest_first=all(rows[i]["review_timestamp_seconds"] >= rows[i+1]["review_timestamp_seconds"] for i in range(len(rows)-1)),
                        invalid_ratings=sum(r["rating"] not in range(1, 6) for r in rows),
                        english_export_respects_cutoff=all(r["on_or_before_cutoff"] for r in english))
    dump(root / "verification.json", verification)
    report = {"source": "Apple App Store public RSS", "storefront": "hk", "since_hk": args.since,
              "as_of_hk": args.as_of, "statistics": statistics, "crawls": summaries,
              "manual_language_corrections": len(applied), "verification": verification}
    dump(root / "collection_report.json", report)
    template = Path(__file__).with_name("apple_review_browser.html").read_text(encoding="utf-8")
    payload = json.dumps({"reviews": english, "report": report}, ensure_ascii=False).replace("<", "\\u003c")
    (root / "review_browser.html").write_text(template.replace("__PAYLOAD__", payload), encoding="utf-8")
    print(json.dumps({"statistics": statistics, "verification": verification, "english_all_fetched": len(english),
                      "english_six_months": len(window), "manual_language_corrections": len(applied)}, ensure_ascii=True, indent=2))
    if verification["errors"] or not verification["unique_app_review_ids"] or not verification["newest_first"]:
        raise RuntimeError("Verification failed")


def probe(args):
    root = Path(args.output)
    summary = []
    def single(source):
        key, url = source
        record = {"key": key, "url": url}
        try:
            text, path, meta = http_capture(url, None, root / "raw" / key, HEADER_PROFILES.get(args.profile))
            record.update(status=meta["status"], raw_file=path.as_posix(), bytes=meta["bytes"], final_url=meta["final_url"])
            try:
                decoded = json.loads(text)
                dump(root / (key + ".json"), decoded)
                if "results" in decoded:
                    record["apps"] = [{k: item.get(k) for k in ("trackId", "trackName", "sellerName", "bundleId", "trackViewUrl")} for item in decoded["results"]]
                if "feed" in decoded:
                    entries = decoded["feed"].get("entry", [])
                    entries = [entries] if isinstance(entries, dict) else entries
                    reviews = [entry for entry in entries if "im:rating" in entry]
                    record["review_count"] = len(reviews)
                    record["dates"] = [entry.get("updated", {}).get("label") for entry in reviews[:3]]
                    record["links"] = decoded["feed"].get("link", [])
            except json.JSONDecodeError:
                record["title"] = html.unescape(re.search(r"<title[^>]*>(.*?)</title>", text, re.S).group(1)) if "<title" in text else None
                record["apple_links"] = sorted(set(html.unescape(match) for match in re.findall(r'https?://[^\s"<>]*(?:apps\.apple\.com|itunes\.apple\.com)[^\s"<>]*', text)))[:12]
                record["app_ids_in_page"] = sorted(set(re.findall(r'(?:itunes\.apple\.com|apps\.apple\.com)[^\s"<>]{0,200}?id(\d+)', text)))
                record["xml_entry_count"] = text.count("<entry>")
                record["review_snippet_count"] = text.count("review")
        except Exception as error:
            record["error"] = f"{type(error).__name__}: {error}"
        return record
    sources = [(args.key or "custom", args.url)] if args.url else RSS_LIMIT if args.limit_probe else RSS_RECHECK if args.recheck else FEED_VARIANTS if args.variants else PROBES
    with ThreadPoolExecutor(max_workers=3) as pool:
        for record in pool.map(single, sources):
            summary.append(record)
            dump(root / "probe_summary.json", summary)
            print(json.dumps(record, ensure_ascii=True), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["probe", "crawl", "export"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--variants", action="store_true")
    parser.add_argument("--recheck", action="store_true")
    parser.add_argument("--limit-probe", action="store_true")
    parser.add_argument("--url")
    parser.add_argument("--key")
    parser.add_argument("--profile", choices=list(HEADER_PROFILES))
    parser.add_argument("--app", choices=list(APPS))
    parser.add_argument("--since", default="2026-04-19")
    parser.add_argument("--as-of", default="2026-10-19")
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--resume", action="store_true", help="Append repaired missing pages without altering earlier raw captures")
    args = parser.parse_args()
    if args.mode == "probe":
        probe(args)
    elif args.mode == "crawl":
        if not args.app:
            parser.error("crawl requires --app")
        crawl(args)
    else:
        export(args)


if __name__ == "__main__":
    main()
