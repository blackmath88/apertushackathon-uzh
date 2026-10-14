# Local Codex / supervised Orca handoff — B5 rank tomography first

Date: 2026-10-13. Owner intent: execute a bounded, scientific next experiment. This document is an **execution handoff**, not a Weavr Mission command, dispatch or accepted Plan.

## Orientation (mandatory)

- Follow `blackmath88/weavr/docs/CHATGPT-OPERATING-CONTRACT.md`.
- Inspect current UZH repository, Observatory if present, PRs #12–#17 and any newer concurrent PRs, active Orca ownership, and existing local worktree. Read repository instructions. Read two archived original reports and synthesis under `track_2a/docs/research/`.
- Read `track_2a/experiments/b4-alignment-first-sdm/report.md`, B4 oracle/alignment code, frozen 30-ID manifest, evaluator, B3/B2 stored run evidence, `track_2a/docs/JUDGE_READINESS.md`, submission checklist.
- Route through qualified Orca if available; the previously used `orca-cli` + supervised orchestration fallback is acceptable only after verifying supervision/stop/settlement/isolation. No misleading “worker registered” assertion or unowned background job.
- Establish new isolated implementation branch/worktree from this research branch. Avoid rewriting/updating existing draft PRs or frozen artifacts.

## A. Freeze a gold-blind router — BEFORE gold-aware metrics

Implement `uzh_rsd.b5_tomography` or equivalent, with unit tests, versioned manifest and deterministic CLI.

1. Read the same 30 dev IDs B4 used and the exact published DiffAlign prediction vectors; the test split must be refused before any test file IO.
2. Use no gold in router functions (ideally structurally separate gold-free selection from oracle/evaluator). Freeze stable selection config, selected windows and checksum manifest in a commit **before** computing oracle results.
3. Routers: top anomaly, local peak, high gradient, repeated structured value, low-context support, uniform seeded random. No inferred counterpart edges from score-only cache.
4. Budgets: 1/3/5/10 non-overlapping official-token windows per document; exactly width 3 except clipped boundaries. Treat both document sides and official punctuation mask consistently. Freeze tie-breaks and random seeds. Record unique EN parent groups across DE/FR/IT for bootstrap.
5. First run: route-only dry run (no gold): document IDs, selected-window counts and input SHA. Inspect for any router implementation bug **before** gold analysis; if corrected, commit a new documented policy revision.

## B. Run gold-isolated rank-error tomography

No LLM or paid compute. Use existing evaluation semantics for pooled per-language Spearman.

Compute: gold and prediction midranks, signed/squared rank residual diagnostics, reach of gold-positive/under-ranked-positive/over-ranked-zero tokens, squared-rank-error mass, random percentile and per-EN-parent breakdown.

Implement two **separately labelled** diagnostic corrections on identical frozen windows:
- Idealized exact-gold replacement at selected positions (not deployable; upper diagnostic).
- Restricted-offset `[-1,-.5,-.25,0,.25,.5,1] × language prediction standard deviation`, per-window constant, maximum three coordinate passes chosen with dev gold (optimistic attainable-within-heuristic-search diagnostic, **not a true upper bound**). Explicit score bounding/clipping and stable tie behavior.

Produce same-budget seeded random controls, original DiffAlign and gold-oracle sanity controls. Record all 30 documents and language breakdown.

Apply predeclared **3-window** decision gate from `B5_RESEARCH_SYNTHESIS_AND_DECISION_PLAN.md`. Never change the gate after seeing results. Expected baseline macro 0.187117 must be independently reproduced rather than assumed.

- CONTINUE only if restricted-offset gained >= +0.02 macro; beats random 95th percentile in >=2 languages; reaches under-ranked positive *and* over-ranked zero cases; no one EN parent drives >50% of gain.
- REJECT if gain < +0.01 or fails random or dominated by one language/parent.
- Otherwise INCONCLUSIVE. If any criteria are contradictory, mark INCONCLUSIVE, explain; do not cherry-pick.

Preserve full manifests, checksums, source revisions, scripts, analysis tables and 3 failure examples. Include grouped bootstrap uncertainty where computationally feasible.

## C. Embedding/correspondence feasibility — independent of A

Read-only inspect B4 caches and pinned upstream implementation to establish whether same-embedding candidate matrices/argmax links can be obtained. If not available, record honest regeneration hardware, time, model/checkpoint/rights and source proof. No implicit large downloads.

If **already available** under safe resources and A supports continued work, optionally implement the minimum matched-input ablation: original independent max, reciprocal cycle/mutual match, NULL-aware capacity control. Preserve one-to-many as a diagnosed limitation. Do not introduce POT, HMM, or wide search by default.

## D. Apertus inference — gated, not automatic

No Apertus calls solely because the oracle's idealized gold replacement shows headroom.

After A CONTINUE and real counterpart alternatives are verified, use a small unscored/training smoke set to compare:
- Contrastive 3-option best/alternative/NULL.
- Pairwise relative semantic ranking of two candidate anomalies.

Use single-token candidate probabilities (verify pinned llama.cpp behavior); controlled option order/label permutation; no rationale or generated source offsets. Pick **one** full protocol before main 30-pair run.

Cap proposed full run at either <=180 calls (contrastive) OR <=360 calls (tournament), plus explicit walltime budget. Before model start, assess submission readiness and potential schedule conflict. No paid compute, HF jobs, test access, automatic retries, alternate models, new Weavr Mission, publishing third-party pages, or changing Morrow.

If inference is run: localhost Apertus :11436 only, pinned model hash; verify process identity and stop only owned process, Morrow :11435 remains unchanged; supervisor must confirm worker settlement.

Run deterministic / shuffled / constant / identical-candidate Apertus ablations. Only count **incremental full-sample improvement** above no-Apertus deterministic controls as support.

## E. Delivery and decision

Run all existing and new tests; refuse official test split; checksum frozen original runs; reproduce from saved artifacts without inference.

Commit code/tests/evidence in an independent branch; open draft PR stacked on this research branch. Do not merge.

Return:
- exact route/worker/settlement and source/base/head;
- source hashes and test count;
- full router reach and oracle correction table for 1/3/5/10 windows;
- EN-grouped uncertainty, random controls, per-language scores;
- A verdict and stop/continue decision;
- embedding availability and measured/estimated resource costs clearly distinguished;
- whether any Apertus experiment happened and its ablation (if not, explicit “not run”);
- current judge/packaging blockers and honest submission recommendation.

**First deliverable is A+B complete. Never treat optional C/D as a reason to delay delivering A+B.**
