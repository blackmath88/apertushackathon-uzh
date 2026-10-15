# B3 Semantic Decision Middleware experiment

This directory is the predeclared B3 experiment on the exact 30 development
IDs frozen by PR #14.  The task graph and all policies were frozen before any
B3 inference response was viewed.

Preflight: **FIT**.  The graph has 230 comparison tasks: 219 model routes and
11 deterministic structural routes, with no overflow.  The maximum is eight
tasks in any document, below the declared 12.  The run therefore needs at most
219 classifier calls (limit 300), 21,024 completion tokens at the 96-token cap,
and approximately 56,513 prompt tokens.  Using the observed local rate of 29
completion tokens/s plus 0.75 s request overhead, conservative runtime is
889.216 s (14.82 min), below the 35-minute ceiling.

The projection policy marks both inherited passage spans as `1.0` only for a
validated `DIFFERENT` decision. Resolved `EQUIVALENT` spans are `0.0`.
Unresolved or abstained spans retain an explicit unknown mask; the separately
reported full-sample vector uses zero only as an **evaluation default**, never
as a semantic-equivalence claim.

## Commands

```sh
PYTHONPATH=track_2a/src python3 -m uzh_rsd.sdm.experiment freeze \
  --source track_2a/experiments/b2-projection-evidence/manifest.json \
  --out track_2a/experiments/b3-sdm/task-manifest.json

LLM_NAME=apertus-v1.5-8b-text-q8_0 \
LLM_BASE_URL=http://127.0.0.1:11436/v1 LLM_API_KEY=local \
PYTHONPATH=track_2a/src python3 -m uzh_rsd.sdm.experiment infer \
  --manifest track_2a/experiments/b3-sdm/task-manifest.json \
  --out track_2a/experiments/b3-sdm/local-q8-20261013

PYTHONPATH=track_2a/src python3 -m uzh_rsd.sdm.experiment score \
  --manifest track_2a/experiments/b3-sdm/task-manifest.json \
  --run track_2a/experiments/b3-sdm/local-q8-20261013
```

Only the development split is in scope. No official test data, HF job, cloud
endpoint, paid compute, or Zürich network/city data is used.

## Outcome

The run completed in 442.277 s with 219 calls and zero transport failures, but
only 42 model responses passed the frozen strict contract. No document had
complete semantic-decision coverage; B3 IT was constant/undefined under the
full-sample zero evaluation default. Verdict: **NOT SUPPORTED**. See the
[run report](local-q8-20261013/report.md) for comparison tables and cases.
