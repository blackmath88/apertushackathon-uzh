"""Versioned, dependency-free SDM contracts.

All token intervals are half-open offsets into the official ``str.split()``
token arrays.  Model output never supplies or changes an offset.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

SCHEMA_VERSION = "sdm/v1"


class Relation(str, Enum):
    EQUIVALENT = "EQUIVALENT"
    DIFFERENT = "DIFFERENT"
    UNCERTAIN = "UNCERTAIN"


class DifferenceKind(str, Enum):
    NUMERIC_CHANGE = "NUMERIC_CHANGE"
    NEGATION_CHANGE = "NEGATION_CHANGE"
    ENTITY_CHANGE = "ENTITY_CHANGE"
    TEMPORAL_CHANGE = "TEMPORAL_CHANGE"
    MODALITY_CHANGE = "MODALITY_CHANGE"
    QUALIFICATION_CHANGE = "QUALIFICATION_CHANGE"
    OMISSION = "OMISSION"
    ADDITION = "ADDITION"
    OTHER = "OTHER"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Passage:
    start_token: int
    end_token: int
    text: str

    def __post_init__(self) -> None:
        if self.start_token < 0 or self.end_token <= self.start_token:
            raise ValueError("passage offsets must be a non-empty half-open interval")


@dataclass(frozen=True)
class ComparisonTask:
    task_id: str
    document_id: str
    language_pair: str
    left: Passage | None
    right: Passage | None
    alignment_basis: str
    alignment_status: str
    route: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.left is None and self.right is None:
            raise ValueError("a comparison task needs evidence on at least one side")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ClassifierResponse:
    relation: Relation
    kind: DifferenceKind
    rationale: str | None = None

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"relation": self.relation.value, "kind": self.kind.value}
        if self.rationale is not None:
            result["rationale"] = self.rationale
        return result


@dataclass(frozen=True)
class DecisionRecord:
    task_id: str
    document_id: str
    route: str
    status: str
    relation: Relation | None
    kind: DifferenceKind
    failure: str | None
    raw_response_sha256: str | None
    prompt_version: str
    schema_version: str
    model: str | None
    finish_reason: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_s: float | None
    left: Passage | None
    right: Passage | None

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["relation"] = self.relation.value if self.relation else None
        value["kind"] = self.kind.value
        return value


@dataclass(frozen=True)
class EvidenceRecord:
    task_id: str
    observation: str
    left: Passage | None
    right: Passage | None
    provenance: str = "deterministic_source_offsets"
    schema_version: str = SCHEMA_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
