# Hack Apertus UZH — submission roadmap and execution contract

Agreed scope: 7 October 2026. Target: submission-ready candidate by 15 October; recorded deadline 16 October 2026, 12:00 Europe/Zurich. Verify the current UZH-specific rules in M1.
Starting evidence: main 654b58ee131efd21e47c1aabe27f020832a97aac; scaffold only, no open PRs; issue #1 defines core MVP. No Observatory or Weavr configuration found in inspected tree. No live Weavr read tool available here; mission state is unverified.

## Current execution boundary (S1 only)
The current owner instruction restricts work to S1. Read [S1_DELIVERY_CONTRACT.md](S1_DELIVERY_CONTRACT.md) and `.weavr/staged/s1-delivery.json` for its narrowed scope, required checks and human gates. S2–S6 remain roadmap goals and are not current execution authority. The older all-stage continuity wording below is superseded by this boundary. Activation and dispatch have not been requested by this preparation.

## Product and contribution
Apertus-powered semantic difference detector for multilingual government documents, delivered as a reproducible CLI/container plus a static evidence explorer. It compares direct token scoring (B0) against sparse semantic decisions projected deterministically to benchmark tokens (B2a/B2).
The deliverable must contain real measured results, source-linked examples, honest limitations and an exact rerun path. B2 winning is not a prerequisite: a rigorous negative comparison is acceptable. A fixture-only system is not a complete submission.

## Minimum submission package
- Required track_2a layout retained; root and track-level make run invoke Docker.
- Live Apertus prediction path using LLM_NAME, LLM_BASE_URL, LLM_API_KEY; configurable bounded inference.
- Official-format prediction export and verified official evaluator adapter.
- Fixed dev comparison across EN–DE/FR/IT where available, with counts and failure accounting.
- Static local report showing paired passages, evidence, difference/uncertainty and run metadata. No application backend or hosted product required.
- One-canton pilot when authoritative paired material exists, separately labelled unscored.
- README, filled technical_report.md, sources/licenses, architecture, run manifest/results and submission checklist.
- Verify UZH-specific deliverables, report/video limits and final evaluation procedure; do not import Track 2B limits as UZH rules.
- Prepare a short demo recording script and recordable report. Prepare video if required or helpful; actual recording may need human help.
- Data directory <=100 MB; no secrets/model weights/unlicensed source content committed.
- Public/open-source submission required by official template; current repo remains private until owner authorizes visibility change.

## Dates, dependencies and exit gates
Dates are delivery targets, not scheduled automations.

| Milestone | Target | Dependency | Exit gate |
|---|---|---|---|
| S1 Contract, data and runtime readiness | Oct 7–8 | none | Rules/revisions pinned; dev loader and evaluator verified; real Apertus smoke run or explicit compute blocker |
| S2 Working B0 MVP | Oct 8–9 | S1 | Exact-length predictions and real tiny dev baseline; Docker run path works |
| S3 Semantic compiler comparison | Oct 9–11 | S2 | B2a/B2 on same manifest/model; failures and UNKNOWN explicit |
| S4 Evidence explorer and canton pilot | Oct 11–12 | S3 artifacts; corpus research may start after S1 | Inspectable local report; 3–5 authentic paired canton documents or documented availability limitation |
| S5 Validation and freeze | Oct 12–14 | S2–S4 | Frozen strategy, broader dev validation, fresh-checkout acceptance, evidence-backed limitations |
| S6 Submission candidate | Oct 14–15 | S5 | Complete submission package, release checklist and PR ready for owner |
| Human submission | Oct 16 before noon | accepted candidate | Access/publication requirements met and portal receipt retained |

## S1 — official contract and benchmark adapter
Read issue #1 and PLAN.md before coding. Verify the official template and UZH brief, including allowable models, supporting models, decomposition, metric, required output format and test policy. Record source URLs/revisions and unresolved questions in docs/SUBMISSION_CHECKLIST.md.
Pin SwissGov-RSD dataset and evaluator without downloading or opening test material. Development paths allow only train/dev and reject disallowed split before I/O.
Create exact token bookkeeping and fixed 5–10-pair dev manifest covering language pairs where possible. Gold belongs to evaluation objects, never inference input.
Reconcile similarity-to-difference conversion with existing severity 1–5 IR and schema.
Configure actual Apertus endpoint/model identity; measure one real request. Record compute availability, approximate corpus call budget and timeout/retry limits. Do not invent availability or unlimited budget.
Confirm full-document B0 fits context. Unsupported lengths are explicit failures; introduce any chunked baseline under a different name.

