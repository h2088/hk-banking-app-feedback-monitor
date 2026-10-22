"""English manager delivery, Chinese/English comments, three banks and separate stores.
Run stages: import, prepare, build, verify, finalize. Read samples before build.
"""
import argparse
import collections
import csv
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0, str(ROOT / "engine"))
from feedback_io import bounds, csv_write, dump, fingerprints, load, now, sha, sorted_rows, validate_row, xlsx_write
from source_utils import parse_rpc, nested
from apple_parser import parse_feed, entries_from_feed, entry_label
from bilingual_rules import THEMES, ZH, classify, language_group, metrics, normalized, theme_metrics

STORES = ["Google Play", "Apple App Store"]
KEYS = ["sc_mobile", "hsbc_hk", "bochk"]
NAMES = dict(zip(KEYS, ["SC Mobile", "HSBC HK", "BOCHK"]))
SLUG = dict(zip(STORES, ["google_play", "apple_app_store"]))


def combined_metrics(rows, name, extra):
    result = metrics(rows, name, extra)
    # The supplementary English lexicon remains in row exports only.
    for key in ("text_negative_rule_count", "text_negative_rule_rate", "text_sentiment_evaluated_count"):
        result.pop(key, None)
    return result


def export(stem, rows, fields=None):
    path = ROOT / stem
    path.parent.mkdir(parents=True, exist_ok=True)
    dump(path.with_suffix(".json"), rows)
    csv_write(path.with_suffix(".csv"), rows, fields)


def import_input():
    v2 = PROJECT / "v2"
    assert not (ROOT / "data/input/v2_all_reviews.json").exists(), "Input already imported"
    manifest = load(v2 / "manifest.json")
    assert all(sha(v2 / name) == item["sha256"] for name,item in manifest["files"].items()), "V2 changed"
    source = load(v2 / "data/merged/master_all_reviews.json")
    evidence = {}
    for row in source:
        for field in ("raw_response_workspace_path", "raw_items_workspace_path"):
            if not row.get(field):
                continue
            original = row[field]
            path = (v2 / original).resolve()
            assert path.is_relative_to(v2) and path.is_file()
            digest = sha(path)
            target = ROOT / "data/raw/imported" / (digest + path.suffix)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copyfile(path, target)
            evidence[original] = dict(sha256=digest, copied_path=target.relative_to(ROOT).as_posix())
            row["v2_origin_" + field] = original
            row[field] = target.relative_to(ROOT).as_posix()
    dump(ROOT / "data/input/v2_all_reviews.json", source)
    dump(ROOT / "data/input/v2_english_baseline.json", load(v2 / "data/merged/master_english_six_months.json"))
    dump(ROOT / "data/input/import_manifest.json", dict(v2_source_sha256=sha(v2 / "data/merged/master_all_reviews.json"), evidence=evidence))
    protected = {"v2/"+name: item["sha256"] for name,item in manifest["files"].items()}
    protected["v2/manifest.json"] = sha(v2 / "manifest.json")
    protected.update(load(v2 / "data/input/v1_preservation.json"))
    dump(ROOT / "data/input/prior_preservation.json", protected)
    config = load(ROOT / "config.json")
    config.update(schema_version=3, language="english_and_chinese", chinese_google_request_languages=["zh-HK","zh-CN"],
                  analysis_population="english_and_chinese_combined", google_max_pages=100)
    config.pop("language_scopes", None)
    dump(ROOT / "config.json", config)
    print(json.dumps(dict(imported=len(source), protected_files=len(protected))))


