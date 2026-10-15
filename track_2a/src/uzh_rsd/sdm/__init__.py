"""B3 Semantic Decision Middleware (``sdm/v1``)."""

from .contracts import (
    ClassifierResponse,
    ComparisonTask,
    DecisionRecord,
    DifferenceKind,
    EvidenceRecord,
    Passage,
    Relation,
)
from .pipeline import POLICY, build_tasks, project_decisions, validate_response

__all__ = [
    "ClassifierResponse", "ComparisonTask", "DecisionRecord", "DifferenceKind",
    "EvidenceRecord", "Passage", "Relation", "POLICY", "build_tasks",
    "project_decisions", "validate_response",
]