## S2 — baseline and reproducibility
Implement B0 faithfully from pinned baseline prompts, strict prediction validation, output export, official evaluation, failure policy and immutable run manifests.
Define commands for fixture smoke, live prediction, dev evaluation and report generation. Root make run should default to a documented small live demo when configured. Missing endpoint must fail clearly with setup guidance, never pass off fixture results as live. Explicit fixture mode remains available for offline verification.
Add Docker, dependency pins and CI for deterministic checks/container smoke. CI must not require paid inference, private credentials or test data.
Record raw model outputs safely plus derived predictions, model/revision, prompt/schema versions, decoding settings, latency, calls and token usage (mark unavailable measurements).
Retry cap: configurable, default at most two retries; record attempts and usage. No silent fallback, omission or score repair. Inference budget decisions belong to the user/configuration, not the router.

## S3 — semantic compiler
Keep CHANGE, ADDITION, OMISSION, UNKNOWN. Implement bounded alignment with traceable original token offsets; document many-to-many, reorder and unmatched handling.
Validate all model outputs independently: type, bounds, finite values, enum, asymmetric evidence and span mappings.
Project B2a binary localisation and B2 severity deterministically. Specify UNKNOWN and uncovered-region behavior separately; uncertainty cannot silently become equivalence.
Compare same manifest/model/decoding conditions. Report per-pair and macro Spearman, eligible sample count, failure coverage, calls, latency and measured usage. Report complete-case and operational failure policy transparently; never improve scores by quietly dropping difficult documents.
Gate: once comparison is credible, retain simpler/better strategy for submitted default. Keep both for reproduction.
No B3, fine-tuning, model ensemble, large taxonomy or provider shopping before core gates. Improvements after core completion are limited to observed alignment/formatting defects within existing B0/B2 scope.

## S4 — evidence report and canton pilot
Produce portable static HTML from saved run artifacts: side-by-side languages, highlights tied to original offsets, evidence details, difference kind/severity, UNKNOWN/failures, strategy/model/run IDs and source links. Keyboard-operable controls, readable contrast, responsive layout, sans serif headings, restrained color and direct labels. Escape source/model text; no executable untrusted HTML.
Report must work locally without a live model/server and distinguish official dev evidence from external unscored pilot.
Prefer Basel-Stadt only if authoritative parallel versions exist. Inspect benchmark source metadata first; no guessed canton labels.
Bound external collection to 3–5 verified related multilingual pairs from one canton. Save provenance, dates, hashes, licensing and pairing rationale. No synthetic translations presented as official versions. Record qualitative human review separately from gold metrics.
If unsuitable corpus: publish evidence of limitation in report, use real official dev examples for demo and continue packaging. Do not let corpus hunting consume the submission window.

