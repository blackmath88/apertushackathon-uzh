# Status — 11 October 2026

## Integrated foundation; live model work pending

Current scope: [one UZH MVP](MVP_PLAN.md), B0 versus B2. The owner authorized cleanup and integration and is arranging Apertus access.

- Implemented: pinned dev adapter, canonical whitespace tokens and offsets, strict score validation, gold/inference separation, nine-pair manifest, official evaluator parity, scale conversion and opt-in smoke check.
- Reviewed: PR #11 at `d98566f54eb0eaa5459de55e1103104c93548587`, plus the Python 3.12 test repair and cleanup in its follow-up commit. See [review evidence](CLEANUP_REVIEW_2026-10-11.md).
- Verified here: 56 tests pass, zero skips; manifest reproduces; dev contains 168 pairs per language; test split refused. Review used Python 3.12.14 / NumPy 2.3.5 / SciPy 1.17.0 / nlpstats 0.0.1 after downloaded SciPy wheels crashed. The original lock needs target-host verification; original builder results remain historical evidence in S1_EVIDENCE.md.
- **Blocked:** actual Apertus readiness. No live call, model predictions or measured model score exists. S1 runtime acceptance remains incomplete.
- **Not implemented:** B0, B2, prediction export, final Docker judge entrypoint and measured technical report. `make run` remains a synthetic demonstration.
- **Deferred:** canton pilot, B2a/B3, extra tracks and the factory trial. Older plans are retained with superseded-scope notices.

## Next actions

1. Owner configures an approved Apertus endpoint locally using `LLM_NAME`, `LLM_BASE_URL`, `LLM_API_KEY` and runs `make -C track_2a s1-smoke-live` once. Share only the redacted outcome.
2. Build the paper B0 and prediction writer from refreshed main, starting with one pair then the fixed nine pairs. Resolve official output/judge rules before declaring compatibility.
3. Add one B2 approach and compare on identical dev inputs; package and document actual results. Follow MVP_PLAN.md for acceptance and cut lines.

No Weavr state was changed or accepted by merging code. Repository integration is not a completed Mission, a waived compute Need, public release or final submission.
