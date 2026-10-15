# Codex local assembly contract — B3 Semantic Decision Middleware

## Goal
Assemble and empirically test the bounded B3 Semantic Decision Middleware using Nebuchadnezzar's local Q8 Apertus runtime, without changing the existing B0/B2 source artifacts or any public-city crawl. Not a new Weavr Mission.

## Coordination / first action
Inspect repository and any Observatory first; then Weavr/GitHub state following `blackmath88/weavr/docs/CHATGPT-OPERATING-CONTRACT.md`. Read installed Orca routing capabilities; use approved qualified local execution route when available. Preserve existing workers' leases, ownership and isolation. If no qualified route, run locally in an isolated worktree with explicit supervision, never pretend it was an Orca dispatch.

Read PRs #12/#13/#14, the current `track_2a/docs/SEMANTIC_DECISION_MIDDLEWARE.md`, PR #14 30-ID manifest and experiment artifacts, existing methods/adapter/contracts/evaluator, latest MVP status, and repository instructions.

## Build slice
- Branch `feat/b3-semantic-decision-middleware` is documentation-only; create isolated implementation branch/worktree from its current head.
- Use module namespace `uzh_rsd.sdm` for source code, with versioned typed task, decision and evidence schemas.
- Deterministic segmentation/alignment candidate generation. Keep offset provenance from supplied token arrays. No semantic authority in the matcher. Handle cross-language reorder, duplicates, no pair, one-to-many, missing sections and caps honestly.
- Small classifier using existing `OpenAICompatibleBackend` with a strict closed relation schema: EQUIVALENT/DIFFERENT/UNCERTAIN. Include bounded difference kinds. Never ask model for offsets, paragraphs, floating severities or a document-wide JSON list.
- Strict validation: invalid JSON, unsupported labels, wrong reference and truncation -> unresolved; no silent fallback to no-difference.
- Independent benchmark projector to exact official token lengths; freeze projection policy before reading dev scores. Logging distinguishes abstain vs predicted low score.
- Durable run directory with full manifest, call/latency/token counts, parseability, coverage, failures and hashes. Deterministic re-score without inference.

## Offline acceptance before local inference
Run existing tests, write unit tests for one-to-one/one-to-many alignments, omissions, multiple occurrences, offsets, invalid outputs, multilingual punctuation, empty documents, overflow, projection length, gold isolation, and never-invent-meaning on unknown. Provide task-count estimate with conservative local time budget; stop if infeasible.

## Local inference safety
Use only explicitly permitted local runtime `127.0.0.1:11436/v1` and pinned Q8 model; verify readiness/model identity; do not touch Morrow on `11435`. Use a bounded attempt and fixed 30-ID manifest. Stop on first systemic failure rather than silently retrying. At end stop only your Apertus server and verify port 11436 closed.

## Scientific comparison
Compare frozen B2 P0/P1 vs B3 with identical Q8 configuration and same 30 IDs. Report all IDs and missingness; per-language Spearman, macro Spearman, parse validity, full-document coverage, number of classifier tasks/calls, token usage, latency, routing failures, false negatives, and examples. If new model settings differ (such as output cap per task), declare that the methods differ and why. Do not report partial-coverage scores as full-sample performance. Keep BF16 pilot separate.

## Reporting
Commit implementation + tests + results to a new draft PR stacked on the concept branch. Leave original PRs unmerged and unmodified. Report exact commit, route, worker settlement, test counts, hashes, measured metrics, known limitations and decision whether B3 helps. If experiment cannot complete, leave an actionable, explicit checkpoint; no invented success.
