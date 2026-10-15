# B4 — Alignment-First SDM comparison

## Decision

Address **token-level projection next**. Exact positive locations with binary severity retain macro Spearman 0.999284, but perfect sentence broadcast drops to 0.534211 and eight-passage broadcast to 0.378722. This is a much larger controlled loss than severity quantisation, and it explains why another passage classifier cannot by itself solve the official token-ranking objective.

Alignment is the second bottleneck: gold-blind continuous DiffAlign improves over the identical-ID B2 full-sample baseline but reaches only 0.187117. Explicit counterpart evidence and better structural alignment are justified; another semantic classifier is not. The subsequently authorized Experiment C capability probe showed that local one-token scoring works, but its control instability does not change this decision.

## Experiment A — oracle representation bottleneck

All rows cover 30/30 documents. Spearman is global over official non-punctuation positions per language; macro is the unweighted mean. `Ties` is the number of evaluated positions beyond distinct prediction values; AP treats gold `> 0` as positive and score ties as one threshold.

| Variant | Granularity | DE | FR | IT | Macro | Ties | AP |
|---|---|---:|---:|---:|---:|---:|---:|
| A0 exact gold | token | 1.000000 | 1.000000 | 1.000000 | 1.000000 | 18,479 | 1.000000 |
| A1 exact locations, binary | token | 0.999764 | 0.999430 | 0.998659 | 0.999284 | 18,483 | 1.000000 |
| A2 three severity buckets | token | 0.999987 | 0.999979 | 0.999967 | 0.999978 | 18,481 | 1.000000 |
| A3 sentence maximum | sentence | 0.590343 | 0.564572 | 0.447718 | 0.534211 | 18,479 | 0.363204 |
| A4 passage maximum | ≤8 passages | 0.428327 | 0.345583 | 0.362255 | 0.378722 | 18,479 | 0.228729 |
| A5 expand 1 | span +1 | 0.894990 | 0.926347 | 0.871767 | 0.897701 | 18,479 | 0.858378 |
| A5 expand 3 | span +3 | 0.776019 | 0.762525 | 0.676254 | 0.738266 | 18,479 | 0.604266 |
| A5 expand 5 | span +5 | 0.707316 | 0.672036 | 0.586678 | 0.655344 | 18,479 | 0.491715 |
| A6 contract 1 | span −1 | 0.675070 | 0.759974 | 0.661478 | 0.698841 | 18,479 | 0.538020 |
| A6 contract 3 | span −3 | 0.386728 | 0.383929 | 0.355172 | 0.375276 | 18,479 | 0.197447 |
| A7 soft boundary decay | soft span | 0.725087 | 0.711405 | 0.665337 | 0.700610 | 18,454 | 0.955998 |
| A8 continuous salience | token | 0.999984 | 0.999913 | 0.999743 | 0.999880 | 18,442 | 1.000000 |

A8 is an oracle diagnostic, not a B feature: it uses known positive positions and severity, then applies deterministic token salience. Its near-perfect result says the simple salience modulation does not improve on exact locations; it does not establish a deployable model.

## Experiment B — alignment-only continuous baseline

| Method | DE | FR | IT | Macro | Coverage | Apertus calls | Measured latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 existing Q8 paper protocol | 0.317790 | 0.176608 | 0.309881 | 0.268093 | 9 docs, different manifest; 6 zero-filled | 9 | 732.8 s |
| B2 P1 existing Q8, parseable only | 0.135377 | 0.115968 | 0.289035 | 0.180127 | 17/30 semantic outputs | 30 | 680.789 s |
| B2 P1 full-sample default zero | 0.084140 | 0.108130 | 0.195647 | 0.129306 | 30/30 vectors; 17/30 semantic outputs | same 30 | same run |
| B3 Q8 full-sample default zero | 0.140951 | 0.136499 | undefined | undefined | 30/30 vectors; 0/30 complete decisions | 219 | 442.221 s |
| **B4 DiffAlign** | **0.217865** | **0.135347** | **0.208138** | **0.187117** | **30/30** | **0** | **0.163 s replay** |

