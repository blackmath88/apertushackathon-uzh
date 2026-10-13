# B4 — Alignment-First SDM

This directory contains immutable Experiment A and B artifacts for the frozen B2/B3 30-document development sample. Gold-derived A predictions are diagnostics only. B predictions are gold-blind pinned DiffAlign outputs; gold is joined only by the scoring stage.

## Exact reproduction

From `track_2a/`:

```bash
make s1-fetch
PYTHONPATH=src python3 -m uzh_rsd.b4 oracle \
  --manifest experiments/b2-projection-evidence/manifest.json \
  --out runs/b4-oracle-reproduction --split dev
PYTHONPATH=src python3 -m uzh_rsd.b4 alignment \
  --manifest experiments/b2-projection-evidence/manifest.json \
  --cache data/upstream/diffalign \
  --out runs/b4-alignment-reproduction --split dev
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Each command refuses to overwrite its output directory. Compare reproduced `results.json` semantically: `created_utc`, measured replay resources, and cache paths are expected to vary. Prediction vectors and metrics are deterministic.

`source-checksums.sha256` fingerprints the frozen B0/B2/B3 evidence used for comparison. `oracle-20261013/checksums.json` and `alignment-20261013/checksums.json` fingerprint the B4 artifacts.

Experiment C was not executed. A/B point to token projection/alignment rather than semantic classification, so no Apertus process was started and no calls were made.
