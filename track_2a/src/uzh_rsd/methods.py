"""Deterministic parsing of raw model responses into token-level predictions.

Parsing runs offline on saved raw responses, so it can be re-run (and audited)
without new model calls. Every outcome is explicit:

* ``ok``          JSON parsed; vectors produced (with per-token diagnostics)
* ``unparseable`` no usable JSON object in the response; **no vectors**
* ``call_failed`` the model call itself failed; **no vectors**

A document without vectors is never silently turned into an all-zero
prediction. The evaluation reports it as missing coverage, and the separate,
explicitly labelled *paper protocol* view scores it the way the upstream
parser would (every token falls back to similarity 5, i.e. difference 0).
"""

from __future__ import annotations

import ast
import json
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from .contracts import DifferenceKind, SemanticDifference, TokenSpan
from .data_adapter import InferenceInput
from .projection import project_differences
from .severity import severities_to_differences, similarity_to_difference

B0_FALLBACK_SIMILARITY = 5.0  # upstream LLMPrediction.get_difference_sample
B2_MAX_EXCERPT_TOKENS = 40


@dataclass
class MethodOutput:
    method: str
    id: str
    status: str
    diff_a: list[float] | None = None
    diff_b: list[float] | None = None
    diagnostics: dict = field(default_factory=dict)


# --- shared JSON extraction ---------------------------------------------------


def extract_json_str(content: str) -> str:
    """Same cleaning as upstream ``LLMPrediction.get_json_str``."""
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    if not content.startswith("{") and "{" in content:
        content = content[content.index("{"):]
    if "```\n" in content:
        content = content.split("```\n")[0]
    return content


def load_json_object(content: str) -> tuple[dict | None, str]:
    """Parse a JSON object. Upstream used ``eval``; we never evaluate model
    output and use ``ast.literal_eval`` as the literal-only equivalent."""
    text = extract_json_str(content)
    try:
        data = json.loads(text)
        mode = "json"
    except (ValueError, RecursionError):
        try:
            data = ast.literal_eval(text)
            mode = "literal_eval"
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
            return None, "unparseable"
    if not isinstance(data, dict):
        return None, f"not an object ({type(data).__name__})"
    return data, mode


# --- B0: direct token scoring (paper baseline) --------------------------------


def _b0_side(tokens: Sequence[str], predictions: object, parse_token_labels: Callable) -> tuple[list[float], dict]:
    sentinel = float("nan")
    if predictions is None:
        labels = [sentinel] * len(tokens)
    else:
        labels = list(parse_token_labels(list(tokens), predictions, fallback_label=sentinel))
    fallback = punct = out_of_range = 0
    differences: list[float] = []
    for label in labels:
        if isinstance(label, float) and math.isnan(label):
            fallback += 1
            differences.append(similarity_to_difference(B0_FALLBACK_SIMILARITY))
        elif label == -1:
            # Upstream keeps -1 (ranked below 0). Valid predictions lie in [0, 1];
            # the model's own punctuation label is scored as "no difference".
            punct += 1
            differences.append(0.0)
        elif not 0.0 <= label <= 5.0:
            out_of_range += 1
            differences.append(similarity_to_difference(B0_FALLBACK_SIMILARITY))
        else:
            differences.append(similarity_to_difference(label))
    returned = len(predictions) if isinstance(predictions, list) else 0
    return differences, {
        "tokens": len(tokens),
        "returned_items": returned,
        "labelled": len(tokens) - fallback - out_of_range,
        "fallback": fallback,
        "model_punctuation_label": punct,
        "out_of_range": out_of_range,
    }


def parse_b0(item: InferenceInput, content: str | None, parse_token_labels: Callable) -> MethodOutput:
    if content is None:
        return MethodOutput("b0", item.id, "call_failed")
    data, mode = load_json_object(content)
    if data is None or ("sentence1" not in data and "sentence2" not in data):
        return MethodOutput("b0", item.id, "unparseable", diagnostics={"parse": mode if data is None else "missing sentence1/sentence2"})
    diff_a, side_a = _b0_side(item.text_a.tokens, data.get("sentence1"), parse_token_labels)
    diff_b, side_b = _b0_side(item.text_b.tokens, data.get("sentence2"), parse_token_labels)
    strict = all(
        isinstance(data.get(key), list) and side["fallback"] == 0 and side["out_of_range"] == 0 and side["returned_items"] == side["tokens"]
        for key, side in (("sentence1", side_a), ("sentence2", side_b))
    )
    return MethodOutput("b0", item.id, "ok", diff_a, diff_b, {"parse": mode, "a": side_a, "b": side_b, "strict_valid": strict})


