# Status — 11 October 2026 (B0/B2 MVP branch)

Scope: [one UZH MVP](MVP_PLAN.md), B0 versus B2 on identical dev documents.

## Implemented and verified here (no GPU)

- **B0 paper baseline.** Pinned upstream admin templates (sha256-checked), the upstream `parse_token_labels` with every fallback token counted, the official `1 − s/5` mapping. Deviations are listed in the [technical report](../technical_report.md#b0--paper-baseline-and-deviations).
- **B2.** Zero-shot difference-span prompt `b2-spans-v1`, verbatim excerpt location, deterministic projection via `projection.py`. Invalid, unlocatable, ambiguous and unknown items are counted.
- **Runner.** Identical manifest documents for both methods, in language-interleaved order. One raw record per call (prompt, response, tokens, latency, finish reason). Deadline skips and call failures are explicit.
- **Scoring.** Matched / available / paper-protocol views with coverage and usage, official-format prediction export, official evaluator cross-check (exact to 1e-10 on fake runs).
- **Backends.**
  - OpenAI-compatible endpoint (judge path), tested against mock HTTP.
  - transformers (HF batch GPU), run end to end on CPU with a tiny public model from the exact job bundle. That run surfaced a processor that silently drops plain-string chat content; a load-time content-format check now guards against it.
- **HF Jobs launcher.** Private dataset repo for bundle and results, upload after every call plus a log-bundle fallback, a spend ledger with a hard ceiling, `attempts=1`.
- **Docker.** `make run` builds and runs the image. Without `LLM_*` it stops with BLOCKED (exit 3). With a mock endpoint, the full path ran in the container: fetch, B0+B2, scoring, predictions. `make reproduce` re-scores committed raw responses offline.
- **Checks.** `make s1-check` gives 83 tests, zero skips; the manifest reproduces; the test split is refused, now also by `infer` / `evaluate` / `run`.

## Not yet done

- **No real Apertus predictions in this repository yet.** The GPU job has to be launched from the owner's machine, where the HF token lives. This cloud session has no HF credential. See the [runbook](../README.md#measured-gpu-run-owner-machine).
- No measured results; the technical report's result cells are empty.
- Docker image built locally from a mirror of the same `python:3.12.7-slim`, because of a Docker Hub rate limit in this sandbox. Re-verify `make run` / `make reproduce` from a clean checkout on a normal host.

## Compute

- Additional HF compute spent by this work: **$0.00**. No job was launched from this session.
- Planned run: one `l40sx1` job, timeout 45 min, so a ceiling of **$1.35** at $0.03/min. Expected 20–35 min, about $0.60–1.05. The ledger refuses any launch that would push committed spend past $3.00.
