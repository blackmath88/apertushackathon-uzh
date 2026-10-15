# B4 — Alignment-First SDM

This directory contains immutable Experiment A and B artifacts for the frozen B2/B3 30-document development sample, plus the separately authorized bounded Experiment C capability probe. Gold-derived A predictions are diagnostics only. B predictions are gold-blind pinned DiffAlign outputs; gold is joined only by the scoring stage.

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

Experiment C was run only after the A/B gate. The committed command was:

```bash
PYTHONPATH=src python3 -m uzh_rsd.b4_probe \
  --base-url http://127.0.0.1:11436 \
  --out experiments/b4-alignment-first-sdm/apertus-probe-20261013 \
  --split dev
```

This command requires the pinned Apertus-v1.5-8B Q8_0 model already running through llama.cpp commit `7ab4ee7` on loopback port 11436 and makes exactly 16 calls, so it is not part of ordinary offline reproduction. It refuses test, other hosts/ports, and existing output directories. `apertus-probe-20261013/checksums.json` fingerprints the prompts, raw outputs, and summary; port 11436 was stopped after capture and Morrow on port 11435 was untouched.
