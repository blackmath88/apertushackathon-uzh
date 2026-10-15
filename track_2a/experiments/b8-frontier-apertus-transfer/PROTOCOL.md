# B8 frozen protocol

Status: **frozen before inference**. This protocol governs a synthetic
frontier-teacher to local-Apertus transfer experiment only.

## Question and non-claims

Does a better evidence representation or fixed task decomposition, discovered
with a frontier teacher on optimization families, improve local Apertus on
unseen source families when the teacher is absent from Apertus inference?

A teacher-only gain is not an Apertus gain. A teacher-authored case-specific
answer consumed by Apertus is a teacher-dependent arm, not autonomous transfer.
Synthetic classification cannot establish official SwissGov-RSD token-ranking
gain. B7's Apertus verifier remains NOT SUPPORTED.

## Frozen cases and split

There are 27 synthetic pairs: nine each for EN-DE, EN-FR, and EN-IT. The split
unit is `source_family_id`. Optimization uses three families (9 cases);
evaluation uses six disjoint families (18 cases). Categories cover modality,
negation, quantity, deadline, condition, exception, omission, faithful
paraphrase, and scope. Selection and expected relations were authored before
any B8 model output.

Every record carries provenance, review status, full context, exact Unicode
code-point offsets, structured commitments, and an expected relation. Review
status is `provisionally_reviewed`, never `human_verified`. Later adjudication
must be independently blinded and versioned; it cannot overwrite this freeze.

## Representations

- R0: exact token-centered focus snippets, matching B7's narrow evidence idea.
- R1: the complete aligned source and counterpart sentences.
- R2: R1 plus the governing heading and condition on each side.
- R3: frozen structured commitments: actor, action, modality, polarity,
  condition, quantity, deadline, and exception. Missing values are explicit
  `null`; the structure is independently authored, never model-generated.

The same case IDs and decision labels are used across representations. The
relation labels are `equivalent`, `commitment`, `missing`, `incorrect`, and
`unresolved`, encoded through counterbalanced opaque label maps. Output is one
opaque label token or abstention.

## Schedule

The full predeclared design comprises:

1. Teacher discovery on all R0-R3 representations for 9 optimization cases: 36 calls.
2. Matched teacher and Apertus direct judgements on R0-R3 for 18 evaluation cases: 144 calls.
3. Four controls (passage order, label permutation, source ablation, and same-domain shuffled counterpart) on R1 and R2 for both models and 18 evaluation cases: 288 calls.
4. Two Apertus transfer contracts (deterministic/no-teacher and teacher-derived generic contract) on R2 for 18 evaluation cases: 36 calls.

Total ceiling is 504 scheduled calls. Same-domain shuffling is deterministic
within language and evaluation split and never pairs a case with its own family.
The teacher-derived contract may use only aggregated optimization-family output;
no evaluation case answer or private reasoning trace may be transferred.

## Identity, budgets, and stop rules

The student is Apertus-v1.5-8B Q8_0 with required GGUF SHA-256
`dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d`,
llama.cpp commit `7ab4ee7`, endpoint `http://127.0.0.1:11436`, temperature 0,
seed 20261014, one attempt, and no retry. The frontier teacher provider and
exact immutable model revision must be supplied through an approved protocol
amendment before calls; unset identity blocks execution.

Hard ceilings are 600 total calls, 120,000 estimated prompt tokens, 45 minutes
projected/observed wall time, zero downloads, and zero unapproved spend. Stop
before the first call on a freeze mismatch, unknown identity, authorization
absence, protected-data signal, non-local student endpoint, or runtime mismatch.
Stop during execution before any call that would cross a ceiling. Preserve every
attempt, prompt hash, output hash, usage, latency, error, and configuration in an
append-only ledger. Never retry silently.

## Metrics and promotion gate

Primary evaluation-family metrics are exact relation accuracy, abstention rate,
valid-output rate, source sensitivity, label stability, passage-order stability,
and per-language accuracy. Report family-clustered bootstrap intervals and all
attempts. Optimization families tune no numeric threshold after the freeze.

Transfer is supported only if Apertus, with the frontier absent at evaluation
inference, exceeds unchanged Apertus R2 and the matched deterministic/no-teacher
contract by at least 0.05 exact accuracy on evaluation families, with label and
order stability each at least 0.85, source sensitivity at least 0.75, valid rate
at least 0.98, and no family-level regression greater than 0.10. Otherwise the
result is NOT SUPPORTED or INCONCLUSIVE as predeclared by the evaluator.

## Authority boundary

This freeze authorizes offline validation and dry scheduling only. It does not
authorize a frontier/cloud call, data upload, local model inference, provider
spend, download, training, submission, deployment, merge, Weavr mutation, or
Morrow change. Draft PR #26 is source context, not execution authority.
