# Track 2A — UZH SwissGov-RSD

Submission workspace for **Lost in Switzerland**: direct Apertus token scoring (B0, the paper baseline) versus difference spans with deterministic token projection (B2), on identical dev documents.

Read [STATUS.md](docs/STATUS.md), [MVP_PLAN.md](docs/MVP_PLAN.md) and the [technical report](technical_report.md). Commands are in the [root README](../README.md).

Requirements: Docker. For `make run`, an OpenAI-compatible Apertus v1.5 endpoint in `LLM_NAME`, `LLM_BASE_URL` and `LLM_API_KEY`. For measured runs, a Hugging Face account with Apertus v1.5 access and Jobs credit. No model weights are stored in this repository.

| Path | Content |
|---|---|
| `src/uzh_rsd/` | adapter, prompts, B0/B2 parsing, runner, scoring, backends, HF job + launcher |
| `manifests/s1-dev.json` | fixed nine-pair dev manifest (gold-blind selection) |
| `results/<run_id>/` | committed measured runs (raw responses, predictions, scores) |
| `tests/` | `make s1-check` (no skips allowed) |

Never use test data in development, download all splits, leak labels into prompts, fabricate measurements, or silently repair prediction lengths. Model failures stay visible in the results.
