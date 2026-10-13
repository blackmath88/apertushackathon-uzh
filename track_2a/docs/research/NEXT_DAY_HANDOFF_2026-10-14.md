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

## Existing application context

- [PR #21](https://github.com/blackmath88/apertushackathon-uzh/pull/21): federal profile-based offline evidence pipeline; live BFE capture remains blocked by a source-rights review.
- [PR #22](https://github.com/blackmath88/apertushackathon-uzh/pull/22): genuine Zürich DE/EN service-page captures and evidence desk; real local Apertus analysis still pending at last verified state. Keep scientific development data separate from live civic evidence and publication permissions.

## Tomorrow's deliverable

1. Short submission-readiness PASS/BLOCKED/NEEDS-OWNER report with an ordered list of minimum repairs.
2. Independent B7 S2 scientific review: supported / caveated / cannot reproduce, with exact hashes and controls.
3. Draft of one narrowly scoped proposition-context stability experiment for **later approval**, not an automatic run.

Follow `blackmath88/weavr/docs/CHATGPT-OPERATING-CONTRACT.md` for any governed future action. Current record is docs-only and authorizes **no merge, deployment, Model Mission dispatch, spend, outreach or release**.
