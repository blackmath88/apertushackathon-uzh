# B7 structural control and bounded semantic verification

This is the immutable development-only B7 evidence package. The protocol-freeze
commit is `70b1eaf`; all new gold-aware results and model calls occurred later.
Published B4, regenerated B5, and B6 are kept distinct. B5 and B6 remain NOT
SUPPORTED. No protected test path or metadata was accessed.

## Exact reproduction

Run from the repository root. `B5_CACHE` is the retained read-only matrix cache;
the commands never invoke an encoder.

```bash
export B7_PY=/home/achim/orca/workspaces/apertushackathon-uzh/b5-competitive-semantic-alignment/track_2a/.venv-b5/bin/python
export B5_CACHE=/home/achim/orca/workspaces/apertushackathon-uzh/b5-competitive-semantic-alignment/track_2a/data/b5-competitive-semantic-alignment/embeddings-5cf2132-layer20-officialmap-v2

PYTHONPATH=track_2a/src "$B7_PY" -m uzh_rsd.b7 freeze \
  --evidence track_2a/experiments/b4-alignment-first-sdm/alignment-20261013/evidence.jsonl \
  --b5-selector track_2a/experiments/b5-competitive-semantic-alignment/selector-manifest.json \
  --cache "$B5_CACHE" \
  --cache-provenance track_2a/experiments/b5-competitive-semantic-alignment/b-embedding-provenance.json \
  --out track_2a/runs/b7-candidate-reproduction.json

PYTHONPATH=track_2a/src "$B7_PY" -m uzh_rsd.b7 structural \
  --cache "$B5_CACHE" \
  --cache-provenance track_2a/experiments/b5-competitive-semantic-alignment/b-embedding-provenance.json \
  --evidence track_2a/experiments/b4-alignment-first-sdm/alignment-20261013/evidence.jsonl \
  --out track_2a/runs/b7-s2-reproduction.jsonl

cd track_2a/experiments/b7-structural-semantic-verification
sha256sum -c freeze-checksums.sha256
sha256sum -c checksums.sha256
cd ../../../
make -C track_2a s1-check VENV=.venv
```

The two local inference commands are intentionally not part of ordinary replay.
They require the exact GGUF and a separately owned llama.cpp server on port
11436; they refuse other endpoints and existing outputs:

```bash
PYTHONPATH=track_2a/src "$B7_PY" -m uzh_rsd.b7 run-synthetic --input track_2a/experiments/b7-structural-semantic-verification/synthetic-cases.json --out NEW_SYNTHETIC.jsonl --base-url http://127.0.0.1:11436 --model apertus-v1.5-8b-q8_0
PYTHONPATH=track_2a/src "$B7_PY" -m uzh_rsd.b7 run-candidates --input track_2a/experiments/b7-structural-semantic-verification/candidate-manifest.json --out NEW_CANDIDATES.jsonl --base-url http://127.0.0.1:11436 --model apertus-v1.5-8b-q8_0
```

Gold-aware `evaluate` and `audit` invocations are represented exactly by the
argument declarations in `b7.py`; `REPORT.md` records the resulting hashes.
