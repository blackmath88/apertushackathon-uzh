# Nebu staged comparison — post-submission research

Status: **Stages 0–2 complete; STOPPED BEFORE GATE A.** This work began from
`da846de` on an isolated branch after the 16 October 2026 12:00 CEST deadline.
It does not alter or make a claim about any submitted snapshot.

## Frozen design

- 163 complete three-language source groups were verified by exact shared
  upstream `page_en` identity, then published only as SHA-256 group keys.
- Exploration: 12 groups / 36 pairs, four groups per short/medium/long stratum.
- Reserved validation pool: 18 disjoint groups / 54 pairs; the first four per
  stratum (12 groups / 36 pairs) were committed for the one validation pass.
- C0 was unchanged `b2-spans-v1`. C1 inserted only the pre-existing P1
  semantic-commitments block. C2 was omitted because no safe existing
  chunk/merge implementation was available.
- Exact schedule: 72 exploration calls plus 36 validation calls; 108/120
  request ceiling, one in flight, no retries, 600 s per request and 3,600 s
  per inference stage.

## Exploration and selection

All 72 cold requests returned and settled in 1,545.241 s. C0 and C1 each had
21/36 usable outputs. C0 scored 0.0129638366 and C1 scored 0.0049155952 on the
fallback-labelled all-subset macro; saved B0 scored 0.0003516384 on the same
36 pairs. C1 used 56,277 prompt and 24,699 completion tokens in 738.220 s;
C0 used 51,345 prompt and 26,924 completion tokens in 806.978 s.

C0 led C1 by 0.0080482414, within the predeclared 0.01 tie band. With equal
usable coverage, the lower measured uncached inference time selected C1. This
is a practical heuristic result, not evidence that C1 is semantically better.
C1 was frozen at commit `f234c0a` before validation.

## One validation pass

All 36 cold C1 calls returned and settled in 766.372 s. Thirteen ended at the
1,024-token output limit and were malformed. Coverage was:

| Method | Intended | Attempted | Returned | Parseable / usable | Strictly valid | Partial projection | Context overflow | Malformed | Transport / unresolved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Saved B0 | 36 | 25 | 25 | 3 | 0 | n/a | 11 | 22 | 0 / 0 |
| C1 | 36 | 36 | 36 | 23 | 14 | 9 | 0 | 13 | 0 / 0 |

Fallback-based official token-level Spearman on the identical 36 pairs:

| Method | EN-DE | EN-FR | EN-IT | Macro |
|---|---:|---:|---:|---:|
| Saved B0 | -0.008251 | 0.024478 | -0.011238 | 0.001663 |
| C1 | -0.026986 | 0.047493 | -0.060244 | -0.013246 |

The macro difference C1 minus B0 is **-0.014909**. The 2,000-replicate,
source-group bootstrap (seed 0) gives CI95 `[-0.104397, 0.066298]`; 818
replicates were defined and 1,182 were undefined because small resamples could
produce constant language vectors.

On the shared usable set, only one document per language remained. C1 scored
0.006275 versus B0 -0.031019 (difference +0.037293), with zero fallback tokens.
That denominator is too small to support a semantic improvement claim.

Verdict: **operational coverage improved; semantic improvement is not
supported.** The all-subset point estimate is worse, the uncertainty interval
crosses zero, and the shared-usable result is based on only three documents.

## Cost and runtime

Validation C1 used 61,951 prompt and 25,414 completion tokens. Summed endpoint
latency was 766.346 s, median 22.151 s and p95 32.807 s; there were no cache
hits. Across all 72 measured C1 calls, prompt/completion totals were
118,228/50,113, summed latency 1,504.566 s, median 21.308 s and p95 32.387 s.

The saved B0 ledger on the validation IDs records 25 endpoint attempts,
65,040 prompt and 65,006 completion tokens, 2,005.033 s summed latency, 72.624
s median and 133.046 s p95. Eleven other cases were deterministic context
overflows and made no endpoint call.

## Gate A estimate — not authorized

C1 uses one full-document request per case and no chunking. A stratum-weighted
projection from the 72 measured C1 calls estimates the exact 489-case manifest
at 489 calls, about 800,770 prompt plus 339,360 completion tokens, and 2.830 h
of inference. Reserve **3.538 h** wall time with a 25% margin.

Exact cache reuse covers 72 already-generated C1 cases. The incremental Gate A
work would therefore be 417 new calls, approximately 682,542 prompt plus
289,247 completion tokens and 2.412 h inference; reserve **3.016 h** with the
same margin. Default state is **WAITING FOR OWNER GO**. No full-development or
test inference has been launched.

## Integrity and review

- Baseline predictions SHA-256: `954d4698f4b8a3cf5b4ed11727e840cc81776798961748d9023256c079242a06`.
- Exploration predictions SHA-256: `b23e7a4e88fb3cd9730b7088082c8b7bcdb5820097cf2a4e63af3a86314389b1`.
- Validation predictions SHA-256: `2fb6bf82ed3f17f3edd2a833789a5860f106128a40855e7381acc13359ac7805`.
- Exploration private ledger SHA-256: `5cf1855640abfefebc639bf76abc3eacd68f3bd2c4df6bcfde3bc24cf22de420`.
- Validation private ledger SHA-256: `01b2b35fce36d80197b82c09dcf8056ea5f5efb5efccf7e329d5f8f0596bbf51`.
- Installed model/server hashes matched PR #40 evidence; llama.cpp `7ab4ee7`,
  Q8_0, 8,192 context, one slot and the embedded chat template were captured.
- Raw prompts, responses, cache and gold stayed ignored/private. Published
  predictions contain only IDs, statuses and numeric vectors.
- The dependency-complete offline suite passed 331/331 tests. A fresh
  exploration and validation re-score reproduced both predictions and summary
  files byte-for-byte. The first system-Python suite attempt had eight
  dependency-only import errors (NumPy/Hugging Face); no dependency was added.
- The transient Apertus service was stopped and port 11436 verified closed.
  Morrow remained PID 1477 on port 11435 with the same start time and command.
- Review is self-review. No independent review route was used.
