# B4 → B5 research synthesis and experimental decision plan

Date: 2026-10-13 (Europe/Zurich). Status: **proposed research; no new experiment executed by this commit**. Submission deadline: 2026-10-16 12:00 CEST.

## Primary source artifacts

Two distinct user-supplied Perplexity reports have been archived verbatim as research inputs:

1. [Adversarial Research Review](perplexity-adversarial-review-2026-10-13.md) — emphasizes **semantic mass left unexplained**, competitor-aware/NULL matching, and a gold-isolated B5 local-correction oracle before calling Apertus.
2. [Denkraum Traverse](perplexity-denkraum-traverse-2026-10-13.md) — follows six dealt moves (`re-enter`, `constellate`, `historicize`, `refuse-the-metaphor`, `demote`, `interpose`); prioritizes **router-conditioned rank-error tomography**, a potential pairwise semantic tournament, cycle-consistency, equivalence certificates, and alternative constraint-based matching.

These reports are **externally generated research proposals, not independently validated facts**. Historical/philosophical attributions and library/API assertions within them need independent verification before use as factual claims. No Denkraum deposit is promoted into canonical state. The related Claude critique (supplied separately in conversation) proposes Apertus teacher-forced token surprisal, but that is **not** either of these two archived Perplexity documents.

## Baseline evidence: grounded in existing B4 PR #17

- Frozen development sample: 30 document pairs; 10 per EN–DE / EN–FR / EN–IT.
- Gold-derived oracles: binary exact positive-token locations macro **0.999284**; perfect sentence broadcast **0.534211**; coarse passage broadcast **0.378722**. Oracle scores only diagnose representational ceilings, not achievable model performance.
- Published Qwen3-Embedding-4B DiffAlign predictions: complete 30-pair macro **0.187117**, **zero Apertus calls**. Existing cache contains scores, **not token embedding matrices, counterpart indices or matching margins**. Cached replay timing does not include encoder generation.
- One-token Apertus 16-call feasibility probe: 16/16 valid numeric outputs; accuracy 50–75% under four small conditions; candidate logprobs available; order/label sensitivity observed. This is *not* proof of semantic uplift or grammar-constrained probability validity.
- B2 full-sample zero-default baseline on same 30 IDs: macro **0.129306** (P1); 17/30 semantic outputs. Avoid treating default-zero vectors as complete semantic coverage.

## Where both reports converge

1. **Do not run B5 model calls yet.** First test whether a fixed, gold-blind router reaches enough correctable rank errors.
2. Keep **gold labels out of all router construction, features and model inputs**. Only diagnostic oracle/evaluator may inspect gold.
3. The most obvious residuals are not necessarily the most important errors: the worst false negatives can be confidently (but wrongly) aligned repetitions.
4. DiffAlign's unrestricted independent maximum allows many-to-one matches and no explicit NULL state. Competition/cycle/position/NULL are hypotheses requiring *same-embedding* comparisons.
5. Apertus needs incremental ablation against identical deterministic baseline, unchanged candidate set and shuffled/model-free controls.
6. Group resampling/validation by shared EN document across all three language pairs; 30 pairs do not constitute 30 independent multilingual source families if they share EN IDs. Count unique English parent IDs from the manifest.

## Where they diverge

| Decision | Earlier review | Denkraum traverse | Proposed resolution |
|---|---|---|---|
| First experiment | B5 selected-region oracle correction ceiling | Router-conditioned rank-error tomography with rank residuals | Combine; latter records where, why, and whether reachable |
| Candidate budget | 1,3,5,10 groups/doc | 1,3,5,10 windows/doc, width 3 tokens | Freeze exact non-overlapping 3-token windows and report all four budgets |
| Oracle adjustment | Flexible keep/promote/demote/NULL family | Fixed uniform offsets in language SD units, 3-pass coordinate search | Implement *both* transparent ceilings: exact gold replacement (unattainable upper diagnostic) and achievable-form restricted-offset optimistic diagnostic. Restricted search is **not mathematically guaranteed global upper bound** |
| Conditional Apertus experiment | Three-option alternative vs best vs NULL (~180 calls) | Four-candidate pairwise semantic tournament (~360 calls) | Defer choice until A shows reachable gain and after quick controlled trial; comparison should test whether *relative* semantics is more stable |
| Secondary deterministic path | NULL-aware assignment / affine gaps / partial transport | Cycle defect, certificates, transport, semantic syndromes | First verify usable embedding or link artifact; test one minimal independent-vs-reciprocal and one NULL-aware control, not a research-stack rewrite |

