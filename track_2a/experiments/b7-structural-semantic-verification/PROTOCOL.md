# B7 frozen protocol

This protocol is frozen before structural scoring, model inference, or any new
gold-aware evaluation. It executes the supplied eight-phase B7 contract on the
authorized 30-document development sample only. Minimum practically meaningful
benchmark improvement is +0.005 macro Spearman over the matched comparator.

## Structural arms

- S0 is the published B4 vector byte-for-byte.
- S1 is B5 regenerated M0, explicitly not the published baseline.
- S2 is CTFAlign coarse-to-fine pruning, upstream commit `30f4f89`, argmax mode,
  width 8, applied to the exact B5 Qwen layer-20 matrices. Continuous anomaly is
  `1 - max(permitted cosine)` and official-token projection is the arithmetic
  mean over the unchanged subword-to-official mapping.
- The S2 ceiling is one implementation, one focused repair, 120 CPU seconds,
  zero downloads and zero embedding calls. Hash mismatch blocks S2.

## Routing and anchoring

R1 reuses the first five actual `suspicious_v1` B5 regions per document. R2 is
SHA-256 deterministic random routing with seed `b7-routing-20261013-v1`. R3
ranks numeric/date and multilingual modality/polarity/condition lexemes plus
anchored lexical disagreement and a fixed 0.05 B4-anomaly tie component. Each
R2/R3 document has exactly R1's unique official source-token coverage (21–25
tokens; 734 total). Candidate generation accepts no gold.

All routes share CTF width-8 argmax anchoring. Exact whitespace-token `[start,
end)` character offsets are stored. Missing correspondence is `unavailable`;
it is never invented. The deduplicated union is inferred once and cached.
Evidence context and scoring footprint are the candidate source and anchored
target spans only; R3 receives no free context or score footprint.

## Verifier and model-call budget

Apertus uses the existing Q8_0 GGUF SHA-256 `dea904ad…202d`, verified llama.cpp
commit `7ab4ee7`, localhost port 11436, temperature 0, seed 20261013, and a
single primary five-label prompt: equivalent, different commitment,
additional/missing, incorrect correspondence, unresolved. Output must be one
label token. Invalid, unavailable, timed-out, and unresolved cases fall back to
baseline. Every prompt, raw output, usage object, latency, error and config is
preserved. Candidate ceiling: 1,578 calls, one attempt each, 60 s timeout.

The independent synthetic set has 24 pre-authored cases spanning EN-DE/FR/IT
and all eight required categories. Each gets base, reversed-passage,
permuted-label, combined, unrelated-counterpart and meaning-preserving calls,
plus A/B and B/A contrastive calls: 192 calls maximum. Acceptance thresholds:
primary accuracy >=0.80, each order/label stability >=0.85, unrelated
counterpart sensitivity >=0.75, equivalent false-positive rate <=0.20, valid
output rate >=0.98, no failed call, and total local wall time <=30 minutes.
Passing is capability evidence only.

## Projection and evaluation

The frozen update is `max(B4, 0.85)` on exact candidate official-token
footprints only for commitment, missing, incorrect, or independently
deterministic constraint-discrepancy evidence. All other positions preserve B4
exactly. Discontinuous spans update their explicit token IDs. No score is
deleted or zero-filled. No fitting is performed.

E0–E3 and E5–E7 follow the supplied contract. E4 is explicitly not measured
because the optional compact comparator exceeds the zero-download dependency
ceiling. E5 shuffles cached Apertus decisions with seed 20261013 while retaining
the identical R1 candidates and footprints. E6 uses actual decisions. E7 uses
R2 versus R3 at identical per-document unique-token coverage.

Primary metrics are official pooled-by-language Spearman and their macro;
diagnostics are per-language deltas, gold-positive and B4-missed-positive
recall, selected-negative burden, unique coverage, punctuation/output
integrity, ties, invalid rate, latency/tokens, shared-family bootstrap (500,
seed 20261013) and leave-one-family-out influence. No threshold, prompt,
routing rule or update is changed after results.

The blinded audit sample is frozen after predictions: five model discrepancies
absent from positives, five positives missed by all, and five seeded controls.
Method identity and prediction are omitted from the review sheet; official gold
is never overwritten.

