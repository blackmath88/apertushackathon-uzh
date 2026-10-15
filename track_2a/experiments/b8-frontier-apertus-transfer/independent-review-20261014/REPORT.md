# B8 independent scientific audit

Date: 2026-10-14. Scope: frozen B8 protocol/cases and committed local-only execution evidence through `db95780`. This was a read-only scientific review: no model call, protected-test access, cloud/frontier call, download, submission, deployment, merge, or change to protocol, cases, raw outputs, or source implementation was performed.

## Executive assessment

The frozen inputs are preserved and the 234-row local schedule, raw ledger, hashes, attempts, and reported numeric budgets are reproducible. The local evidence supports a qualified R2-over-R0 representation result on this small synthetic set, but it does not support frontier-to-Apertus transfer: no teacher arm ran, the no-teacher delta is uncertain, and key frozen controls fail. All 27 labels remain provisional absent real blinded human review, so even the positive representation result is hypothesis-generating rather than a validated semantic benchmark result.

## Reproducibility and preservation

- Commit chronology is freeze `7f8f243` (07:48 CEST), harness `c1778b6` (07:53), then evidence `db95780` (08:05). The eight frozen protocol/case/schema files are byte-identical between the freeze commit and HEAD; their freeze checksums all pass.
- Regeneration yields the committed full schedule hash `e936729...4709` and local schedule hash `61bea1f...45d`; the regenerated 234 local rows exactly equal `frozen-schedule.jsonl`.
- All 14 local-run checksums pass. The ledger hash is `ddd4733...3c83`; all 234 raw-output hashes and all 234 backend-response hashes independently recompute, and the server log contains 234 processing-task records.
- The ledger has 234 sequential, unique call IDs, all marked attempt 1, 234 HTTP 200 statuses, and zero recorded errors. The schedule-to-ledger plan/prompt hashes match. This is strong committed evidence of one preserved attempt per planned local row and no silent retry in the artifact chain, though repository artifacts cannot prove the absence of activity outside that chain.
- `PYTHONPATH=track_2a/src python -m unittest track_2a/tests/test_b8.py` passes 13 tests, and package validation succeeds.
- Reproducibility defect: `sha256sum -c track_2a/experiments/b8-frontier-apertus-transfer/checksums.sha256` fails for `track_2a/src/uzh_rsd/b8.py` and `track_2a/tests/test_b8.py`. Those files changed in the execution commit without refreshing the older package-level manifest. This does not affect the passing freeze manifest or the passing local-run manifest, but the package manifest is not globally reproducible as committed.

## Provenance, split, invariance, and leakage

- The split is genuinely family-disjoint in the artifact: 3 optimization families and 6 evaluation families, with no family overlap. There are also zero exact cross-split overlaps for source sentences, counterpart sentences, source focus strings, or counterpart focus strings.
- Every direct evaluation case occurs under R0-R3 with the same expected relation, system prompt, seed/temperature/output cap, and case ID; only the evidence representation changes. This supports a matched representation comparison.
- Gold relations are present in plans and ledgers but the executed request object contains only call ID, model role, prompt, and configuration. Code and tests therefore support gold-blind callback requests. There is no artifact evidence that protected test data entered the run.
- The negative provenance claims are self-attested metadata, not independently verifiable lineage. All 27 cases say `independently_authored_synthetic` and `protected_test_data_used: false`, but all 27 are only `provisionally_reviewed`; none is `human_verified`. Cases must remain provisional until a real blinded, versioned human review occurs.
- The protocol says opaque label maps are counterbalanced, but all 90 primary matched-direct and transfer rows use one base map. A single cyclic permutation appears only as a control. With imbalanced gold relations (9 equivalent, 9 incorrect, 6 missing, 3 commitment, 0 unresolved), absolute accuracy and token preference are not fully disentangled. The matched within-case representation contrast is less exposed to this confound, but the counterbalancing claim is overstated.

## Controls, uncertainty, and claims

