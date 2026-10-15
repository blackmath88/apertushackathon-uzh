# B3 — Semantic Decision Middleware (SDM)

Status: experimental design, 13 October 2026. **Not an established improvement or a replacement for frozen B0/B2.** This plan is a separate experiment derived from the completed projection-cap experiment in PR #14.

## Name and responsibility

**Semantic Decision Middleware** is a provider-agnostic, deterministic layer between heterogeneous document inputs and a bounded semantic classifier. It is not an agent, another orchestration product, a brand-specific integration, a new source of truth, or a new mandate to run Weavr Missions.

> Deterministic software identifies what semantic question must be answered. Apertus classifies that question from bounded evidence. Deterministic software validates and assembles the result.

Reusable in two adapters: (1) SwissGov-RSD token-score benchmark and (2) the Stadt Zürich bilingual public-services pilot. The latter is in separate draft PR #13 and has no gold labels; field outcomes must not be mixed with benchmark metrics.

## Scientific motivation

PR #14 independently established:
- P1 (160-token cap) recovers 14 saved and 28 local Q8 matchable excerpts but does not consistently improve macro Spearman (frozen pilot 0.175044 -> 0.192060; local Q8 0.189283 -> 0.180127).
- Only 17/30 local Q8 responses were parseable (DE 8, FR 5, IT 4); 12/30 reached 1,024 completion tokens.
- This is **not** proof that smaller decisions improve accuracy. Classification skill, alignment quality, and token-scoring quality must be tested separately.

B3 hypothesis: explicit deterministic segmentation/candidate alignment, small closed-set Apertus classifications, and validated offset-based evidence could improve **full-sample inference coverage** and possibly token-level Spearman, compared with frozen B2 on the same model and predeclared dev IDs. A null or negative result is scientifically valid.

## Architecture

```
input document pair + supplied token offsets
   -> deterministic segmentation / alignment candidates
   -> typed comparison tasks with stable IDs and exact source offsets
   -> deterministic routing
       * lexical/structural observation (never equates to semantic truth)
       * Apertus for unresolved bounded semantic relation
       * UNRESOLVED when evidence is insufficient or output invalid
   -> schema validation and source-offset verification
   -> immutable decision/evidence records
   -> output adapter A: benchmark token score vectors
      output adapter B: human-reviewable bilingual discrepancy candidates
```

No model may change source offsets, select its own tools or routes, mark its decision as verified, or silently repair malformed output. The middleware owns orchestration; the model has **no action authority**.

## Minimal data contracts (proposed `sdm/v1`)

**Comparison task**: `{task_id, document_id, language_pair, left:{start_token,end_token,text}, right:{start_token,end_token,text}|null, alignment_basis, alignment_status}`; half-open positions in the provided official token sequence. Task selection is deterministic, seed/policy/version recorded; an unmatched side remains unresolved until checked, not automatically OMISSION.

**Classifier response**: `{relation: EQUIVALENT|DIFFERENT|UNCERTAIN, kind: NUMERIC_CHANGE|NEGATION_CHANGE|ENTITY_CHANGE|TEMPORAL_CHANGE|MODALITY_CHANGE|QUALIFICATION_CHANGE|OMISSION|ADDITION|OTHER|NONE|UNKNOWN}` and optionally short rationale. Do **not** ask for repeated source text, long excerpts, offsets, or an unconstrained list of arbitrary document-wide differences. For v0 omit severity entirely unless empirically justified.

**Decision record**: task/prompt/model/schema versions, raw response digest, parsed response or typed failure, reasoning status, source spans inherited from task, timestamps, tokens, latency, confidence **only if calibrated**, validation outcome. No fabricated probability/confidence. Invalid output -> UNKNOWN / abstain, not equivalence.

**Projection**: adapter must output vectors of the exact official token length and document ordering when supported. Explicitly distinguish unscored/unknown tokens and prediction defaults; any mandated numeric default is an evaluation policy, not a semantic assertion of equivalence. Affected-token policy is predeclared and independently evaluated; avoid assigning high severity across an entire long passage by default.

## Pilot experiment specification

1. **Inspect/freeze controls before new inference.** Reuse the exact frozen local Q8 30-ID manifest from PR #14: ten documents per EN-DE/FR/IT. Preserve B2 raw/analysis. Same Q8 weights hash `dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d`, llama.cpp revision `7ab4ee7`, decoding configuration and scoring script where feasible. Record every deviation.
2. **Offline first.** Build alignment/segmentation, task DAG, validation, benchmark projection, failure accounting and tests from synthetic fixtures. No access to test split. No hidden gold in prompts or routing, not even through derived 'burden' labels.
3. **Build cheapest honest classifier.** One aligned passage pair per call; strict small JSON object; bounded per-call generation (e.g. 64–128 tokens, chosen/frozen before seeing scores). Use controlled vocabulary and explicit UNCERTAIN. Respect right-side empty cases, multilingual punctuation and duplicate text offsets.
4. **Avoid combinatorial inference.** Set and persist hard maximum tasks/calls per document and total calls, per-request timeout, global walltime ceiling, and a deterministic stop/status for overflow. Preliminary dry-run reports expected calls and time at observed 29 tok/s; do not start if accepted budget cannot cover fixed sample. Refuse truncated task batches without an explicit coverage label.
5. **Evaluate against B2 on identical dev IDs**, including all failures and skipped examples. Report classification parseability per task, *complete-document vector coverage* on all 30, additional UNKNOWNs, per-language and macro Spearman with denominators, calls, prompt/completion tokens, latency, alignment candidate recall/diagnostics when dev labels permit, and representative improvement/regression/unchanged cases.
6. **Ablation:** first compare B2 vs B3 at the same model configuration; where feasible, compare 'direct classifier on supplied aligned spans' against heuristic routing without changing the frozen sample. Mark all exploratory follow-up runs separately.
7. **No claim of success without improvement.** Invalid classifier outputs and unresolved alignments should degrade recorded coverage, not disappear from the denominator. A high parsing percentage alone is not benchmark success.

## Safety and scope

- Test split is never enumerated, inspected, downloaded or used during development; final judge procedure remains a separate owner decision.
- No paid inference, cloud endpoint, auto fallback, new model download, outbound public crawling, publishing findings, outreach, deployment, merge, Need waiver or canonical Weavr Mission change is authorized by this plan.
- Keep PR #12 (submission), #13 (city pilot), #14 (B2 evidence) separate and draft; avoid touching their frozen evidence.
- Local Apertus may be started only under explicit execution authority in a bounded local Codex handoff; restore it stopped, keep Morrow unchanged.
- Finish report as `SUPPORTED`, `NOT SUPPORTED`, or `INCONCLUSIVE` with artifacts. Distinguish engineering/parse success from semantic accuracy.

## Acceptance criteria

- Deterministic pipeline and typed SDM v1 contracts documented and offline tested.
- Alignment unknown and unmatched cases remain explicit; no invented offsets.
- At least one bounded local 30-pair comparison if budget and runner readiness allow; otherwise honest BLOCKED result.
- Comparisons account for all original IDs (including missing predictions), with both conditional-on-parseability and full-sample policies visible.
- Reproducible raw/model/artifact hashes and independent tests.
- No changes to original B2 numbers, gold isolation, official benchmark contract or unrelated projects.
- Draft PR and compact user-facing scientific verdict.
