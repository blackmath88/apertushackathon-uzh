from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DifferenceKind(StrEnum):
    CHANGE = "CHANGE"
    ADDITION = "ADDITION"
    OMISSION = "OMISSION"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TokenSpan:
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise ValueError("TokenSpan must satisfy 0 <= start < end")


@dataclass(frozen=True)
class SemanticDifference:
    source: TokenSpan | None
    target: TokenSpan | None
    kind: DifferenceKind
    severity: float
    confidence: float

    def __post_init__(self) -> None:
        if self.source is None and self.target is None:
            raise ValueError("A difference must reference at least one side")
        if not 0.0 <= self.severity <= 5.0:
            raise ValueError("severity must be between 0 and 5")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
