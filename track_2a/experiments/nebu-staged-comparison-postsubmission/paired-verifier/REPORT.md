# Paired-evidence verifier — final bounded experiment

## Decision

**REJECT.** The verifier did not pass the frozen acceptance rule and is not part
of the delivery method. Gate A remains closed.

The protocol, exact 18-document sample, generator, verifier prompt, metrics,
failure policy and acceptance rule were committed at `0eb4194` before any call.
The sample has 6 DE, 6 FR and 6 IT documents and two source groups in each of
the short, medium and long strata. All 18 cases are now exposed development
diagnostics and are not an untouched validation set.

## Measured result

| Measure | Unchanged C1 | Verifier-filtered C1 |
|---|---:|---:|
| Official fallback-based macro Spearman | 0.061483 | 0.058056 |
| DE | 0.075107 | 0.083385 |
| FR | 0.052017 | 0.011047 |
| IT | 0.057325 | 0.079735 |
| Usable documents | 6/18 | 6/18 |

Treatment minus control is **−0.003427**. The fixed 2,000-replicate paired
source-group bootstrap interval is **[−0.016853, 0.014308]** (1,828 defined,
172 undefined replicates). The verifier returned a valid index list on every
eligible document and kept 17 of 25 proposed items.

The outcome-blind fixed audit covered the predeclared 199, 215 and 185 source
groups across all three languages. Six medium/long documents were unparseable,
so only the 14 proposed items in group 199 could be classified. The unchanged
control has supported-item precision 3/14 = **0.2143** and recall 3/3 =
**1.0000**. The verifier has TP=2, FP=9, FN=1, TN=2: precision 2/11 =
**0.1818**, recall 2/3 = **0.6667**. It therefore worsened both audit metrics.

## Coverage and runtime

- 18 generator calls; 12 ended at the frozen 1,024-token cap and were
  unparseable. These documents use the same explicit zero fallback in both
  diagnostic score arms; the verifier was not asked to repair them.
- 6 verifier calls; all valid. Total: **24 calls**, no retries and no endpoint
  failures.
- Generator: 33,500 prompt tokens, 14,197 completion tokens, 503.472 seconds.
- Verifier: 5,081 prompt tokens, 66 completion tokens, 7.053 seconds.
- Total measured request latency: **510.525 seconds**; median 23.040 seconds,
  p95 41.672 seconds. Zero paid/cloud cost.

The immutable private ledger SHA-256 is
`3c55347f6c6ac1680b004c95f18e29aca46e9a0dc4d564a8578e8dfbcf6a2020`.
The public numeric predictions SHA-256 is
`3bb12c526b074deafa74fef25b7ea65ce850a99a27a40cb3640056c7f8ec913e`.
Raw passages, prompts, responses and the audit annotation file remain ignored
under `data/private/`.

## Interpretation

This experiment repeats neither B7 nor B8: it tests the exact PR #44
paired-evidence keep/drop proposal on a fixed confirmation sample. Its failure
is consistent with those earlier diagnostics: the local Apertus verifier is
not reliably source-sensitive, and filtering cannot fix missing generator
outputs. The simpler frozen B2/C0 delivery path remains the only implemented
Apertus final path, but its known completeness failure is a delivery blocker,
not something this experiment resolves.
