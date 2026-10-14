# Nebu handoff — full-development Apertus paper baseline

Date: 14 October 2026 (Europe/Zurich).
Status: prepared for the owner to hand to local Codex on Nebuchadnezzar. This document does not dispatch a worker or start inference.

## Outcome

Establish a reproducible reference score for the paper's prompting baseline using the existing local Apertus runtime on **all permitted SwissGov-RSD development pairs**, evaluated against development gold with the pinned official evaluator. Deliver configuration, manifest, immutable raw responses, predictions, failure accounting, scores and runtime accounting.

This is the full-development baseline, NOT a full-dataset or test-set run. Do not access, enumerate or inspect protected test content or metadata. Do not use the previous final-test failure outputs to tune anything.

The owner reports that B8 is currently running. That is user-reported state, not independently verified here. No B8 PR was returned by the GitHub search at preparation time; absence of a PR is not evidence of settlement.

## Scope and authority

When the owner hands this task to Nebu for execution, implement the minimum runner hardening needed and execute one local baseline over the frozen dev manifest after B8 has positively settled. Preparation can proceed in an isolated worktree meanwhile.

- Existing installed local Apertus only; no paid/cloud inference, new model downloads, training or external data uploads.
- One inference request at a time, no competing GPU inference.
- No B8 changes, cancellation, runtime restart or reconfiguration while B8 may be live.
- Do not alter Morrow or use its unrelated service as a fallback.
- No merge, deployment, submission, organiser contact or Weavr Mission dispatch/Need waiver.
- Follow repository instructions and blackmath88/weavr/docs/CHATGPT-OPERATING-CONTRACT.md. Inspect actual Weavr state if governed ownership applies; unavailable live state is not permission to override claims.
- Candidate-method comparisons, output-cap variants and B8 expansion are follow-up work, not automatic additions to this baseline.

## 1. Orient on the actual host

Read AGENTS.md and relevant nested instructions, fresh Observstory/Observatory state if present, current GitHub PRs and local dirty/worktree state. Inspect B8's real process, ownership and completion evidence. An idle GPU or missing PR alone is insufficient.

Relevant evidence:
- PR #12: original B0/B2 pilot and judge/final workflow.
- PR #25: B7 structural comparator and failed Apertus verifier.
- PR #26: next-day handoff.
- track_2a/technical_report.md on feat/b0-b2-mvp.
- track_2a/diagnostics/20261012T062327Z-ff965461/audit_supplement.md.
- track_2a/docs/NEXT_EXPERIMENT_PROTOCOL.md: historical smaller cloud comparison, NOT the protocol to execute unchanged.
- track_2a/docs/research/NEXT_DAY_HANDOFF_2026-10-14.md.

Choose and record an exact implementation base after inspection. The docs branch's ancestry is not a requirement to execute its code; newer runner work may live elsewhere. Do not merge scientific branches merely to obtain a runner.

## 2. Preserve what we already know

A real B0 baseline was executed on nine dev pairs with Apertus v1.5 8B BF16 on L40S:
- B0 parseable 3/9, strictly valid 0; B2 parseable 9/9.
- Matched macro 0.136 vs 0.138, all three matched pairs from ONE English source.
- B0 all-document zero-fill sensitivity macro 0.268; the report diagnoses a between-document offset. Do not present this as evidence of strong semantic judgment.
- B2 used about one fifth of B0 generation time/completion tokens on that pilot.

These are legitimate pilot results, not a full-dev baseline. Preserve all prior results byte-for-byte. A new local Q8 run is a distinct model/runtime configuration and must not be labelled a direct BF16 replication.

## 3. Freeze the protocol BEFORE inference/scoring

Write a versioned protocol and run intent on an isolated implementation branch and record their commit/hash.

### Model and runtime

Verify the actual local GGUF hash, model identity, quantisation, llama.cpp revision, chat template, context capacity, decoding and endpoint. Historical reference only: Apertus v1.5 8B Q8_0, GGUF sha256 dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d, llama.cpp 7ab4ee7, loopback port 11436. Verify rather than assume these remain current. Report endpoint-advertised identity separately from weight attestation.

Use the existing runtime only after B8 settles. Keep model, runtime, prompt and decoding fixed for the entire run. Context overflow is an explicit failure; never silently truncate inputs.

### Dataset

Use pinned explicit dev-only files/endpoints; avoid whole-repository/dataset downloads that include test. Build a deterministic manifest of EVERY permitted dev pair, with language, stable ID, original order and hashes. Apply only exclusions required by the pinned official evaluation contract; list excluded IDs and reasons. No short-document filter, score-based selection or successful-response filtering.

Verify actual split definitions/counts locally; do not infer counts from the challenge's 224-document headline. Preserve any upstream dev/train and dev/val membership and existing experimental exposure records. This baseline does not create a fresh holdout, and the full dev score is descriptive after repeated development.

Gold annotations must not enter prompts, example selection or inference inputs. Load dev gold only in the scoring stage after raw generation is frozen. Retain official token identity and offsets.

