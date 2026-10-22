"""Bounded public HK collectors. Called by run_feedback.py collect.

No credentials or browser sessions. Every response and request is preserved.
"""
from __future__ import annotations

import hashlib
import json
import ssl
import time
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from apple_parser import entries_from_feed, entry_label, parse_feed
from feedback_io import HK, bounds, dump, now, require
from source_utils import language, nested, parse_rpc


def capture(url, stem, body=None):
    stem.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded;charset=UTF-8"
    for attempt in range(1, 4):
        path = stem.with_name(stem.name + f"_attempt{attempt}")
        raw = path.with_suffix(".body")
        meta_path = path.with_suffix(".http.json")
        require(not raw.exists() and not meta_path.exists(), "Refusing to overwrite a capture")
        meta = {"requested_url": url, "method": "POST" if body else "GET", "attempt": attempt,
                "request_headers": headers, "request_body": body.decode() if body else None, "started_at_utc": now()}
        try:
            with urlopen(Request(url, data=body, headers=headers), timeout=35,
                         context=ssl.create_default_context()) as response:
                content = response.read()
                meta.update(status=response.status, final_url=response.url, response_headers=dict(response.headers.items()))
            raw.write_bytes(content)
            meta.update(bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
            dump(meta_path, meta, exclusive=True)
            text = content.decode("utf-8")
            require("com.google.play.gateway.proto.PlayGatewayError" not in text, "Google PlayGatewayError")
            return text, raw, meta
        except Exception as error:
            meta["error"] = f"{type(error).__name__}: {error}"
            if isinstance(error, HTTPError):
                content = error.read()
                raw.write_bytes(content)
                meta.update(status=error.code, sha256=hashlib.sha256(content).hexdigest(), bytes=len(content))
            dump(meta_path, meta)
            # Do not repeatedly retry auth, blocking, not-found, or rate-limit responses.
            if isinstance(error, HTTPError) and error.code in (401, 403, 404, 429):
                raise
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def base_row(config, app, platform, identifier, instant, rating, text, title, raw, index, meta, root):
    require(instant.tzinfo is not None, "Source timestamp has no UTC offset")
    source = "google_play" if platform == "Google Play" else "apple"
    appid = app["google_id" if source == "google_play" else "apple_id"]
    detected, status, method, probabilities = language((title + "\n" if title else "") + text)
    row = {"platform": platform, "bank": app["bank"], "app": app["name"], "app_key": app["key"],
           "app_id": appid, "review_id": identifier, "record_key": f"{source}:{appid}:{identifier}",
           "review_time_hk": instant.astimezone(HK).isoformat(), "review_time_utc": instant.astimezone(timezone.utc).isoformat(),
           "review_timestamp_seconds": instant.timestamp(), "rating": rating, "title": title, "text": text,
           "detected_language": detected, "language_status": status, "language_method": method,
           "language_probabilities": probabilities, "collected_at_utc": meta["started_at_utc"],
           "raw_response_workspace_path": raw.relative_to(root).as_posix(),
           "raw_item_index": index if source == "google_play" else None,
           "raw_entry_index": index if source == "apple" else None}
    return row


def collect_google(root, config, app, summary):
    from google_play_scraper.constants.request import Formats
    from google_play_scraper.constants.element import ElementSpecs
    folder = root / "data/raw/google_play" / app["key"]
    listing = "https://play.google.com/store/apps/details?" + urlencode({"id": app["google_id"], "hl": app["google_language"], "gl": "HK"})
    _, listing_raw, _ = capture(listing, folder / "listing")
    summary["listing_snapshot"] = listing_raw.relative_to(root).as_posix()
    token, seen_tokens, seen_ids, older = None, set(), set(), 0
    rows = []
    start, _ = bounds(config)
    for page in range(1, config["google_max_pages"] + 1):
        url = Formats.Reviews.build(lang=app["google_language"], country="hk")
        body = Formats.Reviews.build_body(app["google_id"], 2, 200, "null", "null", token)
        text, raw, meta = capture(url, folder / f"page_{page:04d}", body)
        items, next_token, decoded = parse_rpc(text)
        decoded_path = folder / f"page_{page:04d}.decoded.json"
        dump(decoded_path, decoded, exclusive=True)
        new = []
        for index, item in enumerate(items):
            values = {key: spec.extract_content(item) for key, spec in ElementSpecs.Review.items() if key not in {"at", "repliedAt"}}
            identifier = values.get("reviewId")
            require(isinstance(identifier, str) and identifier, "Google review ID absent")
            if identifier in seen_ids:
                summary["duplicates"] += 1
                continue
            instant = datetime.fromtimestamp(nested(item, [5, 0]), timezone.utc)
            row = base_row(config, app, "Google Play", identifier, instant, values.get("score"), values.get("content") or "", None, raw, index, meta, root)
            row.update(source="Google Play", source_url=listing + "&reviewId=" + identifier,
                request_country="HK", request_language=app["google_language"], user_display_name=values.get("userName"),
                thumbs_up=values.get("thumbsUpCount"), review_app_version=values.get("reviewCreatedVersion"),
                developer_reply=values.get("replyContent"), reply_timestamp_seconds=nested(item, [7, 2, 0]),
                raw_items_workspace_path=decoded_path.relative_to(root).as_posix())
            new.append(row)
            seen_ids.add(identifier)
        rows.extend(new)
        instants = [nested(item, [5, 0]) for item in items]
        older = older + 1 if instants and all(type(x) in (float, int) for x in instants) and max(instants) < start.timestamp() else 0
        summary["pages"].append({"page": page, "returned": len(items), "new_unique": len(new), "has_next_token": bool(next_token)})
        dump(folder / "rows_partial.json", rows)
        if not next_token:
            summary["stop_reason"] = "endpoint_exhausted_for_request_parameters"
            break
        if next_token in seen_tokens or not new:
            summary["stop_reason"] = "repeated_token_or_no_new_ids"
            break
        if older >= 2 and not config["all_history"]:
            summary["stop_reason"] = "two_pages_before_window"
            break
        seen_tokens.add(next_token)
        token = next_token
        time.sleep(config["pause_seconds"])
    else:
        summary["stop_reason"] = "max_pages_safety_limit"
    return rows


def collect_apple(root, config, app, summary):
    folder = root / "data/raw/apple" / app["key"]
    lookup = "https://itunes.apple.com/lookup?" + urlencode({"id": app["apple_id"], "country": "hk"})
    text, raw, _ = capture(lookup, folder / "listing")
    results = json.loads(text).get("results", [])
    require(any(str(item.get("trackId")) == app["apple_id"] for item in results), "Apple lookup identity mismatch")
    summary["listing_snapshot"] = raw.relative_to(root).as_posix()
    rows, seen, last_nonempty = [], set(), None
    for page in range(1, config["apple_max_pages"] + 1):
        base = f"https://itunes.apple.com/hk/rss/customerreviews/page={page}/id={app['apple_id']}/sortBy=mostRecent/"
        candidates = [base + "json?l=" + app["apple_language"], base + "json", base + "xml?l=" + app["apple_language"]]
        entries, decoded = [], None
        for variant, url in enumerate(candidates, 1):
            text, raw, meta = capture(url, folder / f"page_{page:02d}_variant{variant}")
            decoded = parse_feed(text)
            entries = entries_from_feed(decoded)
            if entries:
                break
            time.sleep(config["pause_seconds"])
        new = []
        for index, entry in entries:
            identifier = entry["id"]["label"]
            if identifier in seen:
                summary["duplicates"] += 1
                continue
            instant = datetime.fromisoformat(entry["updated"]["label"])
            row = base_row(config, app, "Apple App Store", identifier, instant, int(entry["im:rating"]["label"]),
                entry_label(entry, "content"), entry_label(entry, "title"), raw, index, meta, root)
            row.update(source="Apple App Store RSS", storefront="hk", source_updated_time=entry["updated"]["label"],
                source_url=f"https://apps.apple.com/hk/app/{app['apple_slug']}/id{app['apple_id']}?l={app['apple_language']}&see-all=reviews&platform=iphone",
                user_display_name=entry.get("author", {}).get("name", {}).get("label"),
                review_app_version=entry.get("im:version", {}).get("label"),
                vote_sum=int(entry.get("im:voteSum", {}).get("label", 0)), vote_count=int(entry.get("im:voteCount", {}).get("label", 0)),
                developer_reply=None, reply_availability="not_exposed_by_public_rss")
            seen.add(identifier)
            new.append(row)
        rows.extend(new)
        summary["pages"].append({"page": page, "returned": len(entries), "new_unique": len(new)})
        dump(folder / "rows_partial.json", rows)
        if not entries:
            summary.setdefault("unresolved_empty_pages", []).append(page)
            # Empty intermediate pages do not prove the end of the public feed.
        else:
            last_nonempty = page
            if not new:
                summary["stop_reason"] = "repeated_ids_no_new_records"
                break
        time.sleep(config["pause_seconds"])
    else:
        summary["stop_reason"] = "configured_feed_page_limit_not_all_time_completeness"
    # Boundary is observed, not assumed. Never repair or overwrite an old capture.
    if config["apple_max_pages"] == 10 and last_nonempty == 10:
        url = f"https://itunes.apple.com/hk/rss/customerreviews/page=11/id={app['apple_id']}/sortBy=mostRecent/json"
        text, _, _ = capture(url, folder / "boundary_page_11")
        summary["page_11_records_observed"] = len(entries_from_feed(parse_feed(text)))
    return rows


def collect(root, config):
    require(not (root / "data/raw").exists(), "Collection already started; use a new batch after inspecting failures")
    summaries, rows = [], []
    dump(root / "collection_summary.json", {"status": "running", "crawls": summaries})
    for app in config["apps"]:
        for platform, function in (("Google Play", collect_google), ("Apple App Store", collect_apple)):
            item = {"app_key": app["key"], "platform": platform, "pages": [], "duplicates": 0, "started_at_utc": now()}
            summaries.append(item)
            try:
                collected = function(root, config, app, item)
                rows.extend(collected)
                item.update(status="collected", records=len(collected), finished_at_utc=now())
            except Exception as error:
                item.update(status="failed", error=f"{type(error).__name__}: {error}")
                dump(root / "collection_summary.json", {"status": "failed", "crawls": summaries})
                raise
            dump(root / "collection_summary.json", {"status": "running", "crawls": summaries})
    dump(root / "source_records.json", rows, exclusive=True)
    dump(root / "collection_summary.json", {"status": "collected", "crawls": summaries,
        "limitations": "Apple public feed and Google request-specific sample; no exhaustive-history claim."})
