# S1 delivery contract — Hack Apertus as Faictory's first real trial

Status: proposed, staged, not activated and not dispatched.
Issue: #2. Machine-readable preparation: `.weavr/staged/s1-delivery.json`.
This file refines S1. It does not authorize S2–S6 or grant runtime authority.

## Outcome and ownership

Prepare the official UZH contract, train/dev benchmark adapter, canonical token bookkeeping, a fixed dev manifest, evaluator/scale parity and one real Apertus readiness request. A full B0 baseline belongs to S2; B2 belongs to S3; the Basel-preferred canton pilot belongs to S4.

Weavr owns Project intent, Mission contracts, Needs and legal progression.
Faictory owns the pinned workspace, implementation attempts, captures, proposals and delivery evidence.
Claude implements. A separate Codex attempt independently reviews the exact candidate and executes its own checks. Human approval, human integration and explicit next-Mission authorization remain separate actions. A Faictory approval is evidence for Weavr, not automatic Mission acceptance.

The preparation packet is a repository-local handoff format. It is not a new Weavr/Faictory API schema. Do not POST it as an execution envelope or treat its fields as native runtime enforcement.

## Activation prerequisites

An authenticated operator must first read canonical Weavr state, match/reuse the repository Project and inspect existing Missions, Needs and Runs. GitHub issue status and this staged file are not that state.

Verify deployed Mission validation, ingress configuration, runner repository access, Claude builder availability and independent Codex review availability. Prove that the Faictory workspace/attempt/capture/evidence path is actually used; a normal Weavr coding run in this repository alone does not prove Faictory integration.

