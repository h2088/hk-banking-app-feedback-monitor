"""Bind individually authored, actually read judgments to the current sample."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))
from feedback_io import dump, load, sha, now
sample = load(ROOT / "data/analysis/validation_sample.json")
notes = {row[0]: row[1:] for row in load(ROOT / "review_judgments.json")}
assert set(notes) == {r["record_key"] for r in sample}, "Actual judgments must cover this exact sample"
dump(ROOT / "manual_review.json", dict(status="reviewed", reviewer="Codex agent", reviewed_at_utc=now(),
    scope="Actually read latest comment in each observed bank/store/rating stratum; targeted limitations recorded, not an independent human accuracy study.",
    sample_sha256=sha(ROOT / "data/analysis/validation_sample.json"),
    reviews=[dict(record_key=r["record_key"], fingerprint=r["fingerprint"], rating_assessment=notes[r["record_key"]][0], theme_assessment=notes[r["record_key"]][1], notes=notes[r["record_key"]][2]) for r in sample]))
print(json.dumps(dict(sample_reviews=len(sample), status="reviewed")))