**Material caution:** the two oracle ceilings answer different questions. Exact gold replacement answers what a perfect intervention inside selected tokens could do. Restricted offset tuning answers what a very simple local score-update operator could *approximately* attain. Neither is deployable, and gold-driven optimisation is not a benchmark result.

## Stage A — gold-blind router-conditioned rank tomography (mandatory; CPU only)

### Preflight freeze
- Inspect latest PR stack, preserve existing workers/state, create an isolated implementation branch/worktree from this research branch; do not update PR #17 source/artefacts.
- Pin SHA-256 hashes of B4 cached prediction vectors, frozen 30-ID manifest and official evaluation code, plus policy source revisions.
- Record the actual unique English parent documents, duplicate-source groups and official punctuation mask.
- Make router code and manifests **unable to import gold**. Freeze the complete router policy/configuration and selected windows in a commit before computing any oracle score. A gold-insensitive dry run is allowed.
- Use the existing scorer's pooled-by-language protocol; bootstrap over EN source family clusters (all linked pair languages together). CI estimates descriptive, not proof of significance.

### Frozen routers and budgets
Candidate windows have width = 3 official tokens (clipped at boundaries), non-overlapping within each document side. Freeze stable tie-breaking and document-side selection. Evaluate 1, 3, 5, 10 windows/doc, both sides when available:
- `top_anomaly`: highest DiffAlign scores.
- `local_peak`: largest difference versus immediate neighborhood.
- `high_gradient`: score transitions.
- `repeated_structured`: repeated numeric/date/URL/capitalized tokens visible in the text; no inferred counterpart links.
- `low_context_support`: anomalous token with locally low contextual anomaly.
- `uniform_random`: seeded negative control (predeclare 1,000 seeds or bounded deterministic resampling).
Do not call score-only routers 'alignment-margin' or 'high-entropy correspondence' without actual candidate-edge evidence.

### Diagnostics (gold isolated)
- Official pooled per-language and macro Spearman for unmodified B4.
- Predicted/gold midranks over eligible (non-punctuation) tokens; signed residual, squared rank residual as **descriptive diagnostics, not additive causal attribution**.
- Local-router recall of gold positives, under-ranked positives, over-ranked gold zeros and squared-rank-error mass; per-language and unique-EN-parent breakdown.
- Selected-window overlap, repeat-value breakdown, score deciles, document contribution and random-router percentiles.
- Two oracle interventions, separately labelled:
  1. **Gold replacement oracle**: overwrite only selected eligible token positions with gold-derived scores; aspirational diagnostic, not achievable by B5.
  2. **Restricted-offset oracle**: score correction chosen from `[-1,-.5,-.25,0,.25,.5,1] * pooled-language std`, **uniformly per selected window**, max three frozen coordinate passes. Use only diagnostic gold; never train/routinely predict with these corrections. Preserve score range contract or valid deterministic clipping as predeclared; track ties/clipping.
- Sanity controls: unchanged B4 scores, random windows with identical budget/algorithm, top-anomaly only, unrestricted whole-document gold oracle labelled impossible.
- Output `router-config.json`, `selected-windows.jsonl`, `rank-errors`, `oracle.jsonl`, `metrics.json`, `random-controls.json`, `report.md`, source checksums and reproducibility instructions. Do not commit third-party full text without licence review.

