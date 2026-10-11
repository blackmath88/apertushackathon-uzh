# Lost in Switzerland — UZH SwissGov-RSD

Hack Apertus 2026 · Track 2A · one submission, one measured B0/B2 comparison.

**Question:** does asking Apertus for meaning-changing spans, then projecting them onto tokens, work better than asking it to score tokens directly?

## Current state

The dev-only adapter, token bookkeeping, fixed nine-pair manifest, evaluator and opt-in Apertus smoke check are implemented. **There are no real model predictions or benchmark results yet.** The owner is arranging Apertus access.

`make run` still runs a synthetic scaffold example. It is not the final Docker judge entrypoint.

## Start here

- [Current MVP plan](track_2a/docs/MVP_PLAN.md)
- [Status and verification](track_2a/docs/STATUS.md)
- [Submission checklist](track_2a/docs/SUBMISSION_CHECKLIST.md)
- [Challenge brief](docs/challenge-source/CHALLENGE.md)
- [Source provenance](docs/challenge-source/source.json)

## Verify the foundation

```bash
make -C track_2a s1-setup
make -C track_2a s1-fetch s1-validate s1-check
```

The recorded lock was originally checked on Python 3.13. The review also checked the suite using Python 3.12 and the runtime's installed scientific libraries; see the review record for the environment limitation.

Only pinned dev files are downloaded. Never fetch all splits or use test data during development.

Once an approved Apertus endpoint is configured locally with `LLM_NAME`, `LLM_BASE_URL` and `LLM_API_KEY`:

```bash
make -C track_2a s1-smoke-live
```

This sends exactly one request. Keep credentials out of commits and shared logs. A successful smoke check establishes endpoint readiness, not benchmark performance.

## Submission focus

Build B0, B2, comparable predictions and measurements, Docker execution and the technical report. A small viewer from real results is optional. Canton collection, B2a/B3, additional tracks and the Weavr/Faictory trial are deferred from this submission path.

Repository integration does not accept a Weavr Mission or waive a Need. Staged governance material remains historical preparation, with no new dispatch authorized. Publication and final portal submission remain separate owner decisions.