Independent family-clustered paired bootstraps (10,000 draws over six evaluation families) give R2 minus R0 accuracy `+0.3889`, 95% interval `[+0.1111, +0.6667]`. This is a positive within-dataset representation signal, but R2 validity is only `0.8889`, the sample is six synthetic families, and labels are not independently adjudicated.

The label-permutation stability point estimate is `16/18 = 0.8889`, just above the frozen 0.85 threshold. That isolated pass does not rescue the control suite: passage-order stability is `13/18 = 0.7222`, source sensitivity is `0/18 = 0`, R2 validity is below 0.98, and overall validity is `183/234 = 0.7821`. Forty-nine outputs hit the two-token cap and two emitted a relation word instead of an opaque token; preservation rather than repair was correct.

Passage reversal is direction-sensitive: `missing` and `commitment` should swap. The committed statistic compares decoded labels for equality and does not state an equivariance rule. In this run the all-case equivariant count happens also to be 13/18, while equivariance among the 16 valid pairs is 13/16 = 0.8125; neither reaches a robust promotion interpretation.

The deterministic no-teacher contract scores `0.7778` versus R2 `0.7222`, but the paired family-cluster bootstrap delta is only `+0.0556` with 95% interval `[-0.1667, +0.3333]`. Its worst family delta is `-0.3333`, and it transfers no teacher-derived information. It is evidence about a hand-written prompt contract, not autonomous frontier-teacher transfer.

## Runtime and budget compliance

The committed evidence records 234/234 local attempts, 31,122 estimated prompt tokens, 24,601 backend-reported prompt tokens, 468 completion tokens, and 75.44 seconds wall time. These are below the original ceilings of 600 calls, 120,000 prompt tokens, and 2,700 seconds, and the run manifest, server identity, pre/postflight records, and server log are mutually consistent. Zero teacher calls is directly reflected by the selected schedule; zero downloads and zero unapproved spend are asserted by the authority boundary but cannot be independently proven from repository artifacts alone.

## Issues and severity

1. **Claim-blocking — teacher evidence absent (`B8-AUD-001`).** No frontier identity, teacher discovery, matched teacher, or teacher-generic transfer arm exists. The central frozen transfer question and teacher ceiling are unevaluable.
2. **High — promotion controls fail (`B8-AUD-002`).** Passage order, source sensitivity, and output validity fail frozen thresholds; promotion is barred even apart from the missing teacher arms.
3. **Medium — primary label maps are not counterbalanced (`B8-AUD-003`).** All primary rows use one mapping despite the protocol wording.
4. **Medium — labels/provenance lack independent adjudication (`B8-AUD-004`).** The cases are internally consistent but remain provisional and self-attested.
5. **Medium — stale package checksum manifest (`B8-AUD-005`).** Two implementation/test hashes fail, while freeze and run manifests pass.
6. **Medium — passage-order metric is underspecified (`B8-AUD-006`).** Directional labels require an explicit equivariance definition, not raw semantic-label equality.

## Five-part verdict

1. **Representation — qualified positive, synthetic only.** R2 materially exceeds R0 in the paired analysis, but low validity, six families, and provisional labels limit external or semantic certainty.
2. **Label stability — isolated point-pass, overall controls fail.** Label permutation is 0.8889, but order stability, source sensitivity, and validity do not meet the frozen gate.
3. **Teacher ceiling — not measured.** No teacher call ran, so neither a ceiling nor a teacher/student gap can be estimated.
4. **Autonomous transfer — not supported.** The no-teacher contract has an uncertain small delta, a large family regression, and no teacher-derived content. The broader frozen frontier-transfer verdict remains **INCONCLUSIVE**, not negative, because required arms are missing.
5. **Benchmark ranking — not measured.** Synthetic relation classification provides no SwissGov-RSD score, rank, submission result, or basis for changing the B7 conclusion.

Machine-readable recomputation evidence is in `audit-evidence.json` beside this report.
