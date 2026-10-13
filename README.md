# Lost in Switzerland — UZH SwissGov-RSD

Hack Apertus 2026 · Track 2A · one submission, one measured B0/B2 comparison.

**Question:** does asking Apertus for meaning-changing spans, then projecting them onto tokens (B2), work better than asking it to score every token directly (B0, the paper baseline)?

## Current state

B0, B2, scoring, Docker `make run` and the HF GPU runner are implemented and tested. **First measured pilot committed** (12 Oct 2026, run `20261012T062327Z-ff965461`, nine dev documents). B2 produced valid output for 9 of 9 documents and B0 for 3 of 9. On the 3 matched documents, macro Spearman is 0.136 for B0 and 0.138 for B2, a tie. B2 used about 20 % of B0's tokens. This is indicative, not a benchmark. See [results](track_2a/results/20261012T062327Z-ff965461/results.md) and [STATUS](track_2a/docs/STATUS.md).

## Commands

| Goal | Command | Needs |
|---|---|---|
| Judge run | `LLM_NAME=… LLM_BASE_URL=… LLM_API_KEY=… make run` | Docker, OpenAI-compatible Apertus endpoint |
| Re-score committed run, no model | `make reproduce` | Docker |
| Tests (no skips allowed) | `make -C track_2a s1-setup s1-fetch s1-check` | Python ≥ 3.11 |

Without the `LLM_*` variables, `make run` stops with a clear BLOCKED message (exit 3). It never substitutes results.

## Measured GPU run (owner machine)

This uses the token saved by `hf auth login`. The token is passed to the job only as the `HF_TOKEN` secret; it is never printed or written. One job, `l40sx1`, timeout 45 min, so the ceiling is **$1.35**. The spend ledger refuses launches beyond $3.00 in total, and there are no automatic retries.

```bash
cd track_2a
make mvp-setup s1-fetch          # venv: evaluator deps + huggingface_hub
make hf-launch-dry               # bundle → private dataset <you>/uzh-rsd-runs; no GPU, $0
make hf-launch                   # starts ONE GPU job; prints run id and job URL
make hf-collect RUN_ID=<run id>  # waits, downloads raw results (repo, else job log), records actual cost
make evaluate  RUN_ID=<run id>   # scores, writes runs/<run id>/results.md + predictions
make hf-spend                    # ledger
```

To commit a run: `cp -r runs/<run id> results/` (drop nothing: raw.jsonl, run_meta.json, results.*, predictions/).

## Start here

- [Orca handoff — submission preparation, 13 October](track_2a/docs/ORCA_HANDOFF_2026-10-13.md): work packets, review gates and owner decisions; no new compute authorized.

- [MVP plan](track_2a/docs/MVP_PLAN.md) · [Status](track_2a/docs/STATUS.md) · [Submission checklist](track_2a/docs/SUBMISSION_CHECKLIST.md)
- [Technical report draft](track_2a/technical_report.md)
- [Challenge brief](docs/challenge-source/CHALLENGE.md) · [Sources](track_2a/docs/SOURCES.md)

Only pinned dev files are downloaded. The test split is never fetched, prompted or evaluated, and the code refuses it before any I/O. Publication and portal submission are owner decisions.