def prepare():
    config = load(ROOT / "config.json")
    config.pop("language_scopes", None)
    config.update(analysis_population="english_and_chinese_combined", report_revision="combined_feedback_monthly_chart")
    dump(ROOT / "config.json", config)
    start, end = bounds(config)
    baseline = load(ROOT / "data/input/v2_all_reviews.json")
    observations = load(ROOT / "data/chinese_collection/source_observations.json")
    # Earliest captured V2 version wins, preserving all 418 English baseline records.
    # New IDs: first zh-HK observation, then zh-CN; all duplicate observations remain saved.
    index = {r["record_key"]:dict(r) for r in baseline}
    seen_in = collections.defaultdict(list)
    variants = []
    for row in baseline + observations:
        seen_in[row["record_key"]].append(dict(request_language=row.get("request_language"), collected_at_utc=row["collected_at_utc"], raw_response_workspace_path=row["raw_response_workspace_path"]))
        if row["record_key"] not in index:
            index[row["record_key"]] = dict(row)
        elif fingerprints(index[row["record_key"]]) != fingerprints(row):
            variants.append(dict(record_key=row["record_key"], chosen_fingerprint=fingerprints(index[row["record_key"]]), variant_fingerprint=fingerprints(row),
                chosen_text=index[row["record_key"]]["text"], variant_text=row["text"], variant_rating=row["rating"], variant_review_time_hk=row["review_time_hk"], variant_raw_path=row["raw_response_workspace_path"], reason="Capture/locale variant; retained in observations, earliest chosen snapshot not overwritten"))
    source = sorted_rows(list(index.values()))
    for row in source:
        row["source_observations"] = seen_in[row["record_key"]]
        row["analysis_language"], row["analysis_language_method"] = language_group(row)
        row["within_six_month_window"] = start.timestamp() <= row["review_timestamp_seconds"] < end.timestamp()
        if row["text"]:
            validate_row(row, config, ROOT)
        else:
            # Some older Google entries have a rating and an empty source body.
            # Preserve them as excluded evidence; validate every other field
            # through a temporary nonempty view without changing the stored row.
            assert row["text"] == "" and row["analysis_language"] == "excluded"
            validate_row(dict(row, text="[empty source body; excluded]"), config, ROOT)
    included = [r for r in source if r["within_six_month_window"] and r["analysis_language"] != "excluded"]
    labels = [dict(r, **classify(r)) for r in included]
    old = load(ROOT / "data/input/v2_english_baseline.json")
    old_fp = {r["record_key"]:fingerprints(r) for r in old}
    recovered = {r["record_key"]:fingerprints(r) for r in included if r["record_key"] in old_fp}
    assert old_fp == recovered and len(old_fp) == 418
    export("data/merged/master_all_reviews", source)
    export("data/merged/master_bilingual_six_months", included)
    export("data/analysis/comment_labels", labels)
    export("data/qa/capture_variants", variants, ["record_key","chosen_fingerprint","variant_fingerprint","chosen_text","variant_text","variant_rating","variant_review_time_hk","variant_raw_path","reason"])
    exclusions = [{k:r.get(k) for k in ("record_key","platform","app_key","review_time_hk","language_status","analysis_language","analysis_language_method")} | {"reason":"outside_date_window" if not r["within_six_month_window"] else "unsupported_or_uncertain_language"} for r in source if r not in included]
    export("data/qa/exclusions", exclusions)
    groups, themes, monthly, deltas, samples, coverage = [], [], [], [], [], []
    for store in STORES:
        for key in KEYS:
            members = [r for r in labels if r["platform"] == store and r["app_key"] == key]
            extra = dict(platform=store, app_key=key, app=NAMES[key])
            groups.append(combined_metrics(members, " | ".join([store,NAMES[key]]),extra))
            themes.extend([dict(t,**extra) for t in theme_metrics(members, " | ".join([store,NAMES[key]]))])
            for month in range(4,11):
                bucket = f"2026-{month:02}"
                subset = [r for r in members if r["review_time_hk"].startswith(bucket)]
                monthly.append(combined_metrics(subset, " | ".join([store,NAMES[key],bucket]), extra | dict(month_hk=bucket,partial_calendar_month=month in {4,10})))
        p = next(g for g in groups if g["platform"]==store and g["app_key"]=="sc_mobile")
        for key in KEYS[1:]:
            b = next(g for g in groups if g["platform"]==store and g["app_key"]==key)
            valid = p["review_count"] and b["review_count"]
            deltas.append(dict(platform=store,primary="SC Mobile",benchmark=NAMES[key],primary_n=p["review_count"],benchmark_n=b["review_count"],
                mean_rating_difference_sc_minus_benchmark=round(p["mean_rating"]-b["mean_rating"],4) if valid else None,
                low_star_rate_difference_percentage_points=round(100*(p["negative_rate_rating_1_2"]-b["negative_rate_rating_1_2"]),4) if valid else None))
    monthly_totals=[]
    for store in STORES:
        for month in range(4,11):
            bucket=f"2026-{month:02}"
            record=dict(platform=store,month_hk=bucket,review_count=0,partial_calendar_month=month in {4,10})
            for key in KEYS:
                m=next(m for m in monthly if m["platform"]==store and m["app_key"]==key and m["month_hk"]==bucket)
                record["review_count"]+=m["review_count"]
                record[key+"_review_count"]=m["review_count"]
                record[key+"_low_star_count"]=m["negative_count_rating_1_2"]
                record[key+"_low_star_rate"]=m["negative_rate_rating_1_2"]
            monthly_totals.append(record)
    for store in STORES:
        members = [r for r in labels if r["platform"]==store]
        export("data/stores/"+SLUG[store]+"_bilingual_reviews",members,list(labels[0]))
        for key in KEYS:
            subset = [r for r in members if r["app_key"]==key]
            fetched = [r for r in source if r["platform"]==store and r["app_key"]==key]
            window = [r for r in fetched if r["within_six_month_window"]]
            coverage.append(dict(platform=store,app_key=key,app=NAMES[key],fetched_unique=len(fetched),window_all_languages=len(window),included_bilingual=len(subset),
                english_count=sum(r["analysis_language"]=="english" for r in subset),chinese_count=sum(r["analysis_language"]=="chinese" for r in subset),mixed_count=sum(r["analysis_language"]=="mixed" for r in subset),
                latest_included_hk=max((r["review_time_hk"] for r in subset),default=None),earliest_included_hk=min((r["review_time_hk"] for r in subset),default=None),
                first_capture_utc=min((r["collected_at_utc"] for r in fetched),default=None),last_capture_utc=max((r["collected_at_utc"] for r in fetched),default=None)))
            export("data/stores/"+SLUG[store]+"_"+key,subset,list(labels[0]))
            # Every bank/store receives one recent observation per actual language,
            # plus extra Chinese examples to cover multiple rating levels.
            for lang in ("english","chinese","mixed"):
                for rating in (1,3,5):
                    selected = next((r for r in subset if r["analysis_language"]==lang and r["rating"]==rating),None)
                    if selected:
                        samples.append({k:selected.get(k) for k in ("record_key","platform","app_key","analysis_language","rating","review_time_hk","title","text","rating_sentiment","themes","theme_labels")} | dict(fingerprint=fingerprints(selected)))
    for name,values in (("store_benchmarks",groups),("themes_by_store_bank",themes),("monthly_by_store_bank",monthly),("benchmark_deltas",deltas),("monthly_feedback_monitoring",monthly_totals)):
        export("data/analysis/"+name,values)
    export("data/qa/coverage",coverage)
    dump(ROOT / "data/analysis/validation_sample.json",samples)
    repeated = collections.defaultdict(list)
    for row in included:
        repeated[normalized(row["text"])].append(row["record_key"])
    repeat_groups = [dict(normalized_text=k,record_keys=v) for k,v in repeated.items() if len(v)>1]
    dump(ROOT / "data/qa/repeated_text_groups.json",repeat_groups)
    summary = dict(prepared_at_utc=now(),window_start_inclusive_hk=start.isoformat(),window_end_exclusive_hk=end.isoformat(),
        unique_fetched_records=len(source),new_locale_observations=len(observations),duplicate_observations=len(baseline)+len(observations)-len(source),capture_variant_count=len(variants),
        new_unique_ids=len(source)-len(baseline),window_all_languages=sum(r["within_six_month_window"] for r in source),included_records=len(included),
        language_counts=dict(collections.Counter(r["analysis_language"] for r in included)),v2_english_records_preserved=418,
        sample_count=len(samples),short_text_count=sum(r["short_text_for_theme_review"] for r in labels),unclassified_count=sum(not r["themes"] for r in labels),
        repeated_text_group_count=len(repeat_groups),coverage=coverage)
    dump(ROOT / "data/qa/qa_summary.json",summary)
    print(json.dumps(summary,ensure_ascii=True),flush=True)


