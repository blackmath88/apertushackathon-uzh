# B2 projection-cap experiment — frozen-pilot-replay

P0 is the frozen 40-token strict projector. P1 changes only the predeclared cap to 160. P2 is infeasible because responses carry no offsets; none were invented.

| Variant | DE | FR | IT | Macro | matched | unmatched | too long | ambiguous | coverage |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P0 | 0.354985 | 0.074941 | 0.095206 | 0.175044 | 62 | 18 | 14 | 1 | 9/9 |
| P1 | 0.332990 | 0.130489 | 0.112702 | 0.192060 | 76 | 4 | 0 | 1 | 9/9 |

Recovered over-cap excerpts under P1: **14**; over-cap excerpts still unmatched after validation: **0**.

Inference: 9/9 returned; 0 hit the completion limit; 8667 prompt and 4682 completion tokens; 149.812 s total, 15.446 s median, 31.253 completion tokens/s; monetary cost $0.

Projection changes do not establish improved semantic reasoning: both variants replay identical model decisions.

## Cases

- **improvement:** `admin_fr_136` P0=0.011162752103378531 P1=0.43674299137760975 delta=0.4255802392742312; failure attribution: projection if diagnostics differ, otherwise semantic decision/scoring. Full bounded passages, decision, and diagnostics are in `analysis.json`.
- **regression:** `admin_fr_197` P0=-0.06344421976908131 P1=-0.2681950806574019 delta=-0.20475086088832056; failure attribution: projection if diagnostics differ, otherwise semantic decision/scoring. Full bounded passages, decision, and diagnostics are in `analysis.json`.
- **unchanged_failure:** `admin_fr_43` P0=-0.09260029490963885 P1=-0.09260029490963885 delta=0.0; failure attribution: projection if diagnostics differ, otherwise semantic decision/scoring. Full bounded passages, decision, and diagnostics are in `analysis.json`.
