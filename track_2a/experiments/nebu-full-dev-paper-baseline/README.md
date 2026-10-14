# Nebu full-dev paper baseline

Preparation is complete; real inference is **NOT RUN**. `PROTOCOL.md`,
`run-config.json`, and `manifest.json` are the immutable pre-inference freeze.
The manifest is text-free and accounts for every pinned dev pair. Private
stage-separated inputs exist only in ignored local storage.

Synthetic/mock verification:

```bash
PYTHONPATH=track_2a/src python -m unittest track_2a/tests/test_full_dev_baseline.py
```

No command in this package starts a server. Execution requires a later,
separately verified launch after checking the freeze commit, exact endpoint
identity, tokenizer context fit, exclusive GPU/runtime ownership, and unchanged
Morrow/B8 boundaries.
