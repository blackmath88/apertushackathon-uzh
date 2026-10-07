# Status

## S1 — contract, data and runtime readiness

- **State:** implemented; **BLOCKED on live Apertus smoke** (no endpoint credentials). Awaiting independent review and owner decision.
- **Branch / commits:** `claude/quirky-babbage-wi047n`; implementation `e907ad2`, evidence docs in the following commit (see the PR head).
- **Changed modules:** `splits.py`, `tokens.py` (new), `data_adapter.py` (new), `evaluation.py` (new), `severity.py` (new), `apertus_smoke.py` (new), `cli.py`; tests `test_s1_*.py` plus synthetic fixtures; `manifests/s1-dev.json`; `Makefile`; `requirements-s1.lock`; docs.
- **Checks:** fresh clone, `make s1-check`: 56 tests OK, 0 skipped, manifest reproduces, test split refused; also passes under the official numpy/scipy pins. Details in [S1_EVIDENCE.md](S1_EVIDENCE.md).
- **Artefacts:** manifest `manifest_sha256` `61e0e98b7a9347716f4a71bc002364a600993c7346d6046e4f8d65899059a835`; dataset `ZurichNLP/SwissGov-RSD@f16aa0536811b8c0cf975fede21eec5996e4b3c1`; evaluator `ZurichNLP/SwissGov-RSD@1807a42100e742ed03d337c54c4b9ea86995f565`.
- **Blockers:** N-COMPUTE-1 (Apertus endpoint, model id, budget); N-RULES-1…5; N-LIC-1.

## How to reproduce

```bash
cd track_2a
make s1-setup      # ignored .venv with nlpstats/numpy/scipy
make s1-fetch      # dev files + pinned official evaluator files (no test data)
make s1-validate   # dev counts and token totals
make s1-check      # full suite (no skips allowed), manifest rebuild, test-split refusal
make s1-smoke      # writes a BLOCKED record unless configured; sends nothing
# with an approved endpoint:
export LLM_NAME=swiss-ai/Apertus-v1.5-8B LLM_BASE_URL=https://… LLM_API_KEY=…
make s1-smoke-live # exactly one request; record in runs/ (ignored)
```

## Next legal step

1. Owner provides or approves an Apertus endpoint, then runs `make s1-smoke-live` once. Attach the redacted record to the PR.
2. Independent Codex review of the PR head.
3. Owner approves and integrates S1. S2 (B0 baseline + Docker) starts only after integration and explicit authorization. **S2 has not been started.**
