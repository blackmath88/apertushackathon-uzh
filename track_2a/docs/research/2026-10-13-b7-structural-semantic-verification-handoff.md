# CODEX / ORCA — B7: Structural Control and Bounded Semantic Verification

**Repository:** `blackmath88/apertushackathon-uzh`

**Research objective:** Execute the complete latest Perplexity research hypothesis as a new, independently versioned **B7 experiment**.

This is NOT a rerun of B6, not a narrow model smoke test, and not an application rewrite.

B7 tests whether structural restriction, linguistic candidate selection and bounded Apertus semantic verification provide independent or complementary improvements over the unchanged B4 DiffAlign baseline.

**The central scientific requirement is causal separation:** change one mechanism at a time, preserve matched controls, and measure complete official-token ranking.

## 0 — Orientation, authority and execution

Before writing anything:

Read and follow:

- `blackmath88/weavr/docs/CHATGPT-OPERATING-CONTRACT.md`
- Current repository Observatory/Observstory state if available
- Current repository instructions and active Orca ownership
- PR #12 — submission and judge-readiness work
- PR #17 — B4 baseline
- PR #19 — B5 competitive alignment
- PR #23 — research literature and synthesis
- PR #24 — B6 negative result
- Existing pinned official evaluator and immutable 30-document development manifest

Read the original Perplexity handoff supplied in this conversation, titled:

**“B6 — Structural Control and Bounded Semantic Verification.”**

Its full eight-phase methodology is the source specification for this experiment. Use it as the research contract, with its stage labels renamed under B7.

If this handoff is not already in the repository, preserve a readable copy under:

`track_2a/docs/research/`

Do not silently substitute the earlier, narrower B7 capability prompt for this full protocol.

Use qualified supervised Orca routing where available. Verify worker isolation, ownership, resource budgets and settlement.

Create an isolated worktree and branch:

`blackmath88/b7-structural-semantic-verification`

Stack the draft PR on the current B6 scientific branch unless current repository state justifies a different, documented base.

Do not modify previous experimental artifacts, dispatch unrelated Weavr Missions, merge branches, deploy or publish anything.

## 1 — Frozen scientific facts and boundaries

Treat the following as existing measured project evidence, to be independently verified from committed artifacts:

- B4 DiffAlign macro Spearman: **0.187117**, using published Qwen3-Embedding-4B scores.
- B4 produces complete official-token vectors on the frozen 30 permitted development pairs.
- B5 competitive alignment: **NOT SUPPORTED**.
- B5's suspicious-region oracle has some correction headroom but barely outperforms random-region controls.
- B6 Semantic Risk Atlas: **NOT SUPPORTED**.
- B6 A2 hidden false-negative recall: approximately **3.207%**, versus **13.022%** for B5 routing.
- Neither B5 nor B6 executed the planned Apertus semantic-verification stage.
- Earlier local Apertus probes showed sensitivity to presentation and label ordering.

Preserve the distinction between:

- Published B4 scores
- Regenerated B5 M0 scores
- B5 structural variants
- B6 routing diagnostics
- New B7 measurements

Never silently substitute regenerated baseline predictions for published B4.

Use only the existing authorized 30-document development sample.

Do not inspect, enumerate, download or query official-test content or metadata, including filenames, directory listings, IDs or blob sizes.

No paid compute, cloud inference, fine-tuning, uncontrolled model downloads, broad prompt search, deployment or submission.

## 2 — Phase 0: Integrity and feasibility

Before implementation, produce an evidence-backed feasibility audit.

Verify:

1. The exact frozen development manifest.
2. Annotation revision and provenance, especially German annotations.
3. Official evaluator and tokenization semantics.
4. B4 published prediction hashes.
5. B5 regenerated matrix cache and character-offset mapping.
6. B6 candidate and result hashes.
7. Shared-English source-family identifiers.
8. Existing local Apertus checkpoint, GGUF hash, llama.cpp revision, tokenizer and endpoint capabilities.
9. GPU memory, runtime availability and disk headroom.
10. Existing model processes and Morrow service ownership.

