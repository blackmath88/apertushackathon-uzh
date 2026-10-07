# SwissGov-RSD Benchmark Notes

Verified in S1 against the pinned dataset revision and evaluator commit (see
[SOURCES.md](SOURCES.md)). Items marked *unverified* are still assumptions.

## Task

Given two related documents in different languages, predict a semantic-difference score for each benchmark token. Symmetric differences and asymmetric ones (additions, omissions) are in scope.

Evaluated pairs: EN–DE, EN–FR, EN–IT.

Primary metric (UZH brief): token-level Spearman per language pair, macro-averaged over the three pairs. Secondary: computational efficiency, innovation/creativity.

## Data (verified)

HF `ZurichNLP/SwissGov-RSD` publishes `data/<lang>/dev_<lang>.jsonl` and `test_<lang>.jsonl`. Dev holds 168 documents per language. The same 168 English documents are paired with DE, FR and IT (multi-parallel). Fields per record: `id` (`admin_<lang>_<n>`), `text_a` (EN), `text_b`, their `_untokenized` variants, `labels_a`, `labels_b`, `page_en`, `page_other`, `subset`.

Dev token totals (whitespace tokens): EN 65,320 per pair; DE 61,101; FR 77,585; IT 71,008. Per-side length ranges from 60 to 1,993 tokens. Every dev label vector has exactly one value per whitespace token; no dev document has a fully masked side b.

All dev sources are federal (`admin.ch` domains: bfe, bk, sbfi, seco, uvek, bakom, www). No document is cantonal, so a canton pilot needs external material (S4).

## Gold representation (verified)

Tokens are `text.split()` (Python whitespace split) on the stored text. `tokens.py` reproduces this and adds character offsets.

Gold labels are already **difference** scores in [0, 1]; `-1` marks punctuation. Gold is never a similarity scale.

## Official evaluation (verified, `scripts/evaluate_predictions_admin.py`)

Per language:
1. Load predictions and gold.
2. If a prediction vector is shorter or longer than gold, **pad with 0.0 or truncate** (and count it).
3. Concatenate `labels_a` for every document, and `labels_b` unless the gold `labels_b` is entirely `-1`.
4. Drop positions whose gold label is `-1`.
5. Compute global Spearman and Kendall with `nlpstats.correlate(level="global")`, plus a 1-resample bootstrap interval.

Observed behaviours that our wrapper handles explicitly:
- The script prints per-language values only. **There is no macro average in the code**; `evaluation.macro_average` adds the brief's macro mean and refuses when a language is missing or undefined.
- `--split` defaults to `full`, and `full` contains test gold. Our code never calls the script's `main`, never reads `full`, and passes only dev gold.
- When the split gold is shorter than the predictions, the script re-reads `gold_labels/full` to filter. Our wrapper avoids that path.
- **Constant prediction vectors crash the official code.** The `nlpstats` bootstrap gets only NaN samples and `np.percentile([])` raises `IndexError`. This reproduces under both the official pins (numpy 2.0.2, scipy 1.13.1) and our lock. Our evaluator returns `None` with a reason instead of a number.
- Length repair is replaced by `LengthMismatchError`. Exact-length predictions are a precondition.
- LLM prediction files have ids in `list_to_drop.txt` (34 ids) removed before scoring. The UZH brief does not say whether final judging drops them (Need N-RULES-2).

Parity: `tests/test_s1_evaluation.py` executes the pinned `compute_correlations` against our implementation. It covers hand fixtures, 25 seeded random vectors with heavy ties and masking, and real dev gold with synthetic predictions for all three languages plus the macro average. Agreement is at 1e-10 or tighter.

## Scale reconciliation (verified)

| Scale | Range | Meaning | Where |
|---|---|---|---|
| Similarity | 0–5, -1 | published prompt output; 5 = equivalent | `prompt_templates/template_*_admin.txt` |
| Severity | 0–5 | our IR (`difference_ir.schema.json`); 0 = no difference | `contracts.py`, `projection.py` |
| Difference | 0–1, gold -1 | evaluated scale | gold labels, predictions |

`difference = 1 - similarity/5 = severity/5`. This matches the official `map_label_from_positive_to_negative`, which is tested against the pinned function. Uncovered tokens project to severity 0, i.e. difference 0.0. Spearman is rank-based, so the linear choice affects artefact readability, not the score.

## B0 interpretation

B0 should preserve the spirit of the published direct baseline (the UZH brief asks participants to reproduce a paper baseline with their Apertus model):

```text
document pair → Apertus → token-level similarity → official mapping → exact-length predictions → evaluation
```

S1 manifest documents have 88–267 tokens per side. The published prompt makes the model regenerate every token with a label, so output length grows with document length. The model card claims a 262,144-token context. The endpoint's actual context and output limits are *unverified* until a live request succeeds. Documents that do not fit must be recorded as explicit failures; any chunked variant needs a different strategy name.

## B2 interpretation

Unchanged: aligned spans → Apertus sparse differences → deterministic projection → exact token vector. Uncovered = 0. Overlaps take the max severity. Additions and omissions may be one-sided. Severity converts with `severity/5`.

## Test-set rule

The provided test set must not enter development in any form. The brief adds: no training, no prompt examples and no tuning against it, or the result is disqualified. The adapter registers no test file. Every entry point rejects any split other than `train`/`dev` before I/O, and `train` raises `SplitUnavailableError`.
