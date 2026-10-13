# Next-day handoff — 14 October 2026

Status: **decision record for tomorrow; not an instruction to launch tonight**.

## Immediate priority: make UZH submission executable and compliant

Deadline: **16 October 2026, 12:00 CEST**. Tomorrow, first inspect current repo/Observstory if present, latest PRs and owner decisions, then audit official input/output and judge endpoint requirements, final prediction completeness, publication/licence conditions, team/report status and clean Docker execution. The last recorded B2 final run had only **88/168 parseable responses**; do not mistake this for complete accepted predictions. Check newer evidence before treating any blocker as still open.

Submission repairs should be bounded, isolated and verified. **Do not inspect the protected test split (including path metadata) in development, re-run final inference, initiate cloud spend, merge or submit without separately confirmed authority.** The local B4/S2 Qwen embedding baseline alone does not establish the required Apertus contribution.

## Independently review the promising B7 structural result

From [draft PR #25](https://github.com/blackmath88/apertushackathon-uzh/pull/25), examine B7 report, implementation and pinned upstream CTF source against frozen B5 matrices and original evaluator.

Observed:
- Published B4 macro Spearman 0.187117 (Qwen DiffAlign, no Apertus).
- Regenerated B7 S1 0.188300.
- **CTF-restricted B7 S2 0.215422**, +0.027122 vs same-matrix S1, CI95 [0.008329, 0.046366], leave-one-English-family-out positive.
- All 18,485 eligible official tokens covered; no new embeddings.

Review continuous scoring semantics, CTF width-8 policy/predeclaration, offset integrity, the source family bootstrap, reproducibility and mismatch between regenerated S1 and original published B4. This is a supported **structural comparator**, not a validated Apertus submission and not a mandate to integrate it.

## Next research hypothesis (separate, post-submission by default)

**Does providing full, human-reviewed source-anchored propositions improve Apertus's semantic judgment stability and accuracy over B7's token-centered fragments?**

B7 verifier was **NOT SUPPORTED** under frozen synthetic capability criteria: primary accuracy 0.7917 (<0.80); label-permutation stability 0.5417 (<0.85), though output validity was 100%. Its actual model evidence exceeded shuffled evidence by +0.006378 macro on B7's fixed R1 cases, but that does not override gate failure. The blinded 15-case audit found 9 invalid correspondences, 0 supported, 6 unsupported and 9 unresolved semantic discrepancies. These are preliminary diagnostic signals, **not proof** that context repair solves instability.

Potential B8 later:
1. Freeze a human-reviewed sample of genuinely corresponding complete propositions **before** model scoring; no gold-driven sample adjustment.
2. Hold GGUF `dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d`, llama.cpp `7ab4ee7`, labels, scoring and cases fixed.
3. Compare token-centered B7 evidence vs complete sentence vs sentence + governing heading/condition.
4. Counterbalance passages and labels; test source/counterpart ablation, unrelated-source controls, faithful paraphrase, multi-sentence exception scope and abstentions. Validate textual evidence and offsets.
5. Independently report semantic judgment quality versus official token projection/ranking, alongside cost and per-language differences.
6. Freeze protocol, thresholds and budgets *before* inference. No prompted retuning on the same sample or unapproved final/test access.

**Do not launch B8 or broad model work simply by opening this handoff.** Plan/accept separately, preserve B7 negative verdict, and avoid a new middleware rewrite.

## B8 additional research option — frontier teacher → local Apertus transfer (post-submission)

**Hypothesis:** A frontier model can reveal which evidence representation and task decomposition make multilingual semantic judgments reliable; the useful representation or decision contract can then be tested on locally deployed Apertus **without the frontier model at inference time**.

This is a proposed **development-time teacher / student diagnostic**, not a mandate to run a frontier service, distill private reasoning traces, or automatically optimize prompts. It complements the proposition-context experiment above rather than replacing it.

### Experimental sequence (requires separate approval and budget)

1. **Teacher ceiling.** Freeze approximately 20–30 human-checked EN–DE/FR/IT proposition pairs containing material differences and faithful paraphrases, stratified by modality, negation/scope, deadlines/quantities, conditions/exceptions and omissions. Check provider terms, permitted data processing and rights before sending any texts externally; do not transmit protected SwissGov test data or rights-restricted private government captures.
2. **Evidence representations.** On identical cases compare R0 token-centered B7 evidence, R1 complete aligned sentence, R2 sentence plus governing heading/condition, and R3 independently validated structured semantic commitments (actor/action/modality/polarity/condition). Hold case identity, gold-independent selection and scoring contract fixed. Measure passage correctness, abstention, source sensitivity and label/order stability, with proper blinded human adjudication.
3. **Transfer mechanisms.** Compare Apertus operating on (a) its own/original evidence, (b) independently authored or deterministic intermediate structures, and (c) frontier-generated intermediate structures only as a separately labeled **teacher-assisted** arm. Where transferable, trial simpler fixed decision contracts, decomposition into bounded subtasks, and a small frozen example set. Distinguish model competence from the teacher having already solved the case.
4. **Independent assessment.** Freeze all prompt/configuration variants before scoring; keep optimization and evaluation source families disjoint, including synthetic variants of the same base sentence. Evaluate on unseen human-checked cases. Control for response-label permutation, passage order, same-domain shuffled counterpart, source removal, fluency and length. Report all attempts and provider/local inference costs; no broad automatic prompt search or fine-tuning by default.
5. **Promotion gate.** A teacher-only improvement is **not** an Apertus improvement. Support transfer only when the frontier model is absent from Apertus inference, Apertus exceeds unchanged B7 and matched no-teacher/deterministic controls on held-out cases, and label stability/counterpart sensitivity pass predeclared thresholds. Benchmark official-token gain requires a separate frozen projection/evaluation arm; successful synthetic classification alone does not establish SwissGov-RSD improvement.

### Outcomes worth distinguishing

- Frontier succeeds but Apertus fails on identical complete evidence → investigate model-capability ceiling, not another router.
- Both models improve with propositions/context → evidence representation is plausible bottleneck.
- Apertus only improves with teacher-written case-specific analyses → **teacher-dependent pipeline**, not autonomous local semantic competence.
- Neither improves → reject current representations/decision task; preserve B7 negative result.

**Resource and authority gate:** No frontier-model call, data upload, paid API, model download, optimization run or training is authorized by this plan. Require a chosen provider/model revision, privacy and licence review, case set, explicit maximum calls/tokens/spend, and supervisor/owner authorization. Hackathon submission readiness stays priority through 16 October 12:00 CEST.

## Existing application context

- [PR #21](https://github.com/blackmath88/apertushackathon-uzh/pull/21): federal profile-based offline evidence pipeline; live BFE capture remains blocked by a source-rights review.
- [PR #22](https://github.com/blackmath88/apertushackathon-uzh/pull/22): genuine Zürich DE/EN service-page captures and evidence desk; real local Apertus analysis still pending at last verified state. Keep scientific development data separate from live civic evidence and publication permissions.

## Tomorrow's deliverable

1. Short submission-readiness PASS/BLOCKED/NEEDS-OWNER report with an ordered list of minimum repairs.
2. Independent B7 S2 scientific review: supported / caveated / cannot reproduce, with exact hashes and controls.
3. Draft of one narrowly scoped proposition-context stability experiment plus the frontier-teacher transfer comparison for **later approval**, not an automatic run.

Follow `blackmath88/weavr/docs/CHATGPT-OPERATING-CONTRACT.md` for any governed future action. Current record is docs-only and authorizes **no merge, deployment, Model Mission dispatch, spend, outreach or release**.