Produce:

`track_2a/experiments/b7-structural-semantic-verification/FEASIBILITY.md`

Include a table:

Component | Existing artifact | Missing dependency | Cost | Decision

Specifically determine whether the CTFAlign structural scoring mechanism can consume the **existing B5 similarity matrices** without regenerating embeddings.

If that cannot be established within the frozen engineering ceiling, mark the structural arm BLOCKED or SKIPPED. Do not regenerate embeddings merely to make the experiment more elaborate.

Also inspect the latest submission-readiness state. Preserve submission-critical resources and do not interrupt active packaging work.

## 3 — Phase 1: Freeze the experiment before results

Create and commit the complete experiment protocol before new gold-aware evaluation.

Freeze:

- Exact data manifest and source-family grouping
- Structural alignment configuration
- Candidate selectors
- Target anchoring algorithm
- Candidate scoring footprints
- Context window sizes
- Candidate and model-call budgets
- Random seeds
- Tie-breaking rules
- Deterministic discrepancy checks
- Verifier prompt and output schema
- Model configuration
- Token-score update rule
- Primary and diagnostic metrics
- Minimum practically meaningful improvement
- Statistical uncertainty procedure
- All stop and escalation conditions

Compute checksums for the frozen protocol and selection artifacts.

Candidate generation and inference APIs must not accept gold labels.

Any correction after observing results must be documented as a separately labeled exploratory follow-up, not silently incorporated into the original predeclared experiment.

## 4 — Phase 2: Structural control

Test whether structural restrictions improve token ranking while holding the embeddings fixed.

Implement three comparison arms:

**S0 — Published B4 DiffAlign**

Use the original published official-token predictions unchanged.

**S1 — B5 regenerated independent-max**

Use B5's pinned, locally regenerated embedding matrices.

**S2 — CTF-restricted DiffAlign**

Apply the structural restriction mechanism from the relevant document-level word-alignment research to the **same existing B5 matrix cache**.

Requirements:

- Same encoder representations.
- Same token and character offsets.
- Same projection to official tokens.
- Same continuous-score semantics.
- One externally specified configuration frozen before scoring.
- No parameter tuning against the 30 development documents.
- No substitution of sparse links for continuous anomaly predictions.

Primary mechanism comparison: **S2 versus S1**.

Operational comparison: **S2 versus S0**.

Record correlation, per-language differences, ties, alignment failures, structural omissions, runtime and reproducibility.

Do not allow structural integration to consume the entire B7 experiment. Set an explicit engineering and runtime ceiling.

A negative S2 result does **not** cancel the independently planned Apertus capability experiment.

## 5 — Phase 3: Shared candidate pool and routing

Build one deduplicated, source-anchored candidate pool across three frozen policies.

**R1 — B5 suspicious-region routing**

Reuse the actual B5 policy and its source-token footprints.

**R2 — Equal-budget random routing**

Use seeded controls with matched eligible-token coverage and documented document/language distribution.

**R3 — Linguistic and semantic-constraint routing**

Use a small independently authored set of:

- Quantities, units, dates and temporal bounds
- Modality, polarity and negation
- Conditions, exceptions and applicability scope
- Structural absence and unmatched propositions

Learn directly from the B6 failure: simple lexical cue presence is insufficient. Prioritize actual cross-language constraint disagreement where usable anchoring exists.

Do not change B6's original result or claim this new R3 is the same method.

For every candidate preserve:

- Candidate ID
- Document and source-family IDs
- Language pair
- Original source token IDs
- Exact source evidence offsets
- Target anchor offsets
- Anchor method and ambiguity
- Risk features
- DiffAlign features
- Provenance
- Estimated and actual measurement cost

Use one shared, frozen anchoring procedure.

Allow valid, ambiguous or unavailable correspondence. Never invent a target counterpart to satisfy the schema.

Match routing policies by **unique official source-token scoring coverage**, not merely numbers of regions.

Separately account for:

- Evidence-context tokens read
- Tokens whose official scores could be changed
- Apertus model calls
- Total model input/output tokens