B0 is not a like-for-like 30-ID comparison: no B0 run exists for this frozen manifest, and the historical nine-document evidence was not rewritten. B2 and B3 rows are the identical 30 IDs. BF16/HF and local Q8 results are not mixed.

B4 uses 18,485 evaluated tokens, masks 2,669 official punctuation positions, has 5,971 ties, and achieves positive-token AP 0.203888. Local replay used 0.162916 wall seconds, 0.161673 CPU seconds, and 124,424 KiB maximum resident memory. These figures exclude upstream Qwen encoder generation; the published artifacts do not report its hardware or latency.

## Failure examples

- `admin_fr_58` has defined per-document rho 0.040309. DiffAlign ranks ordinary `Federal`, `staff`, and `chief` highly, while annotated differences around `Rossi`, `married`, and `and` receive low anomaly scores. Repeated biographical vocabulary creates plausible but wrong maxima.
- `admin_it_167` has rho 0.077837. Unchanged function words (`but`, `in`; Italian `modo`, `confrontano`) score high, while changed date tokens such as `2025`, `03`, and `2018` score low because matching numeric forms exist elsewhere in the documents.
- `admin_de_140` has rho 0.085928. Generic words (`both`, `then`, `part`) are false-high, while the annotated date change receives low scores. Global all-to-all maxima confuse repeated boilerplate/numbers and motivate explicit structural links.
- Five documents have undefined per-document rho because their gold vector is constant, not because B4 omitted predictions. They remain in the per-language global denominator; undefined document correlations are reported, never imputed.

## Experiment C capability verdict

After A and B were frozen, the coordinator authorized a capability-only probe. Native inspection preceded inference: llama.cpp exposed `/health`, `/v1/models`, `/props`, `/tokenize`, `/apply-template`, chat completions, JSON-schema/grammar controls, and top-token log-probabilities. Labels `0`, `1`, and `2` are each exactly one token (IDs 1048, 1049, and 1050), and the applied chat template begins generation directly after the assistant marker. Grammar was deliberately not used because it renormalizes over the allowed set and would make label probabilities conditional rather than preserve the model's unconstrained distribution. These behaviors follow the official [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/tree/7ab4ee7/examples/server) and were verified against commit `7ab4ee7` before calls.

The frozen smoke set contains four development-only pairs (two equivalent, two different) and four conditions: base, reversed passage order, rotated label mapping, and both controls together. Each condition was attempted once, without rationale or prompt search: 16 calls total against the permitted 24-call ceiling, no retries, and no test data.

| Condition | Accuracy | Calls | Valid one-token outputs |
|---|---:|---:|---:|
| Base | 0.75 | 4 | 4/4 |
| Order reversed | 0.75 | 4 | 4/4 |
| Labels rotated | 0.75 | 4 | 4/4 |
| Order reversed + labels rotated | 0.50 | 4 | 4/4 |

All 16 top-20 lists contained the three candidate labels. Semantic stability was 0.875 under order reversal and 0.875 under label permutation: one of eight paired decisions changed for each control. The honest verdict is **operational but not benchmark-ready**. Native unconstrained one-token probabilities are extractable, but this tiny capability probe is not an accuracy estimate and the observed control sensitivity argues against promoting Experiment C to a benchmark method.

The 16 calls took 5.703686 wall seconds (0.314765-second median request) after approximately 6.96 seconds of model startup, using local Apertus-v1.5-8B Q8_0 on `SYCL0`; no cloud or paid compute was used. The isolated server bound only to `127.0.0.1:11436` and was stopped immediately afterward. Morrow remained at the same PID 1240 on loopback port 11435 and was not touched.

## Reproduction and integrity

See `README.md` for exact commands. Every output vector has exact official-token length and finite `[0,1]` values. The code validates the frozen manifest byte hash, text and gold fingerprints, upstream IDs/text/lengths, upstream file SHA-256, evaluator file hashes, and output-directory immutability. Gold is absent from the B prediction loader's API and joined only for scoring. Experiment C records complete prompts, raw outputs, label log-probabilities, timings, model and runtime pins, and content hashes; its code refuses non-dev splits, non-loopback endpoints, any port other than 11436, and output overwrites.
