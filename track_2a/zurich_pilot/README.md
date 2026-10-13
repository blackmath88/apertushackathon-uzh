# Stadt Zürich — Lost in Switzerland field pilot

This directory documents the municipal multilingual-content pilot. The scientific UZH submission stays in the existing B0/B2 pipeline; this experiment has **no SwissGov-RSD gold labels**.

## Implemented (first slice)
- [Concept](../docs/LOST_IN_SWITZERLAND_CONCEPT.md) and [build plan](../docs/ZURICH_PILOT_BUILD_PLAN.md)
- Python standard-library `uzh_rsd.zurich_pilot`: strict HTTPS same-host discovery, URL normalisation, content-type/size bounds, robots fail-closed, bounded crawl and delay, explicit reciprocal `hreflang` pair candidates.
- Source URL, UTC capture time, HTML digest, extraction version and candidate pairing retained in JSON; excludes whole HTML/text from output.
- Python contract tests for scope, tracking parameters, real hreflang, negative pairing and limits.

## Offline checks
From `track_2a`:

```sh
PYTHONPATH=src python -m unittest discover -s tests -p 'test_zurich_pilot.py' -v
```

## Explicitly opt-in live research

Review current `stadt-zuerich.ch` terms and robots policy first. The command below **makes public-site requests** and should be run only by an authorized operator (not in CI):

```sh
cd track_2a
PYTHONPATH=src python - <<'PY'
from uzh_rsd.zurich_pilot import scout
result = scout(
    "https://www.stadt-zuerich.ch/de/lebenslagen/neu-in-zuerich",
    max_pages=15, max_depth=2, delay_seconds=2.0,
    out="runs/zurich-scout.json")
print({"captured": len(result["captured"]),
       "candidate_pairs": len(result["pairs"]),
       "unpaired": result["unpaired_count"],
       "failures": len(result["failures"])})
PY
```

**No page fetching or model inference has been executed by the creation of this branch.** Explicit reciprocal `hreflang` remains **candidate**, never verified semantic equivalence. Empty candidate pairing is a valid outcome. No PDFs, login, forms or browser interactions are attempted.

## Next work
Integrate a provenance-checked pair capture with a bounded excerpt adapter to B2, plus reviewer status and a small viewer; only after source reuse and network policy checks. The current Scout deliberately does **not** claim to detect semantic discrepancies, does not crawl 3–5 proven pairs yet, does not run WATCH and does not publish findings.

### Architecture attribution
Adapted from [accessibility-red-team](https://github.com/blackmath88/accessibility-red-team) concepts, especially `src/scout/`, `src/network-policy.ts`, `src/provenance/`, `src/watch/` and `docs/CAMPAIGN.md`. The implementation is a clean Python rewrite for bilingual semantic comparison; it does not copy WCAG scanning or inaccessible-site reporting logic.
