# Pre-inference freeze report

Status: **COMPLETE PREPARATION / INFERENCE NOT RUN**. Date: 2026-10-14 CEST.

The checkout is branch `blackmath88/nebu-full-dev-apertus-baseline`, based
exactly on `origin/docs/nebu-full-dev-baseline-20261014` at `d6f1419`. The
protocol, complete manifest, run configuration, resumable runner, and focused
synthetic/mock tests are ready for the required freeze commit. No real model
request was made and no server was started.

## Frozen identities and accounting

- Manifest canonical SHA-256:
  `053d2ac8cf0714ba1ad1d909eb437dff1e99a5958673ac4e89bd740afa699551`;
  file SHA-256:
  `7943b068051df948dee5cfa9fb46c6f2cc7689999a208876c5a6486116fb2edf`.
- Source rows: 504. Included: 489 (163 EN-DE, 163 EN-FR, 163 EN-IT).
  Applicable official exclusions: 15. Every `(id, pair)` appears exactly once
  across included and excluded rows. The official exclusion file has 33 unique
  lines, of which 18 have no row in the pinned dev files.
- Dataset revision: `f16aa0536811b8c0cf975fede21eec5996e4b3c1`.
  Dev file SHA-256: DE `4b514141…780ccd`, FR `732ccdb2…587dd`, IT
  `e8f0dc72…07c698` (full values in `manifest.json`).
- Upstream evaluator/parser/prompt commit:
  `1807a42100e742ed03d337c54c4b9ea86995f565`. Evaluator, utility,
  exclusion-list, and all three template hashes match the pins in the
  manifest.
- Request plan: 489 calls, SHA-256
  `836855d724bea5f3015ef8230da4486d34b63e1a9aa7492ed787f0303da849e1`.
  Run-config file SHA-256:
  `9e9b00edd7ec2d75ded7b3bff02170eeaa4da45a5d8d49be6f5cb9640a3d1c91`.
- Model: Apertus v1.5 8B Text Q8_0 GGUF, SHA-256
  `dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d`.
  llama.cpp commit `7ab4ee7`; server binary SHA-256 `d0538ae0…b93f1`;
  embedded chat-template SHA-256 `d23af285…60e0` (16,614 bytes).

Private inference and scoring JSONL are separate, hash-bound, ignored
artifacts. The generation loader rejects gold-bearing fields and validates
identity, order, and text hashes against the manifest. No raw dev text is in
the tracked package.

## Budget and contracts

The dry run fits the frozen bounds: concurrency 1; 489 requests; 600 seconds
per request; 115,200 seconds total; context 8192; output cap 4096; prompt and
completion ceilings 2,002,944 tokens each (4,005,888 combined). An exact
runtime-tokenizer preflight must precede inference; overflow is recorded and
never truncated.

The durable ledger fsyncs intent before each call and result immediately after.
Only never-started entries can resume. Unresolved intents are retained and not
resent; transport/runtime failure pauses; malformed returned output is not
repaired or retried; response hashes are verified. Failure state remains
separate from the declared all-manifest numeric fallback.

## Verification

- Focused suite: **10 passed**, including split refusal before I/O, gold-field
  isolation contract, exact-length/context overflow, runtime/timeout identity,
  one-request execution, failure pause, resume, unresolved-intent refusal,
  raw-response integrity, and pinned official-evaluator parity on synthetic
  vectors.
- Repository suite: **199 passed** under the existing S1 environment.
- Manifest integration check: 504 unique accounted pairs, 489 gold-free private
  generation rows, hashes and order reproduced.
- `git diff --check`: pass. Private source/gold artifacts are confirmed ignored.

B8 settlement is recorded from commit `4cb2176`; port 11436 was closed after
its owned server exited and Morrow was unchanged. B8 remains untouched.

Next smallest action: after reviewing the freeze commit, perform the exact
tokenizer/context and endpoint-identity preflight under exclusive local runtime
ownership. That later action needs separate authority to start the existing
server and issue real requests.
