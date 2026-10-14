# B8 pre-inference completion report

Recorded 2026-10-14 CEST. Outcome: **READY FOR SEPARATE AUTHORIZATION;
INFERENCE NOT AUTHORIZED OR PERFORMED**.

## Freeze evidence

- Exact branch: `blackmath88/b8-frontier-apertus-transfer`.
- Base/handoff: draft PR #26 head `2a83afdc3e6238cd6d37da395b80e212a62bbb13`.
- Protocol-freeze commit: `7f8f243` (`experiment: freeze B8 frontier Apertus transfer protocol`).
- Frozen cases: 27 pairs, SHA-256 `9030f3dc5723266084c3901de39538c6242bd8c86ac35b7ada29dd308d3ff540`.
- Frozen families: 9 families, SHA-256 `71fecbc76bfe35ee05b57e8f00a032d4b19245c26229b5f093d6a5347b667060`.
- Split: 3 optimization families / 6 evaluation families, with one EN-DE,
  EN-FR, and EN-IT pair in every family and no cross-split family.
- Review status: all cases `provisionally_reviewed`; none `human_verified`.

The freeze commit precedes the runner/evaluator implementation. The freeze
manifest records zero frontier and zero local model calls before the commit.
No model call occurred afterward during this task either.

## Runtime identity and authority

The local GGUF was read-only hashed as
`dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d`
(8,567,121,856 bytes). The required llama.cpp commit is `7ab4ee7` and the only
allowed student endpoint is `http://127.0.0.1:11436`. That port remained closed.
Morrow on `127.0.0.1:11435` was not changed or signalled.

Execution remains blocked because the teacher provider/revision, external-data
approval, and spending authorization are unset. The runner has no network
client. It requires an injected callable, an authorization bound to the frozen
protocol, an immutable teacher identity, and a locally attested student
identity; mismatches fail before the callback receives a request. Gold expected
relations are not passed to the injected callable.

## Dry-run evidence

The full design schedules 504 one-attempt calls:

| Arm | Calls |
|---|---:|
| Teacher discovery, optimization families | 36 |
| Matched direct evaluation | 144 |
| Counterbalanced controls | 288 |
| Apertus transfer contracts | 36 |

The dry run estimates 67,135 prompt tokens and 2,016 sequential seconds
(33.6 minutes), below the hard ceilings of 600 calls, 120,000 prompt tokens,
and 2,700 seconds. The schedule SHA-256 is
`e936729c4873ddb6c3bfaf928c6b6eb86c2ae8817f762de0f104af71f8694709`.
`schedule-ledger.jsonl` contains all 504 prompt plans; the summary explicitly
records `model_calls_performed: 0`.

## Verification

Successful focused command:

```text
PYTHONPATH=track_2a/src /home/achim/orca/workspaces/apertushackathon-uzh/b5-competitive-semantic-alignment/track_2a/.venv-b5/bin/python -m unittest track_2a/tests/test_b7.py track_2a/tests/test_b8.py
....................
Ran 20 tests in 0.098s
OK
```

Coverage includes the unchanged B7 focused suite plus B8 freeze integrity,
offset round trips, R0-R3 contracts, source-family isolation, deterministic
schedule counts and ceilings, cross-family shuffled controls, fail-closed
authority/identity, gold-blind callback requests, append-only 504-row fake-call
ledger behavior, and incomplete-evaluation handling.

`git diff 2a83afd --name-only` is restricted to the new B8 experiment package,
`track_2a/src/uzh_rsd/b8.py`, and `track_2a/tests/test_b8.py`. Thus B0-B7 remain
byte-for-byte unchanged relative to the branch base.

## What remains

Before any future call, an owner must approve a protocol-bound teacher provider
and immutable revision, privacy/data processing, and spend; the runtime operator
must re-attest the GGUF bytes, llama.cpp build, and localhost endpoint. A later
result must preserve the B7 negative finding and may claim Apertus transfer only
if the frozen promotion gate passes on evaluation families.
