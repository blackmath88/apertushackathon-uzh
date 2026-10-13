# Live government pilot v1

This directory is separate from SwissGov-RSD train/dev/test data. It contains a bounded distributable policy/run manifest and a clearly marked **synthetic** fixture demonstration. It contains no BFE page HTML or copied BFE prose.

## Current result

The 13 October 2026 policy preflight made two requests: BFE `robots.txt` and the applicable official `admin.ch` legal notice. Robots did not disallow the proposed paths, but the legal notice says reproduction of site elements requires prior written permission. Because that permission is not documented, the pipeline stopped before either BFE content seed was requested: 0 content pages, 0 candidates, 0 verified live pairs.

The committed viewer demonstrates the complete offline mechanics using project-authored German/French fixtures. Its `HUMAN_VERIFIED` state applies to the synthetic fixture pair only; it is not a government-page finding.

## Reproduce

From `track_2a`:

```sh
# Offline tests (includes all original Zürich tests)
PYTHONPATH=src python -m unittest discover -s tests -v

# Deterministic fixture capture, analysis and viewer generation
PYTHONPATH=src python -m uzh_rsd.live_government_pilot demo \
  --fixtures tests/fixtures/live_government_pilot \
  --policy live_government_pilot/v1/policy/bfe-policy-review-20261013.json \
  --out live_government_pilot/v1/demo

# Direct live module entrypoint. Under the committed policy it writes/prints a
# POLICY_BLOCKED manifest and the Python process exits 3 without a page request.
PYTHONPATH=src python -m uzh_rsd.live_government_pilot live --confirm-live \
  --policy live_government_pilot/v1/policy/bfe-policy-review-20261013.json \
  --out runs/live-government-pilot.json

# Make invokes that same command. The recipe command returns 3; GNU Make then
# reports the failed recipe and exits 2 (GNU Make's wrapper status).
make federal-pilot-live

# Local viewer; stop with Ctrl-C.
python -m http.server 8765 --directory live_government_pilot/v1/demo
curl --fail http://127.0.0.1:8765/viewer.html >/dev/null
```

The two exit codes describe different processes: direct callers of
`python -m uzh_rsd.live_government_pilot live ...` receive **3**, while callers
of `make federal-pilot-live` receive **2** from GNU Make. Both paths remain
`POLICY_BLOCKED` and make zero BFE content-page requests.

Raw response and capture storage is content-addressed under `runs/` or a generated `raw/` directory and is gitignored. The committed demo manifest contains only synthetic fixture excerpts. If reuse permission is later documented, create a new immutable policy review rather than editing this one, then run the same bounded entrypoint; profile constraints remain max 20 pages, depth 2, at least two seconds per host, exact HTTPS hosts, fail-closed robots and redirect revalidation.

## Method and scientific boundary

`deterministic-lexical-structural-v1` records source facts (hashes, block counts/order and structural deltas) separately from an unresolved cross-language lexical-overlap diagnostic. It is explicitly non-Apertus, uses no B4 vectors, makes zero model calls, has no live gold labels and makes no Spearman or discrepancy claim. B4 remains a separate Qwen-based zero-Apertus benchmark result; B5 remains **NOT SUPPORTED**.

Architecture concepts are attributed to `blackmath88/accessibility-red-team` (bounded prioritized discovery, strict scope, provenance, explicit triage states and escaped static reports). That repository exposes no license, so no source code was copied.
