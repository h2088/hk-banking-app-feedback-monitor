# Reproduce V2

Use Python 3.10+; collection dependencies are in requirements-collection.txt. The saved-input pipeline is offline and uses the Python standard library.

Copy this entire v2 directory to a new sibling directory before reprocessing. Do not rerun collection in an existing batch. In the copied directory, run:

```powershell
& '..\.venv\Scripts\python.exe' -B scripts/pipeline.py prepare --reuse-input
# Read data/analysis/validation_sample.json; write actual judgments in manual_review.json.
& '..\.venv\Scripts\python.exe' -B scripts/pipeline.py build
& '..\.venv\Scripts\python.exe' -B scripts/pipeline.py verify
& '..\.venv\Scripts\python.exe' -B scripts/browser_check.py
# Inspect screenshots before writing the visual inspection record.
& '..\.venv\Scripts\python.exe' -B scripts/pipeline.py finalize
```

Reusing the unchanged input, configuration and rules reproduces the metrics; capture timestamps, build/check times, ZIP metadata and integrity manifests can differ. A fresh network collection is a new observation and need not reproduce historical counts. collect_bochk.py is a bounded, BOCHK-only collector; SC/HSBC refresh requires an explicitly new batch and a revised capture plan. Frozen helper code in engine/ is reused; its original two-app CLI is not the V2 entry point.
