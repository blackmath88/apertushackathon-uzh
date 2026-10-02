# Technical Report — Working Draft

## Title

**Compiling Cross-Lingual Semantic Differences: A Minimum-AI Approach to SwissGov-RSD with Apertus**

## Research question

Does structured semantic compilation over aligned evidence improve token-level semantic-difference prediction compared with direct token scoring?

## Hypothesis

Apertus should be used for the smallest unresolved semantic decision. Traditional software should own ingestion, alignment candidates, split discipline, structured-output validation, token projection and official evaluation.

## Experiments

| ID | Strategy | Purpose | Status |
|---|---|---|---|
| B0 | Direct Apertus token scoring | Reproducible control | planned |
| B2a | Sparse binary difference spans | Test localisation hypothesis | planned |
| B2 | Sparse spans + severity | Main semantic-compiler hypothesis | planned |
| B3 | Heuristic gate + Apertus | Efficiency/minimum-AI extension | deferred |

## Metrics

Primary: token-level Spearman correlation for EN–DE, EN–FR and EN–IT, macro-averaged.

Also record model/revision, prompt/schema versions, split, input/output tokens, model calls, latency, invalid outputs, UNKNOWN rate and repair/fallback events.

## Results

Not yet measured.

## Interpretation rule

The architecture is not the conclusion. If B2 does not improve the benchmark or produce a meaningful efficiency/reproducibility benefit, revise or reject the hypothesis.