### Paper method and deviations

Inspect pinned upstream paper-baseline code/prompts against the repo B0 implementation. Reuse pinned templates, few-shot examples, similarity-to-difference mapping and upstream parsing semantics. Document exact differences before launch.

Existing B0 reported deviations include token-list rendering/non-ASCII handling, safe literal parsing instead of eval, treatment of model punctuation labels, and backend/chat-template settings. Resolve faithfully where safe, or explicitly retain and name each deviation. Do not execute model output with eval.

Freeze greedy decoding and the paper's original output budget after verifying it (the earlier B0 used 4096 new tokens). Do not enlarge output allowance or repair JSON midway. An enlarged-budget/repair arm is a separately named future experiment.

### Failure/scoring contract

Check the actual pinned evaluator and parser; do not assume an earlier protocol's description is authoritative. Before launch define:
- how missing token labels, malformed documents, transport failures, truncation and context overflow are represented;
- the all-manifest scoring convention and whether it is an upstream reproduction or a declared sensitivity convention;
- handling of constant vectors/undefined correlations;
- exact coverage denominator and required output lengths.

Keep failure status separate from numeric fallback predictions. Never label zero-filled or incomplete documents as successful model output. If the official tooling cannot score missing cases, report that limitation; any all-manifest fallback score must be explicitly labelled. Matched/available-only scores are secondary and must never silently replace the all-manifest report.

Do not promote the older 0.268 fallback score into the new baseline reference or tune failure conventions to improve correlation.

## 4. Harden the runner without changing the model method

Reuse the existing pipeline; no general orchestration rewrite.

Meaningful synthetic checks must cover:
- pinned dev-only access and refusal of test before I/O;
- inference-input isolation from labels;
- official token identity, ordering and vector lengths;
- raw-output durability, integrity and failure accounting;
- interrupted-run/resume behaviour;
- one-request concurrency and timeout;
- scorer parity against the pinned official evaluator.

Use synthetic prompts to verify endpoint compatibility before the real run. Synthetic infrastructure checks do not count as semantic acceptance.

Persist intent before each request and raw response/status immediately afterwards. Resume only never-started items under identical configuration. Do not automatically resend an interrupted/possibly-live request. Establish settlement first; retain an unresolved item as such rather than fabricating a response. Transport/runtime failure should checkpoint and pause for diagnosis; returned malformed model outputs are recorded and do not justify repair/retry.

Before launch, set explicit per-request and total wall-clock limits from the actual context/output bounds and observed local throughput, with conservative headroom. Record the numeric limits and enforce them. If the limit interrupts the run, report INCOMPLETE and preserve evidence. No self-extending retries. Runtime estimates are estimates, not a promise of completion.

## 5. Execute after B8 settlement

Commit protocol, manifest and run configuration before generating model responses. Run one baseline pass with immutable run ID. Verify that no competing inference or runtime mutation is present.

Log progress by attempted/completed/failed/unstarted counts and elapsed time, without dumping source text into public logs. Keep raw dev-text artifacts private under existing publication rules; commit code, hashes and text-free summaries. Do not assume repo privacy or permission to publish source text.

## 6. Report and acceptance

Deliver a concise report with:
- exact code/model/runtime/prompt/config/manifest hashes;
- intended/attempted/returned/unstarted counts;
- parseable vs strictly valid counts;
- malformed/truncated/transport/context failures and token fallbacks;
- per-language and macro official Spearman under the frozen convention;
- secondary available-only scores with denominators;
- completion/input tokens where observable, total wall time and request latency;
- deterministic re-score/integrity verification;
- split/exposure limitations and all deviations;
- reviewer status: self-review unless a real independent review occurred.

Distinguish RUN FINISHED (every intended item accounted for) from COMPLETE MODEL PREDICTIONS (every required prediction usable without undisclosed fallback). Poor accuracy or many format failures do not invalidate the experiment; hiding them does.

Acceptance:
1. All permitted dev pairs appear exactly once in the manifest or in a justified official-exclusion list.
2. The frozen configuration is verifiable; no gold enters generation.
3. Every attempted request has durable provenance/status; no silent retries or result overwrites.
4. Scores reproduce under the frozen official-evaluator contract, or an explicit blocker explains why they cannot.
5. Coverage, failures and runtime accompany every headline score.
6. B8, prior evidence, test data, Morrow and publication boundaries remain intact.

Return a draft PR/handoff with exact commit, report location, status COMPLETE/INCOMPLETE/BLOCKED and the next smallest action. No automatic merge.

## Subsequent comparison — not part of this run

Once the baseline exists, evaluate a frozen Apertus candidate on the identical manifest, local model/runtime and scoring contract. Compare accuracy, coverage and cost. The existing Qwen-based B7 structural score is a separate comparator. Existing B8 results are comparable only where all relevant conditions actually match.

The purpose is a stable scientific reference, not a guaranteed higher score.
