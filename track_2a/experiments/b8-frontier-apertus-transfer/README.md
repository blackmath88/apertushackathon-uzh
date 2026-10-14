# B8 frontier-to-Apertus transfer package

Status: **frozen pre-inference design; no model calls performed**.

B8 tests whether evidence representation and a fixed decision contract transfer
from a development-time frontier teacher to local Apertus. It does not claim an
Apertus improvement, does not alter the B7 result, and does not project synthetic
judgements onto SwissGov-RSD.

The package contains 27 independently authored synthetic EN-DE/FR/IT pairs in
nine source families. Three families are optimization-only and six are held-out
evaluation families. Every case is marked `provisionally_reviewed`, never
`human_verified`; no protected test data or metadata is present.

Frozen inputs:

- `PROTOCOL.md` and `protocol.json`: design, gates, controls, thresholds, and hard ceilings.
- `families.json` and `synthetic-cases.json`: source-family split and case evidence.
- `schemas/R0.schema.json` through `schemas/R3.schema.json`: representation contracts.
- `freeze-manifest.json` and `freeze-checksums.sha256`: immutable input hashes.

Implementation and evidence:

- `uzh_rsd.b8`: validates the freeze, expands representations, schedules the
  complete design, writes append-only JSONL ledgers, and evaluates already
  captured outputs. Network access is absent from this module by design.
- `schedule-dry-run.json`: proves the full design fits the frozen ceilings.
- `checksums.sha256`: package evidence checksums after the dry run.

The runner accepts an injected callable only; the CLI offers validation,
scheduling, and evaluation but no HTTP or provider client. Any later execution
requires separate authorization and must prove model identity before the first
call. The local student identity is fixed to GGUF SHA-256
`dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d`,
llama.cpp commit `7ab4ee7`, and `http://127.0.0.1:11436`.

```bash
PYTHONPATH=track_2a/src python -m uzh_rsd.b8 validate \
  --package track_2a/experiments/b8-frontier-apertus-transfer
PYTHONPATH=track_2a/src python -m uzh_rsd.b8 schedule \
  --package track_2a/experiments/b8-frontier-apertus-transfer
python -m unittest track_2a/tests/test_b8.py
```

The PR #26 handoff is preserved as input context, not execution authority:
<https://github.com/blackmath88/apertushackathon-uzh/pull/26>.
