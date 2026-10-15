# Audit supplement — run `20261012T062327Z-ff965461`

Accounting diagnostic re-read from frozen raw responses with unchanged parsers. No scores; not a new experiment.

- raw.jsonl sha256 `d0e49eac0a9f917d47ca700a41a69fe4c16a73000326185aeae8a40aa0b68f8c`; run directory unchanged: True
- code commit `67b732605a90fa3bd44be8f5598787c63b73dc35` (src dirty: False); invocation: `python -m uzh_rsd.cli audit --run results/20261012T062327Z-ff965461`

## B0

- Documents 9; parseable 3; strictly valid 0.
- Unparseable by finish reason: {'stop': 3, 'length': 3}.
- In parseable documents, 46 of 541 tokens fell back to "no difference"; 9 tokens got a model `-1` label (scored 0).

## B2 (units: item = one `differences` entry; excerpt = one side of a valid item)

- Items 41: projected_complete 30, projected_partial 4, unprojected 7.
- Excerpts 82 (= 2 × valid items): ambiguous (subset of located) 1, empty 2, exact 62, not_found 4, too_long 14.
- Excerpt cap: 40 whitespace tokens; longer excerpts are counted `too_long` and not located.
- `projected_complete`: every non-empty excerpt located. `projected_partial`: one side located, the other not found or over the cap. `ambiguous` is a subset of located excerpts, not an extra category.

Item side combinations (each valid item counted once):

| a + b match | items |
|---|---|
| empty + exact | 2 |
| exact + exact | 28 |
| exact + not_found | 2 |
| exact + too_long | 2 |
| not_found + not_found | 1 |
| too_long + too_long | 6 |

| Document | items | complete | partial | unprojected | not_found excerpts | too_long excerpts | ambiguous excerpts |
|---|---|---|---|---|---|---|---|
| admin_de_43 | 4 | 4 | 0 | 0 | 0 | 0 | 0 |
| admin_de_136 | 7 | 6 | 0 | 1 | 0 | 2 | 0 |
| admin_de_197 | 4 | 3 | 0 | 1 | 0 | 2 | 1 |
| admin_fr_43 | 4 | 1 | 2 | 1 | 4 | 0 | 0 |
| admin_fr_136 | 8 | 5 | 2 | 1 | 0 | 4 | 0 |
| admin_fr_197 | 2 | 1 | 0 | 1 | 0 | 2 | 0 |
| admin_it_43 | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| admin_it_136 | 7 | 6 | 0 | 1 | 0 | 2 | 0 |
| admin_it_197 | 2 | 1 | 0 | 1 | 0 | 2 | 0 |

Per-item detail (excerpt sha256 and token length, no text) is in `audit_supplement.json`.
