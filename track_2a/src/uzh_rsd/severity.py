"""Scale reconciliation between the published prompt, the IR and the gold labels.

Three scales are in play:

* **Similarity** (published LLM prompts, 0-5): 5 = equivalent, 0 = unrelated,
  -1 = punctuation. The official ``map_label_from_positive_to_negative`` maps
  it to a difference score ``1 - s/5`` (and -1 to -1).
* **Severity** (our ``difference_ir`` schema, 0-5): 0 = no difference,
  5 = maximal difference. It is the mirror image of similarity:
  ``severity = 5 - similarity``.
* **Difference** (gold labels and official predictions, 0-1): the evaluated
  scale. Gold uses -1 for punctuation, which the evaluator masks.

Hence ``difference = severity / 5 = 1 - similarity / 5``. Spearman is rank
based, so any strictly monotone transform would score identically; this
module fixes the linear one so artefacts stay on the official 0-1 scale.
"""

from __future__ import annotations

import math

MAX_LEVEL = 5.0
PUNCTUATION = -1.0


def _check_level(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if not 0.0 <= number <= MAX_LEVEL:
        raise ValueError(f"{name}={number} outside [0, {MAX_LEVEL:g}]")
    return number


def similarity_to_difference(similarity: float) -> float:
    """Official mapping; ``-1`` (punctuation) passes through unchanged."""
    if not isinstance(similarity, bool) and isinstance(similarity, (int, float)) and float(similarity) == PUNCTUATION:
        return PUNCTUATION
    return 1.0 - _check_level(similarity, "similarity") / MAX_LEVEL


def severity_to_difference(severity: float) -> float:
    return _check_level(severity, "severity") / MAX_LEVEL


def similarity_to_severity(similarity: float) -> float:
    return MAX_LEVEL - _check_level(similarity, "similarity")


def severities_to_differences(severities: list[float]) -> list[float]:
    """Convert a projected IR severity vector (see projection.py) to 0-1 scores."""
    return [severity_to_difference(value) for value in severities]
