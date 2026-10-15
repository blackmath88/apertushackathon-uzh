# B2 projection-cap experiment — local-q8-fixed-b2

P0 is the frozen 40-token strict projector. P1 changes only the predeclared cap to 160. P2 is infeasible because responses carry no offsets; none were invented.

| Variant | DE | FR | IT | Macro | matched | unmatched | too long | ambiguous | coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P0 | 0.174778 | 0.160441 | 0.232632 | 0.189283 | 103 | 34 | 32 | 0 | 17/30 |
| P1 | 0.135377 | 0.115968 | 0.289035 | 0.180127 | 131 | 6 | 0 | 0 | 17/30 |

Recovered over-cap excerpts under P1: **28**; over-cap excerpts still unmatched after validation: **4**.

Inference: 30/30 returned; 12 hit the completion limit; 39210 prompt and 19995 completion tokens; 680.789 s total, 24.361 s median, 29.37 completion tokens/s; monetary cost $0.

Projection changes do not establish improved semantic reasoning: both variants replay identical model decisions.

## Cases

- **improvement:** `admin_fr_156` P0=-0.22617853252703585 P1=0.24036430711222617 delta=0.466542839639262; failure attribution: projection if diagnostics differ, otherwise semantic decision/scoring. Full bounded passages, decision, and diagnostics are in `analysis.json`.
- **regression:** `admin_fr_105` P0=-0.12611727195811784 P1=-0.499409332339578 delta=-0.3732920603814602; failure attribution: projection if diagnostics differ, otherwise semantic decision/scoring. Full bounded passages, decision, and diagnostics are in `analysis.json`.
- **unchanged_failure:** `admin_de_105` P0=-0.6503304946101328 P1=-0.6503304946101328 delta=0.0; failure attribution: projection if diagnostics differ, otherwise semantic decision/scoring. Full bounded passages, decision, and diagnostics are in `analysis.json`.
