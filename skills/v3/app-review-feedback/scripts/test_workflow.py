"""Offline behavioral regression tests. Fixtures never enter customer deliveries."""
import contextlib
import copy
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import run_feedback as w
import collect_reviews as collector
from bilingual_rules import classify, language_group
from build_report import build
from feedback_io import HK, SKILL, config_for, dump, fingerprints, load, sha, six_months_before, validate_row
from verify_report import verify


def entry(identifier, day, rating, body, title="Synthetic fixture"):
    return {"id":{"label":str(identifier)}, "updated":{"label":day+"T12:00:00+08:00"},
        "title":{"label":title}, "content":{"label":body}, "im:rating":{"label":str(rating)}}


def row(config, app, value, root, raw="fixture.json"):
    instant=datetime.fromisoformat(value["updated"]["label"])
    return dict(platform="Apple App Store", app=app["name"], app_key=app["key"], bank=app["bank"],
        app_id=app["apple_id"], review_id=value["id"]["label"], record_key="apple:"+app["apple_id"]+":"+value["id"]["label"],
        title=value["title"]["label"], text=value["content"]["label"], rating=int(value["im:rating"]["label"]),
        review_time_hk=instant.isoformat(), review_time_utc=instant.astimezone(timezone.utc).isoformat(),
        review_timestamp_seconds=instant.timestamp(), source_url="https://apps.apple.com/hk/app/test/id"+app["apple_id"],
        language_status="english" if "中文" not in value["content"]["label"] else "non_english",
        collected_at_utc="2026-10-22T00:00:00+00:00", raw_response_workspace_path=raw, raw_entry_index=None)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="hk_feedback_schema2_test_")
        self.root=Path(self.temp.name)
        self.quiet=contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None,None,None)
        self.temp.cleanup()

    def init(self, path=None):
        path=path or self.root/"batch"
        apps=copy.deepcopy(load(SKILL/"assets/apps.json")[:2])
        for i,a in enumerate(apps):
            a.update(key="renamed_"+str(i),name="Fixture "+str(i),bank="SYNTHETIC ONLY",
                google_id="example.test"+str(i),apple_id=str(9000000000+i))
        dump(self.root/"apps.json",apps)
        w.initialize(SimpleNamespace(root=path,apps=self.root/"apps.json",since="2026-09-01",as_of="2026-09-30"))
        return path,config_for(path)

    def fixture(self):
        root,c=self.init()
        values=[entry(1,"2026-09-01",5,'=TEST </script><img src=x onerror="window.__attack=1"> transfer'),
            entry(2,"2026-09-30",4,"中文 轉帳方便"),entry(3,"2026-09-10",1,"中文 登入閃退"),
            entry(4,"2026-09-20",2,"Cannot login crash"),entry(5,"2026-08-31",1,"Outside before"),
            entry(6,"2026-10-01",1,"Outside after"),entry(7,"2026-09-05",1,"日本語かな"),
            entry(8,"2026-09-07",1,"")]
        dump(root/"fixture.json",{"feed":{"entry":values}})
        rows=[]
        for i,e in enumerate(values):
            r=row(c,c["apps"][0 if i in (0,1,4,5,6,7) else 1],e,root)
            r["raw_entry_index"]=i
            rows.append(r)
        # Same source ID with an alternate body is retained as a capture variant.
        rows.append(dict(rows[0],text="Alternate capture, must not replace first"))
        dump(root/"source_records.json",rows)
        dump(root/"collection_summary.json",dict(status="imported",raw_evidence_sha256={"fixture.json":sha(root/"fixture.json")},limitations="SYNTHETIC ONLY"))
        w.prepare(root,c);w.qa(root,c);w.analyze(root,c)
        return root,c

    def test_combined_pipeline_and_evidence_guards(self):
        root,c=self.fixture()
        selected=load(root/"data/merged/master_bilingual_six_months.json")
        self.assertEqual([r["review_id"] for r in selected],["2","4","3","1"])
        self.assertEqual(len(load(root/"data/merged/capture_variants.json")),1)
        self.assertEqual(len(load(root/"data/merged/exclusions.json")),4)
        self.assertEqual(load(root/"data/qa/summary.json")["included_records"],4)
        self.assertEqual(w.month_buckets(c),[("2026-09",False)])
        groups=load(root/"data/analysis/store_benchmarks.json")
        self.assertEqual([g["review_count"] for g in groups],[0,0,2,2])
        self.assertEqual([g["mean_rating"] for g in groups],[None,None,4.5,1.5])
        self.assertEqual(load(root/"data/analysis/benchmark_deltas.json")[-1]["low_star_rate_difference_percentage_points"],-100)
        with self.assertRaisesRegex(ValueError,"pending"):w.validate_review(root)
        # Explicit synthetic test annotations; never applied to real reviews.
        review=load(root/"manual_review.json")
        review.update(status="reviewed",reviewer="SYNTHETIC TEST ONLY",reviewed_at="2026-10-22")
        for j in review["judgements"]:
            j.update(rating_assessment="plausible",theme_assessment="limitation_noted",notes="SYNTHETIC fixture annotation only, not an actual customer reading.")
        dump(root/"manual_review.json",review)
        build(root,c)
        self.assertTrue(verify(root,c)["passed"])
        before=sha(root/"validation/static_results.json")
        # Test-only freeze sentinel; not a fabricated customer delivery or visual approval.
        dump(root/"manifest.json",dict(files={"validation/static_results.json":dict(sha256=before)}))
        self.assertTrue(verify(root,c)["passed"])
        self.assertEqual(sha(root/"validation/static_results.json"),before)
        (root/"manifest.json").unlink()
        document=(root/"report_customer_feedback.html").read_text(encoding="utf-8")
        self.assertIn("2026-09-01",document)
        self.assertNotIn('<img src=x onerror="window.__attack=1">',document)
        self.assertNotIn('id="languageFilter"',document)
        with ZipFile(root/"data/reviews_master.xlsx") as z:
            ns={"s":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            sheet=ET.fromstring(z.read("xl/worksheets/sheet2.xml"))
            cells=[x for x in sheet.findall(".//s:c",ns) if (x.findtext("s:is/s:t",namespaces=ns) or "").startswith("=TEST")]
            self.assertEqual(len(cells),1);self.assertEqual(cells[0].attrib["t"],"inlineStr")
        original=(root/"fixture.json").read_bytes()
        (root/"fixture.json").write_bytes(original+b"TAMPER")
        with self.assertRaisesRegex(ValueError,"Imported raw hashes"):verify(root,c)
        (root/"fixture.json").write_bytes(original)
        updated=load(root/"config.json");updated["as_of"]="2026-10-01";dump(root/"config.json",updated)
        with self.assertRaisesRegex(ValueError,"Configuration changed"):w.guard(root)
        self.assertFalse((root/"manifest.json").exists())

    def test_language_topics_and_no_global_phrase_whitelist(self):
        r={"title":None,"text":"中文 login password 之後轉帳一直loading閃退","language_status":"non_english"}
        group,method=language_group(r);self.assertIn(group,{"chinese","mixed"})
        labels=classify(dict(r,rating=1,analysis_language=group))
        self.assertTrue({"login_authentication_access","app_stability_performance","transfers_payments_cards"}<=set(labels["themes"]))
        self.assertEqual(labels["rating_sentiment"],"negative")
        self.assertIsNone(labels["text_negative_hits"])
        self.assertEqual(language_group(dict(r,text="日本語かな"))[0],"excluded")
        self.assertEqual(language_group(dict(r,text="",title="中文好用"))[0],"excluded")
        self.assertEqual(language_group(dict(r,text="excellent",language_status="uncertain"))[0],"excluded")
        self.assertEqual(language_group(dict(r,text="excellent",language_override_applied=True,analysis_language="english",analysis_language_method="Exact actual reading"))[0],"english")

    def test_imported_decisions_and_exact_overrides(self):
        evidence=self.root/"evidence";evidence.mkdir()
        root,c=self.init()
        e=entry(1,"2026-09-15",5,"excellent")
        dump(evidence/"fixture.json",{"feed":{"entry":[e]}})
        r=row(c,c["apps"][0],e,root)
        r.update(raw_entry_index=0,language_status="uncertain",analysis_language="english",analysis_language_method="Previously actually read exact text")
        dump(self.root/"input.json",[r])
        w.import_snapshot(root,c,SimpleNamespace(input=self.root/"input.json",evidence_root=evidence,coverage_note="SYNTHETIC"))
        imported=load(root/"source_records.json")[0]
        self.assertEqual(imported["imported_language_decision"]["fingerprint"],fingerprints(r))
        w.prepare(root,c)
        self.assertEqual(load(root/"data/merged/master_bilingual_six_months.json")[0]["analysis_language"],"english")
        # A separate batch with an incorrect exact override must fail.
        other,oc=self.init(self.root/"other")
        dump(other/"fixture.json",{"feed":{"entry":[e]}})
        r.pop("analysis_language");r.pop("analysis_language_method")
        dump(other/"source_records.json",[r])
        oc["language_overrides"]=[dict(record_key=r["record_key"],expected_text="DIFFERENT",expected_title=r["title"],language="english",reason="Fixture",reviewer="TEST",reviewed_at="2026-10-22")]
        dump(other/"config.json",oc)
        with self.assertRaisesRegex(ValueError,"Override original differs"):w.prepare(other,oc)

    def test_boundaries_and_invalid_source(self):
        root,c=self.init()
        self.assertEqual(w.month_buckets(dict(c,since="2026-08-19",as_of="2026-10-19")),[("2026-08",True),("2026-09",False),("2026-10",True)])
        self.assertEqual(str(six_months_before(datetime.fromisoformat("2024-08-31").date())),"2024-02-29")
        e=entry(1,"2026-09-01",5,"good");dump(root/"fixture.json",{"feed":{"entry":[e]}})
        r=row(c,c["apps"][0],e,root)
        validate_row(r,c,root)
        for change,message in [(dict(app_id="WRONG"),"App ID"),(dict(raw_response_workspace_path="../escape"),"Path leaves"),(dict(review_time_hk="2026-09-01T00:00:00+08:00"),"HK time")]:
            with self.assertRaisesRegex(ValueError,message):validate_row(dict(r,**change),c,root)

    def test_collector_locale_jobs_and_failure_status(self):
        root,c=self.init()
        calls=[]
        def google(r,c,a,s):calls.append((a["key"],a["google_language"]));return []
        def apple(r,c,a,s):return []
        with patch.object(collector,"collect_google",google),patch.object(collector,"collect_apple",apple):
            collector.collect(root,c)
        self.assertEqual(calls,[(a["key"],lang) for a in c["apps"] for lang in ["en","zh-HK","zh-CN"]])
        self.assertEqual(len(load(root/"collection_summary.json")["crawls"]),8)
        other,oc=self.init(self.root/"failed")
        with patch.object(collector,"collect_google",side_effect=RuntimeError("MOCK failure")):
            with self.assertRaisesRegex(RuntimeError,"MOCK failure"):collector.collect(other,oc)
        self.assertEqual(load(other/"collection_summary.json")["status"],"failed")
        self.assertFalse((other/"source_records.json").exists())

    def test_apple_page_11_http400_boundary(self):
        root,c=self.init();app=c["apps"][0]
        def capture(url,stem,body=None):
            if "page=11/" in url:raise HTTPError(url,400,"MOCK feed boundary",None,io.BytesIO(b"boundary"))
            content={"results":[{"trackId":int(app["apple_id"])}]} if "/lookup?" in url else {"feed":{"entry":[entry(url.split("page=")[1].split("/")[0],"2026-09-10",1,"Cannot login")]}}
            path=stem.with_suffix(".body");dump(path,content)
            return json.dumps(content),path,{"started_at_utc":"2026-10-22T00:00:00+00:00"}
        summary={"pages":[],"duplicates":0}
        with patch.object(collector,"capture",capture),patch.object(collector.time,"sleep"):
            rows=collector.collect_apple(root,c,app,summary)
        self.assertEqual(len(rows),10);self.assertEqual(summary["page_11_boundary_status"],400)
        self.assertEqual(summary["stop_reason"],"configured_feed_page_limit_not_all_time_completeness")


if __name__=="__main__":
    unittest.main(verbosity=2)
