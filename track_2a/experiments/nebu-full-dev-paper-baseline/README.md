# Nebu full-dev paper baseline

The pre-inference freeze was executed, independently reviewed, and finalized as
a **descriptive run with a post-freeze runner deviation**. `PROTOCOL.md`,
`run-config.json`, and `manifest.json` remain the immutable historical freeze;
the executed state and results are documented in `execution/REPORT.md`, and the
post-hoc contract is in `execution/AMENDED_EXECUTION_CONTRACT.md`. The manifest
and committed execution outputs are text-free. Private stage-separated inputs
remain only in ignored local storage, with non-sensitive hashes anchored in
`execution/runtime-evidence-checksums.sha256`.

Synthetic/mock verification:

```bash
PYTHONPATH=track_2a/src python -m unittest track_2a/tests/test_full_dev_baseline.py
```

No command in this package starts a server. The freeze-time “PREPARED / NO REAL
MODEL CALLS” wording in `PROTOCOL.md` and `PRE_INFERENCE_REPORT.md` is retained
as historical pre-inference state, not the package's current status.