def review_status():
    sample = load(ROOT / "data/analysis/validation_sample.json")
    notes = load(ROOT / "manual_review.json")
    assert notes["status"]=="reviewed" and "agent" in notes["reviewer"].lower()
    assert notes["sample_sha256"]==sha(ROOT / "data/analysis/validation_sample.json")
    index = {r["record_key"]:r for r in notes["reviews"]}
    assert set(index)=={r["record_key"] for r in sample}
    for row in sample:
        note=index[row["record_key"]]
        assert note["fingerprint"]==row["fingerprint"] and len(note["notes"])>25
        assert note["theme_assessment"] in {"plausible","limitation_noted","insufficient_text"}
    return notes


def build():
    review_status()
    rows=load(ROOT / "data/analysis/comment_labels.json")
    data=dict(config=load(ROOT/"config.json"),summary=load(ROOT/"data/qa/qa_summary.json"),theme_names={k:v[0] for k,v in THEMES.items()})
    for key,name in (("groups","store_benchmarks"),("themes","themes_by_store_bank"),("monthly","monthly_by_store_bank"),("deltas","benchmark_deltas"),("monthly_totals","monthly_feedback_monitoring")):
        data[key]=load(ROOT/("data/analysis/"+name+".json"))
    data["coverage"]=load(ROOT/"data/qa/coverage.json")
    fields=["record_key","platform","app_key","app","rating","title","text","review_time_hk","review_timestamp_seconds","source_url","rating_sentiment","themes","theme_labels"]
    data["rows"]=[{k:r.get(k) for k in fields} for r in rows]
    embedded=json.dumps(data,ensure_ascii=False,allow_nan=False).replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026").replace("\u2028","\\u2028").replace("\u2029","\\u2029")
    template=(ROOT/"assets/report.html").read_text(encoding="utf-8")
    (ROOT/"report_customer_feedback_v3.html").write_text(template.replace("__PAYLOAD__",embedded),encoding="utf-8")
    workbook=ROOT/"data/reviews_v3.xlsx"
    if workbook.exists():
        workbook.unlink()
    xlsx_write(workbook,{"Google Play reviews":[r for r in rows if r["platform"]==STORES[0]],"Apple App Store reviews":[r for r in rows if r["platform"]==STORES[1]],
        "Bank store metrics":data["groups"],"Benchmark deltas":data["deltas"],"Topics by store":data["themes"],"Monthly by bank and store":data["monthly"],"Monthly feedback monitoring":data["monthly_totals"],
        "Coverage":[{k:v for k,v in c.items() if k not in {"english_count","chinese_count","mixed_count"}} for c in data["coverage"]]})
    from docs import write_docs
    write_docs(ROOT,data)
    print(json.dumps(dict(report_sha256=sha(ROOT/"report_customer_feedback_v3.html"),records=len(rows))))