### Stage A decision gate (thresholds frozen *before* scoring)
At **three 3-token windows per document**, **CONTINUE** to investigate model inference only if:
- restricted-offset *attained* macro gain >= **+0.02** above the frozen B4 0.187117;
- above 95th percentile of matched random-window control in at least two language pairs;
- routed windows reach both under-ranked positives and over-ranked zeros;
- no single EN source family accounts for >50% of gain.

**REJECT current router** if restricted-offset gain < +0.01, or fails to beat random, or is effectively concentrated in one language/source family.

Else **INCONCLUSIVE**. Note that thresholds are heuristic go/no-go criteria; do not claim statistical validation from 30 examples. If inconclusive, choose submission preservation over a speculative large run.

The gold-replacement oracle may show headroom when the restricted-offset policy cannot exploit it; log the reason without reversing the predeclared gate after results.

## Stage B — same-embedding matcher feasibility (separate scoped diagnostic; no Apertus)

- Independently inspect upstream pinned alignment repository and local ignored caches for saved Qwen3-Embedding-4B token embeddings, subword maps, similarity matrices or partner indices. Published DiffAlign **scores cannot reconstruct these**.
- If unavailable: record pinned regeneration path, permissions/licence, file sizes and estimated hardware/runtime; **do not** launch a large embedding regeneration without a separately accepted resource ceiling. A second small checkpoint changes both model and matching law and cannot prove same-embedding improvement versus B4.
- With identical original embeddings/candidate matrix: compare independent max similarity, reciprocal candidate cycles/mutual match and one NULL-aware capacity/assignment control, plus a reasonable one-to-many-safe alternative. Freeze match policy; evaluate full-sample correlation, repeated date/name failures, NULL rate, candidate recovery, memory and true end-to-end encoder cost.
- Only if deterministic matching shows replicated improvement does wider partial transport or affine gap work become plausible. Do not make Stage A dependent on embeddings.

## Stage C — Apertus incremental-value experiment (strictly gated)

- Only if Stage A CONTINUE **and** actual correspondences/candidate alternatives exist and local runtime identity is verified.
- Before inference, compare *two small, fixed* contracts on a tiny permitted training/non-scored smoke sample: three-way match vs best alternative vs NULL, and pairwise relative ranking. Predeclare labels, controls, exact token features and scoring effects; do not use feedback to indefinitely prompt-search.
- If choosing contrastive triage: up to 3 groups/doc * 2 controlled calls = max 180 calls. If choosing pairwise tournament: up to 4 groups/doc, six duels * 2 orders = max 360 calls. **Choose one**, not both full experiments. Record explicit cap, walltime and preflight expected compute; reserve ample time for packaging.
- Compare Apertus arm with unchanged baseline, matching-only deterministic adjustment, shuffled probabilities, hard-label arm, order/label controls, and constant-score control; all use **the same routed candidates and projection policy**. Group uncertainty by EN family; full-document outputs and fallback documented.
- No generated source offsets or free-text rationales. The official held-out test split stays untouched for development. No paid compute/HF/cloud fallback; no merge/deploy; retain original experiments immutably.
- An accepted result is evidence only if Apertus improves full-sample official score beyond deterministic/shuffled controls without hidden coverage reduction. Otherwise record NOT SUPPORTED and stop.

## Submission-preservation gate

Before extending beyond Stage A/B, inspect current `track_2a/docs/JUDGE_READINESS.md`, `SUBMISSION_CHECKLIST.md`, technical report, clean Docker/judge interface, licensing and test/final-input procedure. Do not use the final test set as development feedback. Reserve sufficient time for clean checkout, required artefacts, team/publication decisions, and submission before **October 16, 12:00 CEST**. A promising oracle ceiling is not sufficient reason to jeopardise delivery.

## Repo write authority

- This branch is **research documentation only**, not a Weavr Mission dispatch.
- For future actual governed Weavr writes, follow `blackmath88/weavr/docs/CHATGPT-OPERATING-CONTRACT.md` and use typed `.weavr/inbox/` commands when authorized. No automatic mission creation, waiver, scope expansion or merge.
- Working run reports should distinguish source-derived claims, proposed hypotheses, generated oracle diagnostics and measured observations.
