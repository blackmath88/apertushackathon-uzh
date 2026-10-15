# B8 pre-inference feasibility audit

Recorded 2026-10-14 CEST in the isolated branch
`blackmath88/b8-frontier-apertus-transfer`, based at `2a83afd`.
No inference, frontier/cloud call, download, training, submission, deployment,
merge, Weavr mutation, or Morrow mutation was performed.

## Handoff and scientific boundary

Draft PR #26, "Handoff: Oct 14 submission readiness, S2 review and
proposition-context hypothesis", is docs-only at exact head
`2a83afdc3e6238cd6d37da395b80e212a62bbb13`. It preserves B7's unsupported
verifier finding and requires separate approval for B8. B8 therefore remains a
pre-inference package. It does not reinterpret B7's 0.7917 synthetic primary
accuracy or 0.5417 label-permutation stability as support.

## Local runtime audit

| Item | Observed evidence | B8 decision |
|---|---|---|
| Apertus GGUF | 8,567,121,856 bytes; SHA-256 `dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d`, recomputed locally | exact required student identity |
| llama.cpp | B7 verified commit `7ab4ee7`; existing binary under `/home/achim/.local/lib/morrow/llama.cpp/bin` | exact required build; no repair or launch |
| Apertus endpoint | no listener on `127.0.0.1:11436` | expected pre-inference state |
| Morrow | existing Qwen process on `127.0.0.1:11435` | protected; not signalled, changed, or queried |
| llama binary probe | exited before startup because `libsvml.so` was not in this shell's loader path | no repair attempted; not a model call |
| storage | 341 GiB free | sufficient; zero downloads allowed |

The prior B7 runtime record independently binds the same GGUF hash, llama.cpp
commit, and endpoint. A later authorized run must re-prove all three before its
first student call and must fail closed on any mismatch.

## Data and rights

All 27 pairs are newly authored synthetic administrative examples. They contain
no SwissGov-RSD test text, path, filename, identifier, metadata, label, or
derived content and no live-site/private capture. Provenance is stored per case.
Review status is uniformly `provisionally_reviewed`; the value
`human_verified` is forbidden by validation until an independent documented
review occurs.

Families, not individual language variants, are the split unit: three families
are optimization-only and six are evaluation-only. This prevents DE/FR/IT
siblings of the same semantic template from crossing the experimental boundary.

## Resource feasibility

The complete schedule is constructed without model access and must remain at or
below 600 total calls, 120,000 estimated prompt tokens, and 2,700 projected
sequential seconds (45 minutes). The dry-run ledger records each planned call,
model role, family split, representation, control, and estimate. The bounded
runner checks the ceilings before call 1 and again before every injected call;
it permits one attempt and no retry.

The teacher provider/model revision, external-data authorization, and spending
authority are deliberately unresolved. This is a hard execution blocker, not a
default provider choice. The local Apertus endpoint is also stopped. These facts
do not block schedule validation, schema validation, or offline evaluator tests.
