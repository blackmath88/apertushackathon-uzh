# B8 final report

Recorded 2026-10-14 CEST. The frozen B8 frontier-to-Apertus transfer verdict is
**INCONCLUSIVE**. The frontier teacher and every teacher-derived arm are **NOT
RUN — AUTHORIZATION/PROVIDER**, so neither a teacher ceiling nor autonomous
frontier-to-Apertus transfer was measured. This local-only amendment makes no
benchmark, ranking, submission, deployment, or production claim.

## Relationship to B7

The B7 negative decision is unchanged: the current Apertus verifier and R3
router remain **NOT SUPPORTED**, and B8 supplies no evidence that promotes
either mechanism. B7's CTF-restricted DiffAlign result remains only a supported
structural comparator. No B0-B7 file was changed by the B8 branch.

## Scope and preservation

The original 504-call protocol was frozen at `7f8f243`. A coordinator-approved,
append-only local amendment selected 234 already-planned student rows without
changing their prompts, cases, label maps, configurations, or expected
relations. It excluded 252 teacher-role rows and 18 teacher-generic transfer
rows. The branch did not access protected test data, make a frontier/cloud call,
download a model, submit, deploy, merge, or mutate Weavr.

All 27 synthetic cases remain `provisionally_reviewed`; none is independently
human-verified. Their provenance declarations and labels are therefore
provisional rather than benchmark-grade ground truth. The raw local ledger and
invalid outputs are preserved without repair or retry.

## Local-only measurements

- Execution: 234/234 attempts, 234 HTTP 200 responses, zero recorded errors and
  zero retries; 31,122 estimated prompt tokens, 24,601 backend-reported prompt
  tokens, 468 completion tokens, and 75.437128142 seconds wall time.
- Direct exact accuracy / valid-output rate: R0 0.3333 / 0.5000; R1 0.6111 /
  0.8333; R2 0.7222 / 0.8889; R3 0.6667 / 0.8333.
- Independent family-clustered paired bootstrap for R2 minus R0: +0.3889, 95%
  interval `[+0.1111, +0.6667]` over six evaluation families.
- Deterministic no-teacher contract: 0.7778 accuracy; delta over R2 +0.0556,
  paired family-clustered 95% interval `[-0.1667, +0.3333]`, worst-family delta
  -0.3333. It transfers no teacher-derived information.
- Controls: label-permutation stability 0.8889; passage-order stability 0.7222;
  source sensitivity 0.0000; overall valid-output rate 183/234 = 0.7821. The
  control suite fails the frozen promotion requirements.

The R2-over-R0 contrast is a qualified representation signal on a small,
synthetic, provisionally labelled dataset. It is not evidence of frontier
transfer, a validated semantic benchmark result, or an Apertus benchmark gain.
The primary arms also use only one opaque-label map, so token preference is not
fully disentangled from absolute accuracy. Passage-reversal reporting is
direction-sensitive: the independently recomputed equivariance rate among the
16 valid pairs is 13/16 = 0.8125, still below a promotion interpretation.

## Integrity and reproduction

The canonical full-schedule SHA-256 is
`e936729c4873ddb6c3bfaf928c6b6eb86c2ae8817f762de0f104af71f8694709`;
the canonical local-schedule SHA-256 is
`61bea1f9c939a07b114dbfe8fdf11197cc47d62a3be61f1b7725b4e9b44bf45d`;
and the raw-ledger file SHA-256 is
`ddd47339d4394cd28c0d2799579f5e7d14731f37ad5901e97a0d3b3c0df33c83`.
The top-level checksum manifest covers the final reports, review evidence,
implementation, tests, and generated schedule evidence. The freeze and
local-run manifests independently cover the immutable design and raw run.

From the repository root, reproduce validation without model calls:

```bash
PYTHONPATH=track_2a/src python -m uzh_rsd.b8 validate \
  --package track_2a/experiments/b8-frontier-apertus-transfer
PYTHONPATH=track_2a/src python -m uzh_rsd.b8 schedule \
  --package track_2a/experiments/b8-frontier-apertus-transfer
PYTHONPATH=track_2a/src python -m unittest track_2a/tests/test_b8.py -v
PYTHONPATH=track_2a/src python -m unittest discover -s track_2a/tests -v
(cd track_2a/experiments/b8-frontier-apertus-transfer && \
  sha256sum -c freeze-checksums.sha256 && sha256sum -c checksums.sha256 && \
  cd local-only-q8-20261014 && sha256sum -c checksums.sha256)
```

These commands validate and regenerate schedules in memory/stdout only; they do
not call a model, access a protected split, or alter the preserved evidence.

Final verification passed 14/14 focused B8 tests. The existing offline suite
ran 194 tests with 181 passes, 13 expected skips for deliberately absent pinned
dev/evaluator data, and zero failures or errors, using the already-installed B7
environment (no dependency download). All three checksum manifests passed,
the 504-row schedule regenerated with its committed canonical hash, B0-B7 paths
were unchanged relative to the B7 handoff base, and loopback port 11436 had no
listener after the run. The unrelated Morrow service remained on port 11435 and
was not signalled or mutated.
