"""Canonical benchmark token bookkeeping.

The official SwissGov-RSD evaluator derives tokens with ``str.split()`` on the
stored ``text_a`` / ``text_b`` fields (``evaluation/utils.py::load_gold_data``).
This module reproduces exactly that token sequence and additionally records
each token's character offsets in the original string, so later stages can map
spans back to the source text without re-tokenising.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass


class LengthMismatchError(ValueError):
    """A label/prediction vector does not match its document's token count."""


@dataclass(frozen=True)
class TokenizedText:
    text: str
    tokens: tuple[str, ...]
    offsets: tuple[tuple[int, int], ...]

    def __len__(self) -> int:
        return len(self.tokens)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def tokenize(text: str) -> TokenizedText:
    """Split like ``str.split()`` and keep ``[start, end)`` character offsets."""
    if not isinstance(text, str):
        raise TypeError("text must be str")
    tokens: list[str] = []
    offsets: list[tuple[int, int]] = []
    index, length = 0, len(text)
    while index < length:
        while index < length and text[index].isspace():
            index += 1
        if index >= length:
            break
        start = index
        while index < length and not text[index].isspace():
            index += 1
        tokens.append(text[start:index])
        offsets.append((start, index))
    result = TokenizedText(text=text, tokens=tuple(tokens), offsets=tuple(offsets))
    # Defensive equivalence check with the official tokenisation.
    if result.tokens != tuple(text.split()):
        raise AssertionError("token scan diverged from str.split()")
    return result


def check_vector(document: TokenizedText, values: Sequence[float], *, name: str, allow_mask: bool = False) -> tuple[float, ...]:
    """Validate a per-token vector: exact length, finite numbers, no repair.

    Prediction vectors must lie in [0, 1]. Gold vectors additionally allow the
    official punctuation mask ``-1`` (``allow_mask=True``).
    """
    if len(values) != len(document):
        raise LengthMismatchError(f"{name}: {len(values)} values for {len(document)} tokens")
    checked: list[float] = []
    for position, value in enumerate(values):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name}[{position}] is not a number: {value!r}")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{name}[{position}] is not finite")
        if allow_mask and number == -1.0:
            checked.append(number)
            continue
        if not 0.0 <= number <= 1.0:
            raise ValueError(f"{name}[{position}]={number} outside [0, 1]")
        checked.append(number)
    return tuple(checked)