# --- B2: difference spans + deterministic projection -------------------------


def _normalise(token: str) -> str:
    return token.casefold().strip("\"'«»“”„‘’`")


def locate(tokens: Sequence[str], excerpt: str, *, max_excerpt_tokens: int = B2_MAX_EXCERPT_TOKENS) -> tuple[list[TokenSpan], str]:
    """All occurrences of the excerpt's whitespace tokens in ``tokens``.

    Exact match first, then a case/quote-insensitive match. Returns the spans
    and the match mode (``exact``, ``normalised``, ``not_found``, ``empty``,
    ``too_long``)."""
    parts = excerpt.split()
    if not parts:
        return [], "empty"
    if len(parts) > max_excerpt_tokens:
        return [], "too_long"
    for mode, key in (("exact", lambda t: t), ("normalised", _normalise)):
        target = [key(part) for part in parts]
        keyed = [key(token) for token in tokens]
        width = len(target)
        spans = [TokenSpan(start, start + width) for start in range(len(keyed) - width + 1) if keyed[start:start + width] == target]
        if spans:
            return spans, mode
    return [], "not_found"


def _severity(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or not 1.0 <= number <= 5.0:
        return None
    return number


def parse_b2(item: InferenceInput, content: str | None, *, max_excerpt_tokens: int = B2_MAX_EXCERPT_TOKENS) -> MethodOutput:
    if content is None:
        return MethodOutput("b2", item.id, "call_failed")
    data, mode = load_json_object(content)
    if data is None or not isinstance(data.get("differences"), list):
        return MethodOutput("b2", item.id, "unparseable", diagnostics={"parse": mode if data is None else "missing differences list"})
    counts = {
        "items": len(data["differences"]),
        "projected": 0,
        "invalid_item": 0,
        "invalid_severity": 0,
        "unknown_kind": 0,
        "spans_exact": 0,
        "spans_normalised": 0,
        "spans_not_found": 0,
        "spans_too_long": 0,
        "spans_ambiguous": 0,
    }
    differences: list[SemanticDifference] = []
    for entry in data["differences"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("a", ""), str) or not isinstance(entry.get("b", ""), str):
            counts["invalid_item"] += 1
            continue
        severity = _severity(entry.get("severity"))
        if severity is None:
            counts["invalid_severity"] += 1
            continue
        try:
            kind = DifferenceKind(entry.get("kind"))
        except ValueError:
            kind = DifferenceKind.UNKNOWN
            counts["unknown_kind"] += 1
        located = []
        for side_tokens, excerpt in ((item.text_a.tokens, entry.get("a", "")), (item.text_b.tokens, entry.get("b", ""))):
            spans, match = locate(side_tokens, excerpt, max_excerpt_tokens=max_excerpt_tokens)
            if match in ("exact", "normalised"):
                counts[f"spans_{match}"] += 1
                if len(spans) > 1:
                    counts["spans_ambiguous"] += 1
            elif match != "empty":
                counts[f"spans_{match}"] += 1
            located.append(spans)
        spans_a, spans_b = located
        if not spans_a and not spans_b:
            continue
        # Every occurrence of an ambiguous excerpt is marked (deterministic, counted).
        for span in spans_a:
            differences.append(SemanticDifference(source=span, target=None, kind=kind, severity=severity, confidence=1.0))
        for span in spans_b:
            differences.append(SemanticDifference(source=None, target=span, kind=kind, severity=severity, confidence=1.0))
        counts["projected"] += 1
    severities_a, severities_b = project_differences(len(item.text_a), len(item.text_b), differences)
    return MethodOutput(
        "b2", item.id, "ok",
        severities_to_differences(severities_a), severities_to_differences(severities_b),
        {"parse": mode, **counts, "marked_tokens_a": sum(1 for s in severities_a if s), "marked_tokens_b": sum(1 for s in severities_b if s)},
    )