Faictory main currently has the Claude implementation path. Its evaluation baseline (#16) and review domain (#15) remain open; #15 depends on the superseded baseline. The native Codex reviewer and connected execution/evidence bridge remain unverified. Reconcile/validate those capabilities in separately authorized factory work before claiming this complete trial ready.

Only S1 has a future-intake command template. S2–S6 are deferred roadmap inventory, with their existing broad contracts requiring later refinement. Do not copy all six into the inbox. Any authorized materialization creates a fresh immutable command ID; activation is distinct from dispatch. No activation or dispatch is requested by this refinement.

## Pinned execution and exact write boundary

At activation, inspect the current target branch and accepted preparation revision, resolve the authorized base SHA and bind the Weavr envelope and Faictory workspace to it. The inspected SHA in the packet is historical evidence, not an automatic execution base. Preserve user changes.

The exact allowlist is in both the S1 Mission's `scope.writePaths` and the preparation packet. It permits only:
- the train/dev adapter, token mapping, evaluation/scale modules and minimal Apertus smoke module;
- existing CLI/split/kernel/schema files only for adapter wiring and scale reconciliation;
- `test_s1_*.py`, explicitly synthetic S1 fixtures, the existing scaffold regression suite and a tracked S1 dev manifest;
- track-level dependency pins/Makefile and the named source, benchmark, status, evidence and submission-checklist documents.

It excludes root Makefile/README, workflows, Docker files, orchestration configuration, broad `track_2a/**` authority and later-stage implementation. The builder may read this contract and staged metadata but may not modify them. New filenames outside the allowlist require a revised envelope and human decision; a reviewer cannot widen it.

Raw downloaded train/dev data and model outputs live outside the tracked source proposal, in ignored `track_2a/data/` and `track_2a/runs/` or the Faictory artifact store. They require separately recorded execution/artifact authority; source path permission alone does not grant that authority. Never download all splits. Track only the selected manifest and safe evidence references/digests.

## Required implementation and validation

| ID | Deliverable / required evidence |
|---|---|
| S1-RULES | Official template/UZH requirements, dataset/evaluator revision and applicable licenses pinned with exact URLs/content or commit hashes; unresolved rules recorded as Needs. Existing benchmark notes are hypotheses until verified. |
| S1-SPLIT | Loader, CLI and cache paths allow only train/dev. Tests use filesystem/network/cache spies and demonstrate rejection before any I/O, including invalid split strings and absent paths. Do not fetch/iterate all splits or inspect held-out records. |
| S1-TOKENS | Official token order and both sides' offsets preserved across Unicode, whitespace, punctuation and repeated tokens. Official output lengths exact; mismatch fails, with no padding/truncation. |
| S1-MANIFEST | Fixed 5–10 dev pairs, selected before experiments, with IDs, revision, source hashes and actual EN–DE/FR/IT counts. Missing availability stays a Need. Gold is confined to evaluation and never serialized into inference inputs. |
| S1-EVAL | An explicitly synthetic fixture agrees with the pinned official evaluator; cover -1 masking, ties, undefined constant vectors and language/macro aggregation. Do not claim parity using only our own implementation as oracle. |
| S1-SCALE | Explicit similarity-to-difference mapping and internal severity reconciliation, tested against the pinned representation. Kernel edits are limited to this reconciliation, not S3 alignment/UNKNOWN work. |
| S1-RUNTIME | Minimal opt-in module uses configured LLM_NAME/LLM_BASE_URL/LLM_API_KEY, validates the actual returned Apertus identity and records safe settings/latency/context/budget evidence. Mocked responses never establish live readiness. |
| S1-REVIEW | Separate Codex attempt checks the exact immutable candidate/diff, reruns required commands in isolation and cites logs/artifact digests for each criterion. Builder self-report is not independent evidence. |

Required commands are specified in the preparation packet. The S1 test modules are implementation deliverables, not tests claimed to exist today. Record discovered test names/counts: an exit-0 command discovering zero tests cannot satisfy a requirement. The existing `make test` has only four scaffold tests.

The CLI test-split invocation must exit nonzero. That refusal alone does not prove rejection before I/O; the dedicated spy tests must do so. The official parity fixture and real smoke require additional observed evidence beyond a green scaffold suite.

Real smoke: one logical request, no automatic retry by default. Resolve an approved endpoint, returned model identity, context limit and budget before calling. Any retry/cost ceiling must come from approved runtime configuration. Never print keys, authorization headers or secret-bearing URLs in reports/logs. Absent usage measurements remain unavailable. A blocked smoke produces a precise Need and pending rerun instruction.

## Evidence, proposal and recovery

The closure packet binds repository, Mission/intent revision, workspace base, candidate commit, diff digest, changed paths, builder/reviewer attempt identity and check commands/exits/log digests. Include manifest hash, dataset/evaluator revisions, model identity, criterion-level evidence, findings and unresolved Needs.

Capture the Claude attempt before proposing. Independently verify/review the captured digest. Any repair creates a new bounded attempt and capture; rerun the relevant checks and review for the changed commit. Do not reuse stale evidence after edits.

A timeout/cancelled attempt submits no successful result; retain partial artifacts and confirmed termination status. An orphan must block continuation until explicit reconciliation; never blindly replay it. Exercise recovery with fake/local fixtures, not extra paid smoke requests. Link the observed factory recovery evidence and remaining limitations in S1_EVIDENCE.md.

## Human gate and stage order

Codex returns PASS, REVISE or BLOCKED:
- PASS: every required S1 criterion is supported, including real Apertus readiness, and no blocking Need remains. PASS is a recommendation only.
- REVISE: a demonstrated fix is possible inside the same envelope; propose the exact bounded repair.
- BLOCKED: missing live access, official parity/provenance, license/rule decision, independent review or control-plane capability. Preserve partial results; never turn a documented compute blocker into a passing live criterion.

A human reviews the exact proposal and decides. Human integration must identify its resulting commit and preserve evidence linkage. A squash/rebase or material integration change requires evidence remapping/reverification; never pretend the original candidate SHA is the integration SHA.

S2 starts only after explicit human S1 approval AND integration, required gates satisfied, canonical Weavr state reread and explicit next-Mission authorization. Pin the new workspace to the integrated commit. Merely passing unit tests, returning PASS or listing contracts in order cannot start S2.

Native Weavr dependency enforcement is unverified. This is an operator/repository gate; do not advertise it as a backend-enforced scheduler. If the runtime cannot enforce the required authority or stage boundary, report the blocker and stop; do not implement a new orchestrator inside this benchmark repo.

## Outside this test slice

No B0 corpus run, B2 implementation, canton collection, report UI, Docker/submission package, provider expansion, automatic fallback/merge/deploy or portal submission. The owner reports mobile install and JSON handoff merged. Background notifications remain unfinished and are excluded from this delivery trial.
