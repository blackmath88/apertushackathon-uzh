# Build and Experiment Plan

Status: bootstrap / pre-baseline  
Hack Apertus build window: 1–16 October 2026  
Submission deadline: 16 October 2026, 12:00 CEST

## 1. Project sentence

**Extract a semantic-compiler kernel from `accessibility-red-team`, then build the SwissGov-RSD benchmark adapter fresh.**

This is not a fork-and-strip exercise. The parent contributes architecture; this repository owns a new benchmark-specific implementation.

## 2. Challenge

SwissGov-RSD compares related Swiss government documents across English–German, English–French and English–Italian. The target is one semantic-difference score per benchmark token. The primary metric is token-level Spearman correlation per language pair, macro-averaged.

The official repository exposes train/dev/test material. **The provided test set must not enter development in any form.**

## 3. Core hypothesis

> Structured semantic compilation over aligned spans, followed by deterministic projection to token-level scores, can outperform direct token scoring while improving interpretability, reproducibility and efficiency.

Do not protect this hypothesis. The first job is to falsify it cheaply.

## 4. Kernel extracted from accessibility-red-team

Reuse the following ideas/contracts:

1. Traditional software owns workflow and canonical state.
2. Ask: **What is the smallest remaining semantic decision?**
3. Escalation: data/lookup → deterministic → heuristic/statistical → typed semantic decision → constrained synthesis → exceptional agentic escalation.
4. Bounded model inputs.
5. Closed/typed outputs with confidence and `UNKNOWN`.
6. Deterministic validation and consumption.
7. Raw observations stay separate from model-derived data.
8. Content-addressable semantic decisions are desirable for reproducible experiments.
9. Every model call must be benchmarked against a cheaper baseline.

Do **not** transplant accessibility-specific Playwright, axe/WCAG logic, Scout, journeys, Cloudflare UI/application code, municipality profiles or agent orchestration.

## 5. Benchmark adapter built fresh

```text
SwissGov-RSD pair
      ↓
canonical token bookkeeping
      ↓
segmentation / candidate alignment
      ↓
cheap structural or lexical signals
      ↓
bounded Apertus semantic decision
      ↓
typed semantic-difference IR
      ↓
deterministic token projection
      ↓
official-format predictions
      ↓
official evaluation
```

Keep ordinary code responsible for dataset ingestion, split isolation, canonical token mapping, segmentation, schema validation, experiment metadata, caching, projection, prediction formatting, evaluation and run comparison.

## 6. Experiments

### B0 — direct control

```text
dev document pair → benchmark tokens → Apertus → token scores → validation → official evaluation
```

Establish the control with minimal prompt optimisation.

### B2a — localisation diagnostic

```text
aligned evidence → Apertus marks divergent spans → binary projection → official evaluation
```

This separates localisation quality from severity calibration.

### B2 — semantic compiler

Initial IR stays deliberately small:

```json
{
  "differences": [
    {
      "source": {"start": 23, "end": 27},
      "target": {"start": 19, "end": 24},
      "kind": "CHANGE",
      "severity": 4,
      "confidence": 0.91
    }
  ]
}
```

Initial kinds: `CHANGE`, `ADDITION`, `OMISSION`, `UNKNOWN`. Severity is benchmark-aligned 1–5; uncovered tokens project to 0. Add richer change types only if dev evidence shows value.

### B3 — minimum-AI hybrid

Deferred until B0/B2 work. Candidate cheap signals include number/date mismatch, lexical overlap, named strings/entities, structural correspondence, omission/addition candidates and multilingual embedding similarity.

## 7. Run record

Every experiment records: run ID, strategy, model/revision, prompt/schema versions, split, language pair, input/output tokens, model calls, latency, structured-output failures, UNKNOWN rate and Spearman.

Raw observations and source data are immutable. Prompts, semantic decisions, projections and metrics are derived artifacts.

## 8. Development sequence

### M0 — reproducibility shell
- required `track_2a/` shape;
- `make run` and `make test`;
- split guard;
- typed IR skeleton;
- projection function;
- plan + sources.

### M1 — benchmark adapter
- pin SwissGov-RSD revision;
- dev-only loader;
- canonical token representation;
- official-format prediction writer;
- official evaluation wrapper;
- tiny fixed dev slice.

### M2 — B0
- Apertus runtime/provider;
- direct token-scoring prompt;
- structured-output accounting;
- first dev Spearman for all three pairs.

### M3 — B2a/B2
- simple alignment;
- bounded sparse-span prompt;
- schema validation;
- deterministic projection;
- same dev slice and model;
- comparison with B0.

### Decision gate
Continue with UZH as the primary project only if the experiment yields a credible contribution: metric gain and/or meaningful reduction in model work/output fragility with an interpretable trade-off.

### M4 — only if earned
Alignment variants, richer difference types, heuristic gating, 8B vs 70B, self-consistency, adapters/fine-tuning, visualisation/report polish.

## 9. Acceptance for first real experiment

- clean checkout runs tests;
- test split cannot load through normal development path;
- 5–10 fixed dev pairs run end-to-end;
- every Apertus decision references bounded input spans;
- outputs are schema-valid or explicitly failed/fallbacked;
- token projection is deterministic and unit-tested;
- official evaluation runs;
- B0 and B2 are directly comparable;
- experiment metadata is persisted.

## 10. Questions for UZH

1. Is span/sentence decomposition followed by deterministic token projection fully valid?
2. Is direct model token output required anywhere in the submission contract?
3. Are external multilingual embedding models allowed as support tooling if Apertus remains the semantic model?
4. Are there runtime/inference-budget constraints?
5. Are alignment artifacts provided or participant-owned?
6. Which baseline/prompt version is the official reference?
7. How should final test evaluation be invoked without development leakage?

## 11. Scope exclusions

No UI, generic agent framework, open-ended planning, model-driven orchestration, fine-tuning before baseline, large taxonomy before evidence, test-set inspection, or architecture that does not improve the B0/B2 experiment.
