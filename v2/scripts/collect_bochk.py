"""Collect the verified BOCHK retail app; preserve every public response."""
import concurrent.futures
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
from feedback_io import dump, load, now
from collect_reviews import capture, collect_google, collect_apple


def main():
    config = load(ROOT / "config.json")
    app = next(a for a in config["apps"] if a["key"] == "bochk")
    target = ROOT / "data/bochk_collection"
    if target.exists():
        raise ValueError("Collection already exists: inspect it and choose a new batch before recollecting")
    target.mkdir(parents=True)
    # Capture public identity evidence in addition to the per-store listings.
    capture("https://itunes.apple.com/search?term=BOCHK&country=hk&entity=software&limit=12", target / "identity/apple_search")
    capture("https://play.google.com/store/search?q=BOCHK&c=apps&hl=en&gl=HK", target / "identity/google_search")
    summaries = []
    def run(platform, fn):
        summary = dict(app_key="bochk", platform=platform, pages=[], duplicates=0, started_at_utc=now())
        try:
            rows = fn(target, config, app, summary)
            summary.update(status="collected", records=len(rows))
        except Exception as error:
            partial = target / "data/raw" / ("google_play" if platform == "Google Play" else "apple") / "bochk/rows_partial.json"
            rows = load(partial) if partial.exists() else []
            summary.update(status="partial_failure", records=len(rows), error=f"{type(error).__name__}: {error}")
        # Paths are relative to V2, so imported and freshly collected evidence share one root.
        for row in rows:
            for key in ("raw_response_workspace_path", "raw_items_workspace_path"):
                if row.get(key):
                    row[key] = "data/bochk_collection/" + row[key]
        summary["finished_at_utc"] = now()
        dump(target / ("google_records.json" if platform == "Google Play" else "apple_records.json"), rows)
        dump(target / ("google_summary.json" if platform == "Google Play" else "apple_summary.json"), summary)
        print(json.dumps(summary, ensure_ascii=True), flush=True)
        return summary, rows
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, p, f) for p, f in (("Google Play", collect_google), ("Apple App Store", collect_apple))]
        results = [f.result() for f in futures]
    dump(target / "source_records.json", [r for s, rows in results for r in rows])
    dump(target / "collection_summary.json", {"captured_at_utc": now(), "crawls": [s for s, rows in results], "historical_window": [config["since"], config["as_of"]], "limitations": "New BOCHK capture filtered to historical dates; not a reconstruction of the October 19 feed. Public feeds are bounded samples."})


if __name__ == "__main__":
    main()