## S5 — test plan and freeze
### Deterministic tests (every relevant change)
- Split checks happen before filesystem/network access, including CLI, cache and data adapter.
- Token mapping preserves Unicode, punctuation, repeated strings, whitespace and both sides' exact lengths.
- Projection handles start/end boundaries, unilateral spans, overlap, reorder mappings and uncovered tokens.
- Schema rejects NaN/infinity, negative/out-of-range/reversed spans, extra unsupported fields and invalid enum/score.
- Similarity/severity conversion agrees with pinned evaluator; gold -1 masking, ties, undefined constant-vector correlations and macro aggregation covered.
- Inference input excludes gold labels; cache key changes with model, prompt, schema, decoding settings and source hashes.
- Endpoint errors, timeouts, malformed JSON, truncation, retries and exhausted budgets give explicit reproducible outcomes.
- Artifact generation escapes malicious text and marks unknown/failure correctly.
### Integration tests
Fixture provider -> alignment/IR -> projection -> official-format writer -> evaluator -> run record -> HTML report.
Small fixture evaluator parity with official code. Full CLI contract and Docker from fresh checkout.
### Live acceptance
Real Apertus smoke; fixed tiny B0/B2a/B2 comparison; then a predeclared larger dev subset (target 10 pairs per language, or all available if fewer) as compute permits. Report actual count, no unsupported generalisation.
Keep tuning slice and validation slice disjoint when data permits; choose manifests before tuning. No gold-based cherry-picking.
One repeat run on a small fixed subset to quantify inference variability, with cache bypass recorded. Projection/artifact replay must be deterministic even if model calls are not.
### Regression fixtures
Include equivalent translation, numeric change, negation, modality, omission/addition, repeated phrase and reorder examples in EN–DE/FR/IT as feasible. Mark handcrafted examples synthetic and test-only. Never claim their outcomes are official benchmark accuracy.
### Freeze
By Oct 14 freeze prompt/schema/model/default strategy. Bugs may still be fixed with focused regression evidence; no new architecture.
Final benchmark test data remains untouched unless organizers explicitly define a permitted one-shot final procedure. Otherwise submit runnable inference and let official judging handle held-out evaluation. Never tune after final results.

## S6 — package and closure
Fill report from measured artifacts, including baseline parity, difference scale, uncertainty policy, data provenance, compute cost, supported languages, context limits and negative cases.
Keep exact artifact hashes and source commit for every claim. Separate measured, inferred, fixture and unavailable.
Run independent fresh-checkout Docker acceptance using documented environment variables, data preparation and model prerequisites. Check root and track-level entrypoints, prediction format and report opening.
Prepare demo script: problem -> one inspected meaning change -> typed evidence/projection -> benchmark trade-off -> limitations/reproduction.
Submission checklist must enumerate UZH-specific requirements, each with status, artifact link and verification evidence. Distinguish submission-ready package from submitted portal receipt.
Prepare final PR(s), candidate commit and release notes; owner controls merge, visibility/license decisions, publishing and portal submission.

## Claude Code routing and continuity contract
This document describes the submission goal through S6. Current work is S1 readiness refinement only; future S1 implementation requires verified canonical authority and explicit dispatch. Each later stage requires its own accepted, refined envelope and explicit next-Mission authorization. The roadmap does not dispatch Weavr or bypass human gates.
Before edits, inspect current Git/PR state and AGENTS.md; observe user changes. When Weavr project/mission exists, inspect current state and work only inside its accepted envelope. Approved Weavr writes use fresh .weavr/inbox commands. If unavailable, record unverified state rather than fabricate it; do not create new orchestration infrastructure.
Claude owns coding decisions and evidence within scope. Deterministic local tools own bookkeeping/test execution; Apertus owns runtime semantics. Supporting model usage must be documented and comply with challenge rules. Never replace real Apertus evidence with Claude-generated results.
Routing mod may select capable workers only under existing user-approved routing/cost policies. No automatic purchases, premium fallback, mission dispatch, scope expansion or integration.
Do not proceed to another milestone merely because code/evidence checks pass. Independent Codex review is advisory; human approval and integration, a pin to the resulting commit, a fresh canonical Weavr read and explicit next-Mission authorization are required. If compute blocks a required live gate, keep S1 BLOCKED; independent plumbing may continue only inside the accepted S1 scope. Later-stage docs/report/packaging are deferred.
At each milestone save docs/STATUS.md: milestone, commit/branch, changed modules, checks/results, artifact IDs/hashes, blockers and next legal step. Maintain checklist, use meaningful commits and PR evidence. Do not close parent issue until all required deliverables are verified; partial completion is explicit.
Stop dependent work for test-policy conflict, unavailable credentials/compute, provider restrictions, license constraints or required scope changes. Continue independent authorized tasks.
No automatic merge, deployment, public visibility change or final submission. These are owner decisions.

## Scope interpretation
Issue #1 remains the detailed core MVP contract. This roadmap extends delivery through a static report, validation, documentation and submission preparation. It does not authorize a production website, backend, broad crawler, agent framework or expanded research track.
The original PLAN.md 'no UI' exclusion continues to exclude application UI; the static evidence report is explicitly authorized here.
