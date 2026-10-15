# B7 feasibility audit

Recorded 2026-10-13 CEST before B7 scoring or inference. The checkout is branch
`blackmath88/b7-structural-semantic-verification` at exact base
`39f710194f29260a931d1e5fad1890617b7970d2`. No Observatory snapshot exists.
`.weavr/staged/intake.json` is staged-not-applied, SHA-256
`8fd9f687d0db83b3cc24593448fba9da0067d4fccabb9d4d4994ea5b58648c70`, and is out of scope.

| Component | Existing artifact | Missing dependency | Cost | Decision |
|---|---|---|---|---|
| Frozen 30-document dev sample | B2 manifest `523306be…a4c5`; S1 manifest `e837c959…6bce` | none | offline | use only these 30 IDs |
| Annotation provenance | pinned SwissGov-RSD dev revision `1807a42100e742ed03d337c54c4b9ea86995f565`; B4 validation includes German | none | offline | accepted, revalidate through existing loader |
| Official evaluator/tokenization | pinned evaluator hashes in B4; whitespace official tokens and punctuation mask | none | offline | unchanged |
| Published B4 | prediction SHA-256 `54e30793…180`; macro 0.1871166581 | original encoder revision absent | offline | S0/E0 unchanged, never substitute regenerated scores |
| Regenerated B5 M0 and matrices | 30 `officialmap-v2` NPZ files, 37,873,365 bytes; all hashes match committed provenance | cache lives read-only in isolated B5 worktree | offline, <2 min CPU ceiling | S1/E1 and S2 feasible; no embedding regeneration |
| B6 routing | selector SHA-256 `089848b9…e228`; results record NOT SUPPORTED | none | offline | preserve; use actual B5 route as R1, do not relabel B6 |
| Shared-English families | frozen family key is terminal document index; 27 clusters, no complete DE/FR/IT sibling set | complete sibling families absent | offline | cluster bootstrap and leave-one-family-out only |
| CTFAlign | upstream package commit `30f4f89cfcbb150cbf0497884e95c5598198a58c`; paper configuration width 8, argmax | no runtime dependency needed; NumPy translation tested | offline | feasible against existing B5 matrices |
| Apertus v1.5 8B Q8_0 | `/home/achim/.local/share/apertus-local/models/apertus-v1.5-8b-text-q8_0.gguf`, 8,567,121,856 bytes, SHA-256 `dea904ad…202d` | port 11436 server not yet started | local only, zero monetary cost | run independent Phase 5 |
| llama.cpp | verified prior commit `7ab4ee7`; binary `/home/achim/.local/lib/morrow/llama.cpp/bin/llama-server` | requires existing oneAPI library environment | one focused repair + one alternative maximum | start only on 127.0.0.1:11436 |
| Machine | Intel Arc Pro B60, 31 GiB RAM (21 GiB available), 341 GiB disk free, 16 CPU threads | VRAM sysfs counter unavailable | local | sufficient based on verified earlier Q8 run |
| Morrow | PID 1240, user `achim`, Qwen3-14B, healthy on 127.0.0.1:11435 | none | protected | never stop, reconfigure, or signal |
| Optional compact comparator | no separately pinned compatible checkpoint in scope | licence/runtime validation would expand dependencies | exceeds zero-download ceiling | E4 not measured/inapplicable |

The B5 matrix cache is scientifically reusable because each of its 30 current
bytes hashes matches `b-embedding-provenance.json`, whose source evidence hash
is `8a0747e5…c10`. B7 reads that cache by absolute path without writing to the
B5 worktree. The engineering ceiling for S2 is one implementation, one focused
repair, two CPU minutes, and no encoder invocation; failure would mark S2
blocked without affecting the synthetic Apertus phase.

Submission readiness remains blocked as described in PR #12; B7 does not touch
submission inputs, outputs, services, or the protected official test split.

