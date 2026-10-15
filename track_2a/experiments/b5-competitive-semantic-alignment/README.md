# B5 — Competitive Semantic Alignment

This directory is the immutable, development-only evidence package for B5. The mandatory order was followed: A was frozen and scored, the coordinator authorized B, B was frozen and run, and the coordinator stopped the experiment after Gate B failed. Experiment C was not started.

## Exact reproduction

From `track_2a/`:

```bash
make s1-fetch

# A selection freeze: consumes only B4 tokens/scalar anomaly evidence, no gold.
PYTHONPATH=src .venv/bin/python -m uzh_rsd.b5 freeze-a \
  --evidence experiments/b4-alignment-first-sdm/alignment-20261013/evidence.jsonl \
  --out runs/b5-selector-reproduction.json --split dev
sha256sum runs/b5-selector-reproduction.json
# Expected: 34c485e68cc5584b91e1597440952f496e6f206eca2ff8a492140932e86cdd39

# A oracle evaluation: gold enters only after the frozen selector is loaded.
PYTHONPATH=src .venv/bin/python -m uzh_rsd.b5 score-a \
  --selector experiments/b5-competitive-semantic-alignment/selector-manifest.json \
  --baseline experiments/b4-alignment-first-sdm/alignment-20261013/predictions.jsonl \
  --manifest experiments/b2-projection-evidence/manifest.json \
  --out runs/b5-a-reproduction --split dev

# B environment (task-scoped; PyTorch XPU follows the official PyTorch Intel-GPU install route).
python3 -m venv .venv-b5
.venv-b5/bin/pip install torch==2.10.0 --index-url https://download.pytorch.org/whl/xpu
.venv-b5/bin/pip install transformers==5.2.0 tokenizers==0.22.2 \
  huggingface_hub==1.4.1 safetensors==0.7.0 numpy==2.4.2 scipy==1.17.0

# Put Qwen/Qwen3-Embedding-4B revision 5cf2132abc99cad020ac570b19d031efec650f2b
# in data/models/Qwen3-Embedding-4B-5cf2132 and verify the model hashes recorded
# in b-embedding-provenance.json. The two weight files total 8,043,592,088 bytes.
PYTHONPATH=src .venv-b5/bin/python -m uzh_rsd.b5_alignment encode-b \
  --evidence experiments/b4-alignment-first-sdm/alignment-20261013/evidence.jsonl \
  --model data/models/Qwen3-Embedding-4B-5cf2132 \
  --cache data/b5-reproduction/embeddings-layer20 \
  --provenance runs/b5-b-embedding-provenance.json --split dev

PYTHONPATH=src .venv-b5/bin/python -m uzh_rsd.b5_alignment score-b \
  --cache data/b5-reproduction/embeddings-layer20 \
  --cache-provenance runs/b5-b-embedding-provenance.json \
  --evidence experiments/b4-alignment-first-sdm/alignment-20261013/evidence.jsonl \
  --baseline experiments/b4-alignment-first-sdm/alignment-20261013/predictions.jsonl \
  --a-interventions experiments/b5-competitive-semantic-alignment/a-oracle-20261013/interventions.jsonl \
  --manifest experiments/b2-projection-evidence/manifest.json \
  --out runs/b5-b-reproduction --split dev

make s1-check
sha256sum -c experiments/b5-competitive-semantic-alignment/checksums.sha256
```

All commands reject `test` before input I/O and refuse to overwrite outputs. The 37 MB embedding/similarity cache is intentionally ignored; its 30 per-document hashes, source hash, model hashes, software versions, shape, timing and coverage are committed in `b-embedding-provenance.json`.

## Evidence map

- `selector-manifest.json`: pre-gold original-token selections, committed at `dd4141f`.
- `a-oracle-20261013/`: A predictions, metrics, bootstrap, sensitivity and checksums.
- `b-input-audit-and-config.json`: pre-download availability/cost audit and frozen M0–M3 parameters, committed at `231423a`.
- `b-embedding-provenance.json`: exact model/software/cache provenance.
- `b-alignment-20261013/`: official-order predictions, explicit counterpart/NULL records, diagnostics, metrics and checksums.
- `report.md`: interpretation, failures, gates, protocol disclosure and recommendation.
- `checksums.sha256`: package integrity plus frozen B0–B4 source hashes.
