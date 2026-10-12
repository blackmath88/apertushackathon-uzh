# Status — 12 October 2026 (B0/B2 MVP branch)

Scope: [one UZH MVP](MVP_PLAN.md), B0 versus B2 on identical dev documents.

## Measured (Apertus v1.5 8B, HF Jobs L40S)

- **Run `20261012T062327Z-ff965461`** (HF job `6acc7ce1095c578089328f6d`, COMPLETED). Evidence is in [`results/20261012T062327Z-ff965461/`](../results/20261012T062327Z-ff965461/results.md) and the findings in [technical report §5](../technical_report.md#5-evaluation).
  - 18 of 18 calls returned: no call failures, no deadline skips, no upload failures.
  - Running time 994 s. Before that the job waited 53 min for hardware, which is not billed.
- **Coverage.** B2 has valid output for 9 of 9 documents. B0 has it for 3 of 9: three responses were truncated at 4096 tokens (`*_197`) and three were malformed JSON that stopped normally (`*_136`).
- **Matched comparison (n = 3):** macro Spearman 0.136 for B0 and 0.138 for B2, a tie.
  - B2 over all 9 of its documents reaches macro 0.175.
  - B2 used about 20 % of B0's completion tokens and generation time.
  - B0's paper-protocol 0.268 comes from zero-filled documents (6 of 9) creating a between-document offset; it is not token-level skill.
- **Checks on the run:**
  - Official-evaluator parity: max difference 5.6e-17 over 18 cells.
  - An offline re-score of the committed `raw.jsonl` reproduces `results.json` and the predictions byte for byte.
  - A secret scan of the artifacts was clean.
  - No test-split file exists on disk.
- **This is not Apertus evidence:** the earlier CPU run with a tiny public model and the mock-endpoint Docker run only tested the pipeline.

## Implemented and verified

- **B0 paper baseline.** Pinned upstream admin templates (sha256-checked), the upstream `parse_token_labels` with every fallback token counted, the official `1 − s/5` mapping. Deviations are listed in the [technical report](../technical_report.md#b0--paper-baseline-and-deviations).
- **B2.** Zero-shot difference-span prompt `b2-spans-v1`, verbatim excerpt location, deterministic projection via `projection.py`. Invalid, unlocatable, ambiguous and unknown items are counted.
- **Runner.** Identical manifest documents for both methods, in language-interleaved order. One raw record per call (prompt, response, tokens, latency, finish reason). Deadline skips and call failures are explicit.
- **Scoring.** Matched / available / paper-protocol views with coverage and usage, official-format prediction export, official evaluator cross-check.
- **Backends.** OpenAI-compatible endpoint (judge path, tested against mock HTTP); transformers (HF batch GPU, now measured on L40S).
- **HF Jobs launcher.** Private dataset repo `metamax88/uzh-rsd-runs` for bundle and results; privacy was verified, and an anonymous request gets HTTP 401. Results upload after every call, with a log-bundle fallback. A spend ledger enforces a hard ceiling, and `attempts=1`.
- **Docker.** `make run` builds and runs the image. Without `LLM_*` it stops with BLOCKED (exit 3). `make reproduce` re-scores committed raw responses offline.
- **Checks.** On the Mac with Python 3.13, `make s1-check` gives 83 tests and zero skips. The manifest reproduces and the test split is refused.

## Not yet done

- **Larger dev slice.** Only the nine-document pilot is measured. A larger, predeclared dev slice is needed before any claim about which method correlates better.
- **Judge endpoint.** No Apertus endpoint for `make run` is confirmed (N-JUDGE-1).
- **Docker clean checkout.** `make reproduce` from a clean checkout on a normal host is recorded in the submission checklist (E3).

## Compute (all Hack Apertus HF Jobs on account `metamax88`)

| Job | What | Running | Upper bound |
|---|---|---|---|
| `6acbc136fee2c90070199598` | manual smoke, ERROR | 53 s | $0.09 |
| `6acbc1d5fee2c90070199649` | manual smoke, COMPLETED | 123 s | $0.09 |
| `6acc7ce1095c578089328f6d` | B0/B2 run, COMPLETED | 994 s | $0.51 |
| **Total** | | | **$0.69** of the $3.00 cap |

How the bounds are computed:

- Price: `l40sx1` at $0.03/min, from the HF API on 12 October.
- HF bills per minute, only while a job is Starting or Running.
- The two smoke bounds also include their scheduling time, rounded up to whole minutes.
- The B0/B2 bound rounds its running time up to whole minutes.
- The HF billing page was not checked, so these are upper bounds, not invoices. Details are in [`compute.json`](../results/20261012T062327Z-ff965461/compute.json).
