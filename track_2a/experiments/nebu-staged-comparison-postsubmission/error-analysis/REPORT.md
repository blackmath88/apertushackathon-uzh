# Offline error analysis

## Guardrails and sample

Gate A remains **closed**. This analysis made no model calls and did not read test data. It replayed only the saved C1 validation ledger (`01b2b35…`) and used development gold after prediction generation, solely for diagnostic scoring. The original responses, predictions, and scores were not changed.

The sample rule was fixed before classification: take the first two source groups in each already-frozen `validation_execution` stratum. This gives 18 documents across six source groups, exactly balanced by language (6 DE / 6 FR / 6 IT) and length (6 short / 6 medium / 6 long). `exposure-registry.json` marks every sampled case as exposed; none may again be described as untouched validation.

Each public trace records:

`input hashes/token counts → saved response hash/finish reason → parsed difference metadata → excerpt location modes/token spans → projected-vector hashes/nonzero counts → official diagnostic score`

Exact source text, response text, excerpts, and development labels remain in the ignored private trace.

## Earlier diagnostics incorporated

- B2 already tested the obvious locator-cap change. Raising the strict excerpt cap from 40 to 160 recovered all 14 over-cap excerpts in its nine-case replay, but macro moved only from 0.175044 to 0.192060 and one case regressed by 0.204751. This analysis does not repeat that experiment.
- B4 already established the representation upper bound: exact positive locations with binary severity retained 0.999284 macro Spearman, while sentence broadcast fell to 0.534211 and eight-passage broadcast to 0.378722. Exact placement matters much more than severity quantisation.

## Counts

Categories are document incidences and may overlap.

| Category | Documents | Concrete evidence |
|---|---:|---|
| 1. Truncated or malformed | 8/18 | Seven responses hit the 1024-token completion cap and were unparseable: all six long cases plus `admin_it_85`. `admin_fr_197` was parseable but contained one invalid `NO_DIFFERENCE` item with severity 0. |
| 2. Judgement wrong or unsupported | 11/18 | Every parseable case contained unsupported equivalence-as-change decisions or missed localized evidence. For example, `admin_de_27` marked 90 tokens while overlapping none of the two gold-positive positions; its per-document rho was −0.272727. |
| 3. Correct difference, excerpt not locatable | 1/18 | `admin_it_52` correctly identified omitted teaching-material content, but source excerpts of 44 and 70 tokens exceeded the frozen 40-token cap. This is consistent with, rather than a repetition of, B2. |
| 4. Correct evidence, projection imprecise | 8/18 | Among the 11 parseable documents, projection marked 1,390 positive positions against 465 gold-positive positions, with 251 overlaps: 0.180576 micro precision and 0.539785 recall. `admin_fr_85` marked 265 positions for 108 gold positives and overlapped 67. |
| 5. Scoring/token-order defect | 0/18 | Offline parsing reproduced every preserved vector exactly. Vector lengths and input hashes matched the frozen manifest. The local scorer matched the pinned official evaluator within 1.4e−17 for all three languages. |

The 11 parseable responses contained 48 difference items; 45 projected at least one side. Locator diagnostics counted six not-found sides, eight over-cap sides, three ambiguous matches, and one invalid severity. These raw locator failures are not all category 3: most arose from unsupported or model-altered excerpts rather than correct evidence.

The official score on the fixed sample, including explicit zero fallback for the seven unparseable documents, was:

| Language | Documents | Evaluated positions | Spearman |
|---|---:|---:|---:|
| DE | 6 | 2,567 | −0.074084 |
| FR | 6 | 2,902 | 0.023327 |
| IT | 6 | 2,781 | −0.066664 |
| Macro | 18 | 8,250 | **−0.039140** |

Representative traces:

- `admin_it_52` mixed categories 2/3/4: one correct omission exceeds the cap, an unrelated target passage is paired with it, and only 6 of 70 projected positives overlap 82 gold positives (rho −0.456097).
- `admin_fr_197` mixed categories 1/2/4: an invalid severity-zero item coexists with sentence-level overprojection; 147 positions are marked, 43 are gold-positive, and 35 overlap (rho 0.263472).
- `admin_it_27` mixed categories 2/4: all 25 gold positives are covered, but 132 positions are marked and the unmasked prediction is constant, making per-document Spearman undefined.

## Conclusion and one next change

The largest evidenced incidence is model judgement (11/18), not locator failure (1/18 correct-evidence case) or an implementation defect (0/18). The next change should therefore be **one post-generation paired-evidence verification gate**: apply a compact keep/drop judgement to each C1 difference and retain an item only when the two cited excerpts make a factual mismatch, not merely a translation or reordering. The verifier returns indices only; the parser, 40-token locator, severity, projection, scorer, and C1 generator remain frozen. This isolates semantic filtering and avoids re-running B2's cap experiment or changing the B4-sensitive projection machinery at the same time.

The bounded, unexecuted plan is in `NEXT_EXPERIMENT_PLAN.md`. Gate A remains closed.

