# Status — 13 October 2026 (B0/B2 MVP branch)

**Candidate prepared with blockers.** Live endpoint judge execution has never been performed against a real Apertus endpoint, and the official evaluation contract is unconfirmed. Corrections on 13 Oct, second pass: "valid" became "parseable" for B0; "a tie" became near-equality; B2 loss accounting now has explicit units ([audit supplement](../diagnostics/20261012T062327Z-ff965461/audit_supplement.md)); replay network needs stated; test-split judging added as a blocker. Review pass 13 Oct: [review](review/REVIEW_2026-10-13.md), [judge readiness](JUDGE_READINESS.md), [publication review](PUBLICATION_REVIEW.md), [task ledger](ORCA_TASK_LEDGER.md).

Scope: [one UZH MVP](MVP_PLAN.md), B0 versus B2 on identical dev documents.

## Measured (Apertus v1.5 8B, HF Jobs L40S)

- **Run `20261012T062327Z-ff965461`** (HF job `6acc7ce1095c578089328f6d`, COMPLETED). Evidence is in [`results/20261012T062327Z-ff965461/`](../results/20261012T062327Z-ff965461/results.md) and the findings in [technical report §5](../technical_report.md#5-evaluation).
  - 18 of 18 calls returned: no call failures, no deadline skips, no upload failures.
  - Running time 994 s. Before that the job waited 53 min for hardware, which is not billed. Recovered logs of the two earlier smoke jobs are in `prior_jobs/`.
- **Coverage.** B2 output is parseable for 9 of 9 documents. B0 output is parseable for 3 of 9: three responses were truncated at 4096 tokens (`*_197`) and three were malformed JSON that stopped normally (`*_136`). None of the three parseable B0 documents is strictly valid: 46 of 541 tokens fell back to "no difference".
- **Matched comparison (n = 3, one document per language sharing one English source):** macro Spearman 0.136 for B0 and 0.138 for B2. Nearly equal; no accuracy advantage is demonstrated.
  - Of B2's 41 items, 30 were projected completely, 4 partially (one excerpt located, the other not) and 7 not at all. The 7 unprojected items are 6 with both excerpts over the 40-token cap and 1 with both excerpts not found (`admin_fr_43`). Counted per excerpt (two per item): 14 over the cap (12 in unprojected items, 2 in partial ones) and 4 not found (2 + 2), all 4 in `admin_fr_43`. Accounting: [audit supplement](../diagnostics/20261012T062327Z-ff965461/audit_supplement.md).
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
- **Docker.** `make run` builds and runs the image. Without `LLM_*` it stops with BLOCKED (exit 3). `make reproduce` re-scores committed raw responses with no model inference. It still needs network access for the base image and the pinned dev data/evaluator files.
- **Checks.** On the Mac with Python 3.13, `make s1-check` gives 105 tests and zero skips (83 before the 13 Oct audit-supplement and final-inference tests). The manifest reproduces and the test split is refused.

## Not yet done

- **Larger dev slice.** Only the nine-document pilot is measured. A larger, predeclared dev slice is needed before any claim about which method correlates better. Protocol drafted (not run): [NEXT_EXPERIMENT_PROTOCOL.md](NEXT_EXPERIMENT_PROTOCOL.md).
- **Judge endpoint.** No Apertus endpoint for `make run` is confirmed (N-JUDGE-1).
- **Live Docker run.** `make run` has not run against a real Apertus endpoint: no endpoint for judges is confirmed (N-JUDGE-1), which does not mean none exists. The UZH Q&A mentions a CSCS inference API with a 60 s gateway timeout. Docker `make reproduce` was verified from a clean clone on 12 Oct and again at `662e14d` on 13 Oct.
- **Test-split predictions (N-RULES-1, new 13 Oct).** The UZH Q&A says judges score on the test split and teams run their system on it at the end. This repo has no final-evaluation path and no test predictions. Adding them needs an owner decision and new compute; see [JUDGE_READINESS.md](JUDGE_READINESS.md).
  - **Final-inference path implemented (13 Oct, third pass), synthetic tests only.** `python -m uzh_rsd.final` is gold-blind, contract-gated (the committed template is refused), keeps contract order and never zero-fills or overwrites. It has never run on real test data or a real endpoint, and the gold-stripping input step is not built. See [JUDGE_READINESS.md](JUDGE_READINESS.md#final-inference-path-implemented-13-oct-synthetic-tests-only).

## Compute (all Hack Apertus HF Jobs on account `metamax88`)

| Job | What | Running | Upper bound |
|---|---|---|---|
| `6acbc136fee2c90070199598` | manual smoke, ERROR | 53 s | $0.09 |
| `6acbc1d5fee2c90070199649` | manual smoke, COMPLETED | 123 s | $0.09 |
| `6acc7ce1095c578089328f6d` | B0/B2 run, COMPLETED | 994 s | $0.57 |
| **Total** | | | **$0.75** of the $3.00 cap |

How the bounds are computed:

- Price: `l40sx1` at $0.03/min, from the HF API on 12 October.
- HF bills per minute, only while a job is Starting or Running.
- The two smoke bounds also include their scheduling time, rounded up to whole minutes.
- The B0/B2 bound rounds its running time up to whole minutes, then adds 2 min for billed Starting time that may fall before `started_at` (the largest pre-start overhead observed on this image was 101 s).
- The HF billing page was not checked, so these are upper bounds, not invoices. Details are in [`compute.json`](../results/20261012T062327Z-ff965461/compute.json).
