"""Frozen deterministic segmentation, alignment, routing and projection."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from ..backends import Generation
from ..data_adapter import InferenceInput
from ..tokens import check_vector
from .contracts import ClassifierResponse, ComparisonTask, DifferenceKind, Passage, Relation

POLICY = {
    "version": "sdm-policy/v1",
    "segmentation": "punctuation-units regrouped deterministically to <=8 passages/side",
    "alignment": "unique shared numeric anchors, otherwise monotone proportional candidates",
    "max_passages_per_side": 8,
    "max_tasks_per_document": 12,
    "max_calls_total": 300,
    "max_completion_tokens": 96,
    "timeout_s": 90,
    "global_wall_s": 2100,
    "routes": "exact identity and shape-identical numeric changes are structural; remainder model",
    "projection": "DIFFERENT marks both inherited spans 1.0; other resolved relations 0.0; unresolved tokens use explicit evaluation_default=0.0",
    "prompt_version": "sdm-classifier/v1",
    "schema_version": "sdm/v1",
}

_END = re.compile(r"[.!?;:…][\"'»”)]*$")
_NUMBER = re.compile(r"(?<!\w)[+-]?(?:\d[\d'’.,]*)(?:%|‰)?(?!\w)")


def _text(tokens: Sequence[str], start: int, end: int) -> str:
    return " ".join(tokens[start:end])


def segment(tokens: Sequence[str], *, max_passages: int = 8) -> list[Passage]:
    if not tokens:
        return []
    units: list[tuple[int, int]] = []
    start = 0
    for index, token in enumerate(tokens, 1):
        if _END.search(token) or index - start >= 64:
            units.append((start, index))
            start = index
    if start < len(tokens):
        units.append((start, len(tokens)))
    groups = min(max_passages, len(units))
    passages: list[Passage] = []
    for group in range(groups):
        first = group * len(units) // groups
        last = (group + 1) * len(units) // groups
        begin, end = units[first][0], units[last - 1][1]
        passages.append(Passage(begin, end, _text(tokens, begin, end)))
    return passages


def _numbers(text: str) -> tuple[str, ...]:
    return tuple(match.group(0).casefold().replace("’", "'") for match in _NUMBER.finditer(text))


def _shape(text: str) -> str:
    return " ".join(_NUMBER.sub("#", text).casefold().split())


def _normal(text: str) -> str:
    return " ".join(text.casefold().replace("’", "'").split())


def _route(left: Passage | None, right: Passage | None) -> str:
    if left and right and _normal(left.text) == _normal(right.text):
        return "structural_identity"
    if left and right and _shape(left.text) == _shape(right.text) and _numbers(left.text) != _numbers(right.text):
        return "structural_numeric"
    return "model"


def build_tasks(item: InferenceInput) -> tuple[list[ComparisonTask], dict]:
    left, right = segment(item.text_a.tokens), segment(item.text_b.tokens)
    if not left and not right:
        return [], {"status": "empty", "overflow": False, "left_passages": 0, "right_passages": 0}
    count = max(len(left), len(right))
    pairs: list[tuple[Passage | None, Passage | None, str, str]] = []
    # Unique exact numeric anchors allow cross-language reorder without semantic claims.
    rnums: dict[tuple[str, ...], list[int]] = {}
    for idx, passage in enumerate(right):
        if _numbers(passage.text):
            rnums.setdefault(_numbers(passage.text), []).append(idx)
    anchored: dict[int, int] = {}
    used: set[int] = set()
    for idx, passage in enumerate(left):
        key = _numbers(passage.text)
        if key and len(rnums.get(key, ())) == 1 and rnums[key][0] not in used:
            anchored[idx] = rnums[key][0]
            used.add(rnums[key][0])
    for slot in range(count):
        li = min(len(left) - 1, slot * len(left) // count) if left else None
        ri = min(len(right) - 1, slot * len(right) // count) if right else None
        basis, status = "proportional_order", "candidate"
        if li is not None and li in anchored:
            ri, basis, status = anchored[li], "unique_numeric_anchor", "anchored"
        lp = left[li] if li is not None else None
        rp = right[ri] if ri is not None else None
        pairs.append((lp, rp, basis, status))
    if count > POLICY["max_tasks_per_document"]:
        return [], {"status": "overflow", "overflow": True, "required_tasks": count,
                    "left_passages": len(left), "right_passages": len(right)}
    tasks = []
    for index, (lp, rp, basis, status) in enumerate(pairs):
        digest = hashlib.sha256(json.dumps([item.id, index, lp.start_token if lp else None,
                                            rp.start_token if rp else None]).encode()).hexdigest()[:12]
        tasks.append(ComparisonTask(f"{item.id}:{index:02d}:{digest}", item.id, item.pair,
                                    lp, rp, basis, status, _route(lp, rp)))
    return tasks, {"status": "ok", "overflow": False, "left_passages": len(left),
                   "right_passages": len(right), "tasks": len(tasks),
                   "model_routes": sum(task.route == "model" for task in tasks),
                   "structural_routes": sum(task.route != "model" for task in tasks)}


def structural_response(task: ComparisonTask) -> ClassifierResponse:
    if task.route == "structural_identity":
        return ClassifierResponse(Relation.EQUIVALENT, DifferenceKind.NONE, "deterministic identity")
    if task.route == "structural_numeric":
        return ClassifierResponse(Relation.DIFFERENT, DifferenceKind.NUMERIC_CHANGE, "deterministic numeric observation")
    raise ValueError("not a structural task")


def classifier_prompt(task: ComparisonTask) -> str:
    left = task.left.text if task.left else "[NO PASSAGE]"
    right = task.right.text if task.right else "[NO PASSAGE]"
    return (
        "Classify one aligned bilingual passage pair. Return exactly one JSON object and nothing else.\n"
        'Schema: {"relation":"EQUIVALENT|DIFFERENT|UNCERTAIN","kind":"NUMERIC_CHANGE|NEGATION_CHANGE|ENTITY_CHANGE|TEMPORAL_CHANGE|MODALITY_CHANGE|QUALIFICATION_CHANGE|OMISSION|ADDITION|OTHER|NONE|UNKNOWN","rationale":"optional, max 160 characters"}\n'
        "Use EQUIVALENT with NONE only. Use UNCERTAIN with UNKNOWN only. Do not quote passages or add fields.\n"
        f"LEFT:\n{left}\nRIGHT:\n{right}\n"
    )


def validate_response(generation: Generation) -> tuple[ClassifierResponse | None, str | None]:
    if generation.error or generation.text is None:
        return None, generation.error or "missing_response"
    if generation.finish_reason == "length":
        return None, "truncated"
    try:
        value = json.loads(generation.text)
    except (ValueError, TypeError):
        return None, "invalid_json"
    if not isinstance(value, dict) or not set(value) <= {"relation", "kind", "rationale"} or not {"relation", "kind"} <= set(value):
        return None, "schema_mismatch"
    rationale = value.get("rationale")
    if rationale is not None and (not isinstance(rationale, str) or len(rationale) > 160):
        return None, "invalid_rationale"
    try:
        response = ClassifierResponse(Relation(value["relation"]), DifferenceKind(value["kind"]), rationale)
    except (ValueError, TypeError):
        return None, "unsupported_label"
    allowed = ((response.relation is Relation.EQUIVALENT and response.kind is DifferenceKind.NONE) or
               (response.relation is Relation.UNCERTAIN and response.kind is DifferenceKind.UNKNOWN) or
               (response.relation is Relation.DIFFERENT and response.kind not in (DifferenceKind.NONE, DifferenceKind.UNKNOWN)))
    if not allowed:
        return None, "ambiguous_relation_kind"
    return response, None


def project_decisions(item: InferenceInput, tasks: Sequence[ComparisonTask], decisions: Iterable[ClassifierResponse | None]) -> dict:
    a = [0.0] * len(item.text_a)
    b = [0.0] * len(item.text_b)
    known_a = [False] * len(a)
    known_b = [False] * len(b)
    for task, decision in zip(tasks, decisions, strict=True):
        if decision is None or decision.relation is Relation.UNCERTAIN:
            continue
        value = 1.0 if decision.relation is Relation.DIFFERENT else 0.0
        for passage, vector, known in ((task.left, a, known_a), (task.right, b, known_b)):
            if passage:
                vector[passage.start_token:passage.end_token] = [value] * (passage.end_token - passage.start_token)
                known[passage.start_token:passage.end_token] = [True] * (passage.end_token - passage.start_token)
    check_vector(item.text_a, a, name=f"{item.id}.prediction_a")
    check_vector(item.text_b, b, name=f"{item.id}.prediction_b")
    return {"prediction_a": a, "prediction_b": b, "known_a": known_a, "known_b": known_b,
            "evaluation_default": 0.0, "semantic_complete": all(known_a) and all(known_b)}
