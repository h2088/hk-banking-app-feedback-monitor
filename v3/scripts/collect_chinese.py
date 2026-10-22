"""New, bounded Chinese Google Play requests; existing Apple feeds retain all languages."""
import concurrent.futures
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
from feedback_io import dump, load, now
from collect_reviews import collect_google


def main():
    config = load(ROOT / "config.json")
    target = ROOT / "data/chinese_collection"
    if target.exists():
        raise ValueError("Use a new capture batch; never overwrite saved responses")
    target.mkdir(parents=True)
    jobs = [(app, lang) for lang in ("zh-HK", "zh-CN") for app in config["apps"]]
    def run(original, language):
        app = dict(original, google_language=language)
        folder = target / language / app["key"]
        summary = dict(app_key=app["key"], platform="Google Play", request_language=language, pages=[], duplicates=0, started_at_utc=now())
        try:
            rows = collect_google(folder, config, app, summary)
            summary.update(status="collected", records=len(rows))
        except Exception as error:
            partial = folder / "data/raw/google_play" / app["key"] / "rows_partial.json"
            rows = load(partial) if partial.exists() else []
            summary.update(status="partial_failure", records=len(rows), error=f"{type(error).__name__}: {error}")
        for row in rows:
            for field in ("raw_response_workspace_path", "raw_items_workspace_path"):
                if row.get(field):
                    row[field] = folder.relative_to(ROOT).as_posix() + "/" + row[field]
            row["snapshot_mode"] = "V3 Chinese-locale Google capture on October 22"
        summary["finished_at_utc"] = now()
        dump(folder / "source_records.json", rows)
        dump(folder / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=True), flush=True)
        return summary, rows
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, app, lang) for app, lang in jobs]
        results = [f.result() for f in futures]
    dump(target / "source_observations.json", [row for summary, rows in results for row in rows])
    dump(target / "collection_summary.json", dict(captured_at_utc=now(), crawls=[s for s,rows in results],
        limitations="Two Chinese request locales in HK; responses overlap and are deduplicated by review ID. Request language does not guarantee comment language, completeness or author location. Apple all-language RSS snapshots are reused, not recollected."))


if __name__ == "__main__":
    main()
