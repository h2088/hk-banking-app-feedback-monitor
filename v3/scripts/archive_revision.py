"""Preserve the existing V3 before the requested combined-output correction."""
import hashlib
import json
import sys
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"engine"))
from feedback_io import dump,load,sha,now

def main():
    manifest=load(ROOT/"manifest.json")
    assert all(sha(ROOT/n)==x["sha256"] for n,x in manifest["files"].items()),"Previous V3 differs from finalized manifest"
    archive=ROOT.parent/"runs/v3_before_combined_2026-10-22.zip"
    assert not archive.exists(),"Preserve the existing revision archive"
    with ZipFile(archive,"x",ZIP_DEFLATED) as z:
        for name in list(manifest["files"])+["manifest.json"]:
            z.write(ROOT/name,"v3/"+name)
    with ZipFile(archive) as z:
        assert all(hashlib.sha256(z.read("v3/"+n)).hexdigest()==x["sha256"] for n,x in manifest["files"].items())
    prefixes=("data/raw/","data/chinese_collection/","data/input/","data/merged/","data/stores/")
    extra={"data/analysis/comment_labels.json","data/analysis/comment_labels.csv","data/analysis/validation_sample.json","manual_review.json","language_boundary_review.json","review_binding.json"}
    protected={n:x["sha256"] for n,x in manifest["files"].items() if n.startswith(prefixes) or n in extra}
    dump(ROOT/"data/input/combined_revision_preservation.json",protected)
    dump(ROOT/"revision.json",dict(revised_at_utc=now(),reason="Combine English and Chinese in one result; retain V1 monthly chart with separate stores and BOCHK",previous_delivery_archive=archive.relative_to(ROOT.parent).as_posix(),archive_sha256=sha(archive),previous_report_sha256=manifest["report_sha256"],protected_files=len(protected),collection="Saved V3 capture reused; no new network collection"))
    print(json.dumps(dict(archived_files=len(manifest["files"])+1,archive=str(archive),protected_files=len(protected))))

if __name__=="__main__":
    main()