def verify():
    config=load(ROOT/"config.json")
    rows=load(ROOT/"data/analysis/comment_labels.json")
    start,end=bounds(config)
    checks=[]
    def check(name,value,detail=None):
        checks.append(dict(name=name,passed=bool(value),detail=detail))
        assert value,name
    check("Unique IDs and stable newest-first ordering",len({r["record_key"] for r in rows})==len(rows) and rows==sorted_rows(rows))
    for row in rows:
        validate_row(row,config,ROOT)
        assert start.timestamp()<=row["review_timestamp_seconds"]<end.timestamp() and row["analysis_language"] in {"english","chinese","mixed"}
    check("Date, ID, source paths and supported languages",True,len(rows))
    baseline=load(ROOT/"data/input/v2_english_baseline.json")
    fp={r["record_key"]:fingerprints(r) for r in baseline}
    check("All 418 V2 English reviews preserved exactly",fp=={r["record_key"]:fingerprints(r) for r in rows if r["record_key"] in fp})
    cache={}
    for row in rows:
        path=ROOT/row["raw_response_workspace_path"]
        if str(path) not in cache:
            cache[str(path)]=parse_rpc(path.read_text(encoding="utf-8"))[0] if row["platform"]==STORES[0] else dict(entries_from_feed(parse_feed(path.read_text(encoding="utf-8"))))
        items=cache[str(path)]
        if row["platform"]==STORES[0]:
            item=items[row["raw_item_index"]]
            assert (nested(item,[0]),nested(item,[4]),nested(item,[2]),nested(item,[5,0]))==(row["review_id"],row["text"],row["rating"],row["review_timestamp_seconds"])
        else:
            item=items[row["raw_entry_index"]]
            assert (item["id"]["label"],entry_label(item,"title"),entry_label(item,"content"),int(item["im:rating"]["label"]),datetime.fromisoformat(item["updated"]["label"]).timestamp())==(row["review_id"],row["title"],row["text"],row["rating"],row["review_timestamp_seconds"])
    check("Every included original title/body/rating/time matches saved raw HTTP evidence",True,len(rows))
    groups=load(ROOT/"data/analysis/store_benchmarks.json")
    for g in groups:
        members=[r for r in rows if r["platform"]==g["platform"] and r["app_key"]==g["app_key"]]
        n=len(members)
        assert n==g["review_count"] and g["negative_count_rating_1_2"]==sum(r["rating"]<=2 for r in members)
        assert g["negative_rate_rating_1_2"]==(round(sum(r["rating"]<=2 for r in members)/n,6) if n else None)
        assert g["mean_rating"]==(round(sum(r["rating"] for r in members)/n,4) if n else None)
    check("Six bank/store metric groups combine all included English and Chinese comments",len(groups)==6 and sum(g["review_count"] for g in groups)==len(rows) and all("language_scope" not in g for g in groups))
    themes=load(ROOT/"data/analysis/themes_by_store_bank.json")
    for t in themes:
        members=[r for r in rows if r["platform"]==t["platform"] and r["app_key"]==t["app_key"]]
        hits=[r for r in members if t["theme"] in r["themes"]]
        assert t["review_count"]==len(members) and t["theme_mentions"]==len(hits) and t["theme_negative_count"]==sum(r["rating"]<=2 for r in hits)
        assert t["theme_mention_rate"]==(round(len(hits)/len(members),6) if members else None)
    check("66 theme rows use combined bank/store denominators",len(themes)==66 and all("language_scope" not in t for t in themes))
    months=load(ROOT/"data/analysis/monthly_by_store_bank.json")
    for m in months:
        members=[r for r in rows if r["platform"]==m["platform"] and r["app_key"]==m["app_key"] and r["review_time_hk"].startswith(m["month_hk"])]
        assert m["review_count"]==len(members) and m["negative_count_rating_1_2"]==sum(r["rating"]<=2 for r in members)
        assert m["negative_rate_rating_1_2"]==(round(sum(r["rating"]<=2 for r in members)/len(members),6) if members else None)
    check("42 bank/store/month groups use combined comments and retain partial-month markers",len(months)==42 and all("language_scope" not in m and m["partial_calendar_month"]==(m["month_hk"] in {"2026-04","2026-10"}) for m in months))
    totals=load(ROOT/"data/analysis/monthly_feedback_monitoring.json")
    for m in totals:
        members=[r for r in rows if r["platform"]==m["platform"] and r["review_time_hk"].startswith(m["month_hk"])]
        assert m["review_count"]==len(members)
        for key in KEYS:
            part=[r for r in members if r["app_key"]==key]
            low=sum(r["rating"]<=2 for r in part)
            assert m[key+"_review_count"]==len(part) and m[key+"_low_star_count"]==low
            assert m[key+"_low_star_rate"]==(round(low/len(part),6) if part else None)
    check("14 monthly chart rows independently match volume, three-bank counts and low-star shares",len(totals)==14 and sum(m["review_count"] for m in totals)==len(rows))
    deltas=load(ROOT/"data/analysis/benchmark_deltas.json")
    for d in deltas:
        p=next(g for g in groups if g["platform"]==d["platform"] and g["app_key"]=="sc_mobile")
        b=next(g for g in groups if g["platform"]==d["platform"] and g["app"]==d["benchmark"])
        expected=round(100*(p["negative_rate_rating_1_2"]-b["negative_rate_rating_1_2"]),4) if p["review_count"] and b["review_count"] else None
        assert d["low_star_rate_difference_percentage_points"]==expected
    check("Four combined within-store benchmark differences recomputed",len(deltas)==4 and all("language_scope" not in d for d in deltas))
    with (ROOT/"data/merged/master_bilingual_six_months.csv").open(encoding="utf-8-sig",newline="") as f:
        values=list(csv.DictReader(f))
    check("CSV exact Unicode source text and ordering",[r["record_key"] for r in values]==[r["record_key"] for r in rows] and all(c["text"]==r["text"] and c["title"]==(r.get("title") or "") for c,r in zip(values,rows)))
    with ZipFile(ROOT/"data/reviews_v3.xlsx") as z:
        check("Typed Excel with separate store sheets and no executable formulas","Google Play reviews" in z.read("xl/workbook.xml").decode() and "Apple App Store reviews" in z.read("xl/workbook.xml").decode() and all("<f>" not in z.read(n).decode() for n in z.namelist() if n.startswith("xl/worksheets/")))
    review_status()
    check("Unchanged source-bound reading sample retains actual agent judgments",True)
    preserved=load(ROOT/"data/input/prior_preservation.json")
    check("V1 and V2 remain unchanged",all(sha(PROJECT/p)==h for p,h in preserved.items()),len(preserved))
    report=(ROOT/"report_customer_feedback_v3.html").read_text(encoding="utf-8")
    check("English interface, unified population, restored monthly chart and no remote/name/reply payload",'<html lang="en">' in report and 'id="languageFilter"' not in report and 'id="monthlyChart"' in report and 'src="http' not in report and '"developer_reply":' not in report and '"user_display_name":' not in report)
    unchanged=load(ROOT/"data/input/combined_revision_preservation.json")
    check("Revision preserves original input, raw evidence, comments, labels and reading sample",all(sha(ROOT/p)==h for p,h in unchanged.items()),len(unchanged))
    dump(ROOT/"validation/static_results.json",dict(passed=True,checked_at_utc=now(),report_sha256=sha(ROOT/"report_customer_feedback_v3.html"),checks=checks))
    print(json.dumps(dict(passed=True,checks=len(checks),raw_verified_reviews=len(rows))))


