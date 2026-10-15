# B6 Semantic Risk Atlas

This is the versioned, development-only B6 evidence package. The scientific verdict is **NOT SUPPORTED**. Gate A failed, the coordinator replied “Stop and package”, and no Apertus process or call was started. Stages B and C were skipped.

## Reproduce

From `track_2a/`, after `make s1-fetch`:

```bash
# These two commands reproduce the already committed freeze. They refuse overwrite,
# so use paths under runs/ when checking the checksums.
PYTHONPATH=src python3 -m uzh_rsd.b6 sanitize-identities \
  --source experiments/b2-projection-evidence/manifest.json \
  --out runs/b6-identity.json --split dev

PYTHONPATH=src python3 -m uzh_rsd.b6 freeze \
  --evidence experiments/b4-alignment-first-sdm/alignment-20261013/evidence.jsonl \
  --identity runs/b6-identity.json \
  --atlas experiments/b6-semantic-risk-atlas/atlas-v1.json \
  --b5-selector experiments/b5-competitive-semantic-alignment/selector-manifest.json \
  --out runs/b6-selection.json --split dev

sha256sum runs/b6-identity.json runs/b6-selection.json
# 3794c524ff1f846122eed721da1e9ef857d1fb0bd6db09ceb3a4649a466d7631
# 089848b977d324c04b67aa5bb77abdfac8ebafcaa80d178d92dbf5066d2ae228

PYTHONPATH=src python3 -m uzh_rsd.b6 score \
  --selector experiments/b6-semantic-risk-atlas/selection-manifest.json \
  --selector-sha256 089848b977d324c04b67aa5bb77abdfac8ebafcaa80d178d92dbf5066d2ae228 \
  --baseline experiments/b4-alignment-first-sdm/alignment-20261013/predictions.jsonl \
  --manifest experiments/b2-projection-evidence/manifest.json \
  --out runs/b6-stage-a --split dev

PYTHONPATH=src python3 -m unittest tests.test_b6 -v
make s1-check
sha256sum -c experiments/b6-semantic-risk-atlas/checksums.sha256
```

The selector command accepts no gold or dataset path. `score` rejects a selector unless its byte checksum is supplied and matches. All commands refuse `test` before any path construction or I/O and refuse output overwrite.

## Evidence map

- `atlas-v1.json`: independently authored CC0 risk patterns and limitations.
- `provenance.json`: primary/official sources, revisions, licences, and no-bulk-extraction policy.
- `protocol.json`: frozen arms, budget, controls, thresholds, and gated B/C contracts.
- `identity-manifest.json`: gold-free 30-document identity projection.
- `selection-manifest.json`: all A0/A1/A2/control regions, frozen at commit `ad345c4` before scoring.
- `stage-a-20261013/results.json`: exact official metrics and clustered uncertainty.
- `stage-a-20261013/selected-offsets.jsonl`: verified official-token and source-character offsets.
- `prior-artifact-proof.json`: B0-B5 byte-preservation proof.
- `report.md`: decision, failures, limitations, and recommendation.

No protected test path, metadata, or content was accessed, enumerated, downloaded, or inferred. External MQM annotations and false-friend resources were not used as hidden benchmark labels.
