# B3 SDM local Q8 result

Scientific verdict: **NOT SUPPORTED**. B3 produced exact-length numeric vectors
for all 30 fixed dev IDs, but no document had a complete set of semantic
decisions. Only 42/219 model responses (19.18%) passed the frozen classifier
contract; 177/230 tasks became explicit `UNKNOWN`, so the apparent per-language
scores under zero default cannot establish semantic improvement.

## Coverage and reliability

| Measure | DE | FR | IT | Total |
|---|---:|---:|---:|---:|
| Documents | 10 | 10 | 10 | 30 |
| Tasks | 77 | 73 | 80 | 230 |
| Model / structural routes | 75 / 2 | 67 / 6 | 77 / 3 | 219 / 11 |
| Resolved / UNKNOWN tasks | 18 / 59 | 20 / 53 | 15 / 65 | 53 / 177 |
| Complete-document semantic decisions | 0 | 0 | 0 | 0/30 |
| Exact-length output vectors | 10 | 10 | 10 | 30/30 |

The 53 resolved tasks comprise 46 `EQUIVALENT` and seven `DIFFERENT` decisions;
11 of the equivalents are deterministic identity routes. There were no valid
`UNCERTAIN` responses/abstentions, no alignment overflow and no call failure.
Validation failures were 153 overlong rationales, 18 inconsistent relation/kind
pairs, four truncated completions and two invalid JSON responses. All are
unresolved; none was repaired. The 230 alignments comprise 44 unique-numeric
anchors and 186 proportional-order candidates. Twenty documents have positive
gold differences but no projected B3 difference, a post-decision diagnostic of
likely missed semantic differences—not an inference-time routing signal.

## Q8 comparison on the identical 30 IDs

Token-level Spearman uses official punctuation masking. `—` means undefined.
B2 parseable-only scores cover 8 DE, 5 FR and 4 IT documents. B3 has zero
complete-decision documents, so its complete-decision-only score is undefined
for every language.

| Method / view | DE | FR | IT | Macro | Semantic/vector coverage |
|---|---:|---:|---:|---:|---:|
| B2 P0, parseable only | 0.174778 | 0.160441 | 0.232632 | 0.189283 | 17/30 |
| B2 P1, parseable only | 0.135377 | 0.115968 | 0.289035 | 0.180127 | 17/30 |
| B3, complete-decision only | — | — | — | — | 0/30 |
| B2 P0, full-sample zero evaluation default | 0.118990 | 0.127443 | 0.169214 | 0.138549 | 30 vectors; 13 defaulted docs |
| B2 P1, full-sample zero evaluation default | 0.084140 | 0.108130 | 0.195647 | 0.129306 | 30 vectors; 13 defaulted docs |
| B3, full-sample zero evaluation default | 0.140951 | 0.136499 | — | — | 30 vectors; 0 complete docs |

Zero is only the declared evaluation default for missing/unresolved predictions;
it is not semantic equivalence. B3 IT is constant and therefore undefined.
The higher B3 DE/FR numbers under this policy do not rescue the hypothesis:
semantic coverage is zero and macro is undefined. This separates a projection
artifact from classifier reliability and semantic accuracy.

## Usage

| Language | Calls | Prompt tokens | Completion tokens | Aggregate latency (s) |
|---|---:|---:|---:|---:|
| DE | 75 | 21,922 | 4,446 | 154.401 |
| FR | 67 | 24,090 | 3,573 | 148.664 |
| IT | 77 | 24,878 | 4,191 | 139.156 |
| Total | 219 | 70,890 | 12,210 | 442.221 |

Median call latency was 1.925 s; measured completion throughput was 27.61
tokens/s. Wall time was 442.277 s. Cost was $0. The run stayed within 219/300
calls, 8/12 tasks per document, 96 completion tokens per call, 90 s per request
and the 35-minute global ceiling.

## Three concrete cases

**Improvement under the default policy — `admin_de_105`.** B2 P1 document
Spearman was -0.650330; B3 was 0.162464 (delta +0.812795). B3 task
`admin_de_105:04:4058f561895f` compared left `[55,60)` “Links Sektion Recht
Specialist staff” with right `[47,50)` “Links Sektion Recht” and returned
`DIFFERENT/OMISSION`. The other four tasks were unresolved, so this is a partial
classification/projection effect under zero default, not a complete-document
semantic success.

**Regression — `admin_de_43`.** B2 P1 document Spearman was 0.324328; B3 was
-0.136813 (delta -0.461142). Proportional alignment split a URL: task
`admin_de_43:06:9e265afa74e1` compared left `[83,85)` “admin .” with right
`[83,85)` “stelle .” and returned `DIFFERENT/ENTITY_CHANGE`; the neighbouring
task marked “stelle .” versus “Links www .” as an omission. This is primarily
an alignment failure that induced false classification and projection effects.

**Unchanged failure — `admin_de_223`.** Both B2 P1 and B3 document Spearman are
undefined because their projected vectors are constant. B3 correctly resolved,
for example, left `[39,53)` “Habitats and ecosystems not only provide shelter
to abundant animal and plant life .” versus right `[37,50)` “Lebensräume und
Ökosysteme beherbergen nicht nur eine reiche Tier - und Pflanzenwelt .” as
`EQUIVALENT/NONE`, but five of eight document tasks remained unresolved. This
is a reliability/coverage failure; neither alignment nor projection supplies a
complete semantic decision.

## Reproduction and controls

Re-score without inference:

```sh
PYTHONPATH=track_2a/src track_2a/.venv/bin/python -m uzh_rsd.sdm.experiment score \
  --manifest track_2a/experiments/b3-sdm/task-manifest.json \
  --run track_2a/experiments/b3-sdm/local-q8-20261013
```

The official test split was neither enumerated nor accessed. No HF job, cloud
endpoint, fallback model, retry, paid compute, Zürich crawl or city data was
used. Frozen B2 checksums verified before and after the run.