Deduplicate the union of all selected candidates. Where feasible, infer once and replay different routing policies from cached responses.

Do not let R3 receive larger score footprints or free extra context relative to R1/R2.

## 6 — Phase 4: Independent semantic measurements

Run deterministic constraint-discrepancy checks wherever applicable.

Optionally introduce **one** compact multilingual semantic comparator, such as a suitable NLI or quality-estimation model, only if its exact licence, checkpoint, compatibility and runtime are confirmed within the approved resource ceiling.

Do not download a collection of models for a leaderboard exercise.

Keep the compact comparator an independent arm, not a prerequisite for Apertus.

The Apertus task is a bounded assessment of correctly anchored source passages.

Allowed semantic relationships:

- Equivalent reformulation
- Different administrative commitment
- Additional or missing information
- Incorrect correspondence
- Unresolved

Preserve distinctions between:

- Obligation and permission
- Prohibition and absence of obligation
- Broader and narrower applicability
- Contradiction and asymmetric information inclusion

Require short structured outputs.

Validate evidence quotations against immutable input passages.

Do not allow generated quotations to determine official-token scoring footprints automatically.

Use controlled alternatives only when they are natural, defensible and independently checkable.

## 7 — Phase 5: Standalone Apertus capability experiment

**This phase is independent of the success or failure of structural alignment and routing.**

Create a separate, human-checkable synthetic contrastive diagnostic set across:

- EN–DE
- EN–FR
- EN–IT

Cover:

1. Changed numeric values and bounds
2. Obligation versus permission
3. Polarity and negation scope
4. Conditions and exceptions
5. Faithful paraphrases
6. Active/passive reformulations
7. Harmless sentence splits
8. Equivalent date formatting

Freeze cases, labels, review notes and scoring criteria before inference.

Use the locally deployed Apertus v1.5 8B Q8_0 GGUF on Nebuchadnezzar.

Verify the checkpoint SHA and runtime identity. Use localhost-only execution.

Test:

- Direct semantic classification
- One fixed contrastive-choice formulation where valid alternatives exist
- Reversed passage order
- Reversed answer order
- Label permutations
- Shuffled or unrelated counterpart
- Meaning-preserving controls
- Source sensitivity

Use one selected primary prompt protocol and treat alternatives as controlled ablations rather than searching for the best prompt after seeing accuracy.

Before inference, freeze numerical acceptance thresholds for semantic discrimination, order/label stability, counterpart sensitivity, false-positive rate, output validity and resource limits.

Count all prompt-prefill tokens, generated tokens, calls, latency and failed responses.

Do not assume completion label logprobs equal teacher-forced target-token likelihood.

Protect Morrow on port 11435. Verify process ownership before starting/stopping Apertus on port 11436.

If this standalone capability gate fails, mark the verifier role NOT SUPPORTED. The other deterministic arms may still complete.

Passing synthetic tests is **not** a claim of SwissGov benchmark improvement.

## 8 — Phase 6: Score projection

Implement one simple, frozen continuous score-update policy.

Requirements:

- Complete finite-score coverage for all official tokens.
- Unchanged B4 baseline outside selected scoring footprints.
- Exact source-token identity and character-offset mapping.
- Deterministic handling of discontinuous spans.
- Baseline fallback for unexamined, unresolved, invalid or timed-out model decisions.
- No silent deletion or zero-filling of difficult documents.
- No flexible supervised fusion fitted and evaluated on the same 30 records.

If supervised fitting is genuinely necessary, use source-family-separated cross-fitting and report it as a distinct experimental component.

For each candidate, separate:

- Linguistic observation
- Deterministic discrepancy
- Model decision
- Evidence validity
- Final scoring action

Never mistake a plausible passage explanation for a correctly localized token prediction.

## 9 — Phase 7: Matched evaluation

Evaluate the following where evidence permits:

| Arm | Components |
|---|---|
| E0 | Published B4 unchanged |
| E1 | S1 regenerated independent-max |
| E2 | S2 structural restriction |
| E3 | Deterministic discrepancy evidence, no Apertus |
| E4 | Optional compact semantic model, no Apertus |
| E5 | Apertus evidence shuffled within compatible strata |
| E6 | Actual Apertus judgments with identical candidates and score-update rule |
| E7 | Random versus routed Apertus selection at matched budget |

Do not label inapplicable arms as measured.

Separate routing quality from prediction quality.

Report:

- B4-missed gold-positive recall
- Total gold-positive recall
- Selected-negative burden
- Unique token coverage
- Official pooled-by-language Spearman
- Macro of per-language correlations
- Complete output and punctuation-mask integrity
- Score ties
- Per-language improvement and regression
- Shared-English-family clustered bootstrap
- Leave-one-family-out influence
- Source and presentation sensitivity
- Inference cost, latency and invalid-response rate

**The decisive Apertus comparison is actual Apertus versus identical non-Apertus and shuffled-Apertus arms**, using exactly the same candidate set and token-scoring footprint.

If Apertus improves synthetic semantic classification but not complete-document official ranking, report that as capability evidence with no benchmark uplift.

Do not rescue a negative comparison by post-hoc prompt, threshold or fusion tuning.

## 10 — Phase 8: Blinded diagnostic audit

After predictions are frozen, draw a small predeclared sample of:

- Model-predicted discrepancies absent from official positives
- Gold-positive differences missed by all methods
- Random controls

Hide method identity and predictions from reviewers.

Annotate:

- Semantic difference supported / unsupported / unresolved
- Correspondence valid / invalid
- Context dependency
- Localization difficulty
- Minimal original-source evidence
- Practical materiality, separately

Do not overwrite official gold labels with review judgments.

Record disagreements and unresolved cases rather than forcing a binary verdict.

## 11 — Scientific decisions

Apply these interpretations:

- **Structural scoring helps:** retain S2 as a comparator.
- **Linguistic routing helps, Apertus doesn't:** retain the deterministic contribution; reject the current model role.
- **Apertus helps, routing doesn't:** retain the verifier hypothesis and reject the router.
- **Apertus semantic judgments work but token ranking regresses:** investigate projection rather than adding prompting.
- **Real Apertus equals shuffled outputs:** no demonstrated incremental semantic information.
- **All experimental arms fail:** preserve B4 as an unchanged benchmark baseline and report B7 NOT SUPPORTED.

Do not claim support from a small synthetic benchmark alone.

## 12 — Deliverables

Create a dedicated B7 experiment package:

`track_2a/experiments/b7-structural-semantic-verification/`

Include:

- `FEASIBILITY.md`
- `PROTOCOL.md`
- Frozen protocol and source hashes
- Candidate/evidence schema
- Frozen candidate manifest
- Synthetic contrastive diagnostic with provenance
- Executed arm results and missing-arm explanations
- Exact reproducibility commands
- Cost/resource evidence
- Results table with uncertainty
- Blinded error audit
- `REPORT.md`
- Evidence checksums

Tests must verify:

- Forbidden test-split access
- Stable original-token offsets
- Gold isolation in generation
- Deterministic reruns
- Baseline preservation
- Correct fallback
- No reduction in required-token coverage
- Correct shuffled-evidence ablations

Run all existing and new tests.

Open a separate **draft PR** stacked on B6 PR #24. Do not merge.

Report Orca route, worker settlement, base/head commits, artifacts, checksums, exact tests passed, actual model-call count and scientific verdict.

## 13 — Submission protection

Submission deadline: **October 16, 2026, 12:00 CEST**.

Before model work, check whether submission packaging has outstanding critical blockers.

Do not touch or rerun the official held-out test split as part of B7.

Do not confuse published B4 Qwen DiffAlign performance with an Apertus-specific result.

If submission readiness conflicts with B7, preserve the submission. Document any unexecuted B7 arms rather than expanding the budget.

**Execute the full scientific B7 programme with independently testable arms, predeclared resource ceilings, and honest stop conditions. Do not replace negative measurements with further architecture development.**