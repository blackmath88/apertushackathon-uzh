# Track 2A — UZH SwissGov-RSD

This directory is the submission workspace for the UZH SwissGov-RSD challenge.

## Research question

Can Apertus perform better when cross-lingual semantic differences are compiled into a small, typed span-level representation and then deterministically projected to token scores, instead of asking the model to score every token directly?

## First comparison

- **B0 — Direct Apertus:** document pair → Apertus → token scores.
- **B2 — Semantic compiler:** document pair → alignment → Apertus sparse difference spans → deterministic token projection.
- **B2a — Binary span localisation:** diagnostic before severity prediction.

## Run

```bash
make run
make test
```

The scaffold currently performs a dry run only. Model integration and dataset ingestion are deliberately not implemented until the baseline adapter is explicit.

## Non-negotiables

- Apertus is the semantic model used by the submitted solution.
- Test data does not enter development.
- Raw source data is never overwritten.
- Model outputs are derived artifacts, not canonical observations.
- Normal code owns split enforcement, schemas, token bookkeeping, projection, evaluation, metadata and caching.
- `UNKNOWN` / abstention remains legal where the semantic decision is unresolved.

See [docs/PLAN.md](docs/PLAN.md).
