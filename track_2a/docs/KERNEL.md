# Semantic Compiler Kernel for SwissGov-RSD

Conceptually derived from https://github.com/blackmath88/accessibility-red-team/blob/main/docs/SEMANTIC_COMPILER.md

## Invariant

**Traditional software owns the workflow. Apertus is a bounded semantic compiler.**

```text
DATA / LOOKUP
  ↓ unresolved
DETERMINISTIC STRUCTURE
  ↓ unresolved
HEURISTIC / STATISTICAL ALIGNMENT
  ↓ unresolved
TYPED APERTUS SEMANTIC DECISION
  ↓
DETERMINISTIC TOKEN PROJECTION
  ↓
OFFICIAL EVALUATION
```

## Required properties of an Apertus call

1. Bounded input evidence.
2. Closed/typed output.
3. Legal options defined by code.
4. Confidence and/or UNKNOWN.
5. Deterministic validation.
6. Deterministic consumer.
7. Recorded model/prompt/schema provenance.
8. A cheaper baseline to compare against.

## Data lineage

```text
SOURCE OBSERVATION
  immutable benchmark input
        ↓
DETERMINISTIC DERIVATION
  token mapping / segmentation / alignment candidates
        ↓
SEMANTIC DECISION
  Apertus + revision + prompt + schema + evidence refs
        ↓
PROJECTION
  reproducible token-score vector
        ↓
METRIC
  official evaluator
```

The initial IR uses only CHANGE, ADDITION, OMISSION and UNKNOWN with token ranges, severity and confidence. A richer taxonomy is an experiment, not infrastructure.
