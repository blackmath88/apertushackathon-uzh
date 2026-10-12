# Results — 20261012T062327Z-ff965461

Dev manifest `61e0e98b7a93…`: 9 documents; 3 have valid output from every method. Small pilot sample: differences between methods are **not** statistically established.

## Matched documents (like-for-like comparison)

| Method | EN–DE | EN–FR | EN–IT | Macro | Docs |
|---|---|---|---|---|---|
| B0 | 0.143 | 0.133 | 0.132 | 0.136 | 3 |
| B2 | 0.324 | -0.093 | 0.183 | 0.138 | 3 |

## All valid documents per method

| Method | EN–DE | EN–FR | EN–IT | Macro | Docs |
|---|---|---|---|---|---|
| B0 | 0.143 | 0.133 | 0.132 | 0.136 | 3 |
| B2 | 0.355 | 0.075 | 0.095 | 0.175 | 9 |

## Paper protocol (missing documents scored as zero difference)

| Method | EN–DE | EN–FR | EN–IT | Macro | Docs |
|---|---|---|---|---|---|
| B0 | 0.318 | 0.177 | 0.310 | 0.268 | 9 (6 zero-filled) |
| B2 | 0.355 | 0.075 | 0.095 | 0.175 | 9 (0 zero-filled) |

## Coverage and usage

| Method | Status | Calls | Prompt tok | Completion tok | Latency total / median (s) | Truncated |
|---|---|---|---|---|---|---|
| B0 | ok 3, unparseable 6 | 9 | 20057 | 22945 | 732.800 / 86.300 | 3 |
| B2 | ok 9 | 9 | 8667 | 4682 | 149.800 / 15.400 | 0 |

B0 parsing: 0 strictly valid documents; 46 of 541 tokens in parsed documents fell back to 'no difference' (upstream fallback similarity 5).
B2 spans: 41 items, 34 projected; excerpts located exactly 62, normalised 0, not found 4, ambiguous 1; invalid items 0, invalid severity 0, unknown kind 0.

Spearman: global token-level per language, gold punctuation masked; official evaluator cross-check included (`official_spearman` in results.json).