def finalize():
    review_status()
    digest=sha(ROOT/"report_customer_feedback_v3.html")
    static=load(ROOT/"validation/static_results.json")
    browser=load(ROOT/"validation/browser_results.json")
    visual=load(ROOT/"validation/visual_inspection.json")
    assert static["passed"] and browser["passed"] and static["report_sha256"]==browser["report_sha256"]==visual["report_sha256"]==digest
    assert visual["status"]=="reviewed" and "agent" in visual["reviewer"].lower()
    assert visual["screenshots"]==browser["screenshot_hashes"] and len(visual["screenshots"])>=5
    assert all(sha(ROOT/p)==v for p,v in visual["screenshots"].items())
    assert all(sha(PROJECT/p)==h for p,h in load(ROOT/"data/input/prior_preservation.json").items())
    unchanged=load(ROOT/"data/input/combined_revision_preservation.json")
    assert all(sha(ROOT/p)==h for p,h in unchanged.items())
    (ROOT/"checkpoint_F_final_review.md").write_text(f"# Checkpoint F - final review\n\nV3 corrected: one combined English/Chinese comment population, three banks and separate stores. The V1 horizontal monthly feedback chart is restored, with BOCHK added and store-specific totals. No report or workbook metrics are split by review language.\n\nReport SHA-256: `{digest}`.\n\nPassed {len(static['checks'])} static checks and {browser['assertions']} real-browser assertions. All 1,682 included source comments were verified against raw evidence. Source input, comment labels and the previously read sample remain hash-identical; their signed agent judgments still apply. New chart and screenshots were inspected for this HTML hash. This is not independent human accuracy evaluation. V1 and V2 remain unchanged.\n\nThe previous V3 delivery is recoverable from the archive named in revision.json. See methodology.md for limits and manifest.json for current delivery hashes.\n",encoding="utf-8")
    files={p.relative_to(ROOT).as_posix():dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(ROOT.rglob("*")) if p.is_file() and p.name!="manifest.json" and "__pycache__" not in p.parts}
    dump(ROOT/"manifest.json",dict(schema_version=3,finalized_at_utc=now(),report_sha256=digest,files=files))
    print(json.dumps(dict(status="complete",files=len(files),report_sha256=digest)))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("stage",choices=["import","prepare","build","verify","finalize"])
    args=parser.parse_args()
    import_input() if args.stage=="import" else globals()[args.stage]()
