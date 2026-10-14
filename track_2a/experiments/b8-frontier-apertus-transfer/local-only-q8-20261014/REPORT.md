# B8 local-only execution report

Recorded 2026-10-14 CEST. Verdict: **INCONCLUSIVE** for the frozen frontier-to-Apertus
transfer claim. No frontier teacher identity or authorization existed, so all
teacher and teacher-derived calls are **NOT RUN — AUTHORIZATION/PROVIDER** and
the frozen promotion gate is not evaluable. Official benchmark gain remains
**NOT MEASURED**.

## Authority and immutable scope

Coordinator amendment `msg_bec0a50ab33b` authorized an append-only local-only
erratum. The original protocol, cases, labels, and prompts were not changed.
The regenerated 504-call schedule had canonical SHA-256
`e936729c4873ddb6c3bfaf928c6b6eb86c2ae8817f762de0f104af71f8694709`.
Before inference it was deterministically filtered to 234 unchanged student
rows: 72 matched-direct R0-R3, 144 controls, and 18 deterministic/no-teacher
transfer calls. Its canonical SHA-256 is
`61bea1f9c939a07b114dbfe8fdf11197cc47d62a3be61f1b7725b4e9b44bf45d`;
the JSONL file SHA-256 is
`51f18468766195d04ff7a8c168f8cc2d86eb602b38d026457d2c54d3ce7002ca`.

## Runtime and ownership

The model was the existing 8,567,121,856-byte Apertus-v1.5-8B Q8_0 GGUF with
SHA-256 `dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d`.
The server binary SHA-256 was
`d0538ae0a50a97ede6c4fece9054ed8d3b891a82e230a1defe810249ee7b93f1`
from llama.cpp commit `7ab4ee7baad2d920464cbacfad4f4b07cf111fd2`. The owned process was PID
37328/start-ticks 129984, user `achim`, bound only to `127.0.0.1:11436`, with
SYCL0, 99 GPU layers, context 8192, parallel 1, and flash attention. Endpoint
metadata independently reported alias `Apertus-v1.5-8B-Q8_0`, ftype Q8_0, and
8,054,976,576 parameters.

Only PID 37328 was stopped through its owned execution session after its
identity and health were rechecked. PID 37328 exited and port 11436 closed.
Morrow remained PID 1240/start-ticks 8199 on port 11435 with health `ok`; its
audit file stayed exactly 226,985 bytes, mtime 1791300964, and SHA-256
`ccb4f592dff43df8553460262cec2ec14f1e864e2c1a29271ee0ad77f2c43ab2`
before and after. Morrow was neither signalled nor mutated.

## Exact execution accounting

- Calls: 234 planned, 234 attempted, 234 HTTP 200, 0 failures, 0 retries.
- Prompt tokens: 31,122 frozen estimate; 24,601 backend-reported actual.
- Completion tokens: 468 backend-reported actual.
- Wall time: 75.43712814200012 seconds.
- Summed request latency: 75.39317450900103 seconds; median 0.307616086,
  mean 0.322193053, p95 0.380858568, maximum 1.029501370 seconds.
- Raw ledger: 234 rows, SHA-256
  `ddd47339d4394cd28c0d2799579f5e7d14731f37ad5901e97a0d3b3c0df33c83`.

Every row preserves the prompt, plan, request and raw-output hashes; full raw
backend response; HTTP status; usage; latency; error field; expected relation;
and configuration. Ordered call IDs, all plan hashes, and all prompt hashes
match the frozen derivative.

## Results

Direct exact accuracy / valid-output rate was R0 0.3333 / 0.5000, R1 0.6111 /
0.8333, R2 0.7222 / 0.8889, and R3 0.6667 / 0.8333. Family-clustered 95%
bootstrap intervals for accuracy were R0 [0.0556, 0.6667], R1 [0.3333,
0.8889], R2 [0.3889, 1.0000], and R3 [0.3333, 1.0000]. The deterministic
no-teacher contract reached 0.7778 accuracy and 1.0000 valid rate, a +0.0556
point estimate over unchanged R2, with family-clustered interval [0.4444,
1.0000]. These wide, overlapping intervals cover only six evaluation families.

The frozen control inputs were label stability 0.8889 (threshold 0.85), passage
order stability 0.7222 (below 0.85), and source sensitivity 0.0000 (below 0.75).
Across all arms, only 183/234 outputs were valid single opaque labels (0.7821):
49 responses stopped at the two-token length cap, chiefly `C=` or `A=`, and two
returned `equivalent`. They remain invalid exactly as captured; no output was
repaired or retried.

The local-only data therefore suggest R2 is materially better than R0 on this
synthetic set and that the deterministic contract has a small positive point
estimate, but the declared transfer claim cannot be supported without the
unrun teacher arms. Independently, passage-order and source-sensitivity controls
fail their frozen thresholds, so this run supplies no basis for promotion,
submission, deployment, benchmark transfer, or changing the B7 conclusion.
