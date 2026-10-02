# SwissGov-RSD Benchmark Notes

This file records the current technical understanding of the benchmark from the official repository and ACL paper. Pin exact revisions when M1 begins.

## Task

Given two related documents in different languages, predict a semantic-difference score for each benchmark token.

Evaluated pairs:

- EN–DE
- EN–FR
- EN–IT

Primary metric: token-level Spearman correlation per language pair, macro-averaged for the challenge.

## Gold representation

The official evaluation loader constructs each sample from:

```text
text_a
text_b
labels_a
labels_b
```

The benchmark token sequence used by the evaluation code is derived from whitespace splitting of the stored text:

```python
text_a.split()
text_b.split()
```

This makes deterministic token bookkeeping possible without asking a model to reproduce tokenization.

## Human annotation shape

The paper describes semantic differences as annotated spans with ordinal severity. Differences may be asymmetric, which naturally represents additions and omissions.

This is important for B2: a span-level semantic IR is compatible with the conceptual annotation process even though final evaluation is token-level.

## Official evaluation

The released evaluator:

1. loads predictions and gold labels;
2. aligns prediction vectors to gold vector lengths;
3. ignores gold labels equal to `-1`;
4. concatenates token labels across samples for a language pair;
5. computes global Spearman (and also Kendall in the repository script).

Our adapter should avoid relying on the evaluator's padding/truncation repair behavior. Prediction length should be correct by construction.

## Published LLM prompting

The repository prompt templates ask the model to return each input token paired with a semantic **similarity** score:

- 5 = complete equivalence
- 3–4 = close semantic similarity
- 1–2 = partial/slight similarity
- 0 = no semantic relation
- -1 = punctuation

The repository then maps positive similarity labels to difference scores:

```text
5 → 0.0 difference
4 → 0.2
3 → 0.4
2 → 0.6
1 → 0.8
0 → 1.0
-1 → -1
```

This published baseline requires the LLM to regenerate token-label pairs for the whole input. The repository includes parsing/repair logic for missing, malformed, short or long outputs.

## B0 interpretation

B0 should intentionally preserve the spirit of the published direct baseline:

```text
document pair
→ Apertus
→ token-level scores
→ strict validation
→ official-format predictions
→ evaluation
```

We should record schema failures and length repair rather than hiding them.

## B2 interpretation

B2 asks Apertus for sparse semantic decisions over bounded evidence:

```text
aligned spans
→ Apertus
→ sparse semantic differences
→ deterministic projection
→ exact token vector
```

Initial projection rule:

- uncovered token = 0;
- tokens covered by one difference = its severity;
- overlapping differences = maximum severity;
- additions/omissions may have a span on only one side.

The exact severity scale used internally must be reconciled carefully with the official prediction format in M1.

## Key experimental decomposition

B2a tests only localisation:

```text
difference span = 1
other tokens = 0
```

B2 then adds ordinal severity.

This separates two hypotheses:

1. sparse semantic localisation is better than direct token scoring;
2. Apertus can also rank the magnitude of those differences usefully.

## Test-set rule

The provided test set must not enter development in any form. Normal project code rejects `test` in development paths. Final evaluation should use a separate, explicit invocation added only once the challenge procedure is confirmed.

## Primary sources

- Repository: https://github.com/ZurichNLP/SwissGov-RSD
- Paper: https://aclanthology.org/2026.acl-long.1437/
- Dataset: https://huggingface.co/datasets/ZurichNLP/SwissGov-RSD
- Evaluator: https://github.com/ZurichNLP/SwissGov-RSD/blob/master/scripts/evaluate_predictions_admin.py
- Prediction parser: https://github.com/ZurichNLP/SwissGov-RSD/blob/master/evaluation/predictions.py
- Evaluation utilities: https://github.com/ZurichNLP/SwissGov-RSD/blob/master/evaluation/utils.py
- Prompt templates: https://github.com/ZurichNLP/SwissGov-RSD/tree/master/prompt_templates
