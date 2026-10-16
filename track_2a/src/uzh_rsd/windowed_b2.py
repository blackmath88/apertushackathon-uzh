"""Bounded long-input B2 with deterministic correspondence and exact maps.

The method deliberately preserves the original :mod:`uzh_rsd.methods` B2
parser/projection.  It only changes how a document is presented to Apertus:
each side is split into bounded, overlapping windows over the *official*
whitespace-token sequence; windows are paired by gold-free structural anchors;
and local scores are projected through explicit original-token indices.

There is one model request per unique bidirectional best-match window pair.
An intent is persisted before every request and a return is persisted after it.
There are no retries.  A document is complete only when every planned request
has a valid, non-truncated response and every official token was included in at
least one successful request.  Thus an explicit ``{"differences": []}`` is not
confused with an unprocessed region.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .backends import Generation
from .data_adapter import InferenceInput
from .methods import parse_b2
from .prompts import prompt_sha256, render_b2
from .tokens import tokenize

METHOD_VERSION = "b2-windowed-v2"
PROMPT_VERSION = "b2-spans-v1"
WINDOW_TOKENS = 320
WINDOW_OVERLAP = 32
MIN_BOUNDARY_DISTANCE = 192
MAX_NEW_TOKENS = 1024
MAX_PROMPT_CHARS = 50_000
LEDGER_SCHEMA = "uzh-rsd.windowed-b2-ledger/v1"

_END = re.compile(r"[.!?;:…][\"'\u00bb”)]*$")
_TRIM = "\"'`.,;:!?()[]{}<>\u00ab\u00bb“”„‘’"
_NUMBER = re.compile(r"\d")


@dataclass(frozen=True)
class Window:
    side: str
    index: int
    start: int
    end: int
    tokens: tuple[str, ...]

    @property
    def center(self) -> float:
        return (self.start + self.end) / 2


@dataclass(frozen=True)
class WindowPair:
    index: int
    left: Window
    right: Window
    basis: str
    shared_anchors: tuple[str, ...]

    @property
    def task_id(self) -> str:
        body = f"{self.left.start}:{self.left.end}:{self.right.start}:{self.right.end}"
        return f"w{self.index:03d}-{hashlib.sha256(body.encode()).hexdigest()[:10]}"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def split_windows(tokens: Sequence[str], *, side: str, limit: int = WINDOW_TOKENS,
                  overlap: int = WINDOW_OVERLAP) -> list[Window]:
    """Return bounded windows whose integer ranges cover every input token."""
    if limit <= 0 or overlap < 0 or overlap >= limit:
        raise ValueError("window limit must be positive and overlap in [0, limit)")
    if not tokens:
        return []
    result: list[Window] = []
    start = 0
    while start < len(tokens):
        hard_end = min(len(tokens), start + limit)
        end = hard_end
        if hard_end < len(tokens):
            minimum = min(hard_end, start + MIN_BOUNDARY_DISTANCE)
            boundaries = [position for position in range(minimum, hard_end + 1) if _END.search(tokens[position - 1])]
            if boundaries:
                end = boundaries[-1]
        result.append(Window(side, len(result), start, end, tuple(tokens[start:end])))
        if end == len(tokens):
            break
        next_start = end - overlap
        if next_start <= start:
            raise AssertionError("window splitter made no progress")
        start = next_start
    covered = {position for window in result for position in range(window.start, window.end)}
    if covered != set(range(len(tokens))):
        raise AssertionError("window splitter did not cover every official token")
    return result


def _normal(token: str) -> str:
    return token.casefold().strip(_TRIM)


def _anchors(window: Window) -> frozenset[str]:
    anchors = set()
    for raw in window.tokens:
        token = _normal(raw)
        if not token:
            continue
        if _NUMBER.search(token) or "://" in token or "@" in token:
            anchors.add(token)
        elif len(token) >= 6 and (raw[:1].isupper() or raw.isupper()):
            anchors.add(token)
        elif len(token) >= 9:
            anchors.add(token)
    return frozenset(anchors)


def _pair_score(left: Window, right: Window, left_total: int, right_total: int) -> tuple[float, int, float, int]:
    shared = _anchors(left) & _anchors(right)
    union = _anchors(left) | _anchors(right)
    anchor_score = len(shared) / len(union) if union else 0.0
    left_words = {_normal(token) for token in left.tokens if len(_normal(token)) >= 5}
    right_words = {_normal(token) for token in right.tokens if len(_normal(token)) >= 5}
    lexical = len(left_words & right_words) / len(left_words | right_words) if left_words | right_words else 0.0
    position = abs(left.center / max(left_total, 1) - right.center / max(right_total, 1))
    # Shared anchors dominate the positional fallback.  The remaining tuple is
    # an explicit deterministic tie-break (more anchors, closer position, lower index).
    score = 8.0 * anchor_score + 2.0 * lexical + (1.0 - position)
    return score, len(shared), -position, -right.index


def align_windows(left: Sequence[Window], right: Sequence[Window], *, left_total: int,
                  right_total: int) -> list[WindowPair]:
    """Pair every window in both directions, permitting crossings/reordering."""
    if not left or not right:
        raise ValueError("both document sides must contain tokens")
    pairs: dict[tuple[int, int], tuple[Window, Window]] = {}
    for source, targets, reverse in ((left, right, False), (right, left, True)):
        for window in source:
            if reverse:
                target = max(targets, key=lambda candidate: _pair_score(candidate, window, left_total, right_total))
                pair = (target, window)
            else:
                target = max(targets, key=lambda candidate: _pair_score(window, candidate, left_total, right_total))
                pair = (window, target)
            pairs[(pair[0].index, pair[1].index)] = pair
    ordered = sorted(pairs.values(), key=lambda pair: (min(pair[0].center / left_total, pair[1].center / right_total),
                                                       pair[0].index, pair[1].index))
    result = []
    for index, (a, b) in enumerate(ordered):
        shared = tuple(sorted(_anchors(a) & _anchors(b)))
        result.append(WindowPair(index, a, b, "shared_anchors" if shared else "proportional_fallback", shared))
    return result


def plan_document(item: InferenceInput) -> list[WindowPair]:
    left = split_windows(item.text_a.tokens, side="a")
    right = split_windows(item.text_b.tokens, side="b")
    return align_windows(left, right, left_total=len(item.text_a), right_total=len(item.text_b))


def _slice_item(item: InferenceInput, pair: WindowPair) -> InferenceInput:
    text_a = tokenize(" ".join(pair.left.tokens))
    text_b = tokenize(" ".join(pair.right.tokens))
    if text_a.tokens != pair.left.tokens or text_b.tokens != pair.right.tokens:
        raise AssertionError("window token reconstruction changed official tokens")
    return InferenceInput(f"{item.id}:{pair.task_id}", item.language, text_a, text_b, item.page_en, item.page_other)


def validate_window_response(local: InferenceInput, generation: Generation):
    if generation.finish_reason == "length":
        return None, "truncated"
    output = parse_b2(local, generation.text)
    if output.diff_a is None:
        return None, output.status
    diagnostics = output.diagnostics
    rejected = [name for name in ("invalid_item", "invalid_severity", "unknown_kind", "spans_not_found", "spans_too_long")
                if diagnostics.get(name, 0)]
    if rejected:
        return output, "invalid_evidence:" + ",".join(rejected)
    return output, None


def _append(path: Path, value: Mapping) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
        handle.flush()


def execute_document(backend, item: InferenceInput, ledger_path: Path, *, run_id: str,
                     total_deadline: float | None = None, clock: Callable[[], float] = time.monotonic,
                     after_call: Callable[[dict], None] | None = None) -> dict:
    """Execute one planned document once; return vectors only when complete."""
    pairs = plan_document(item)
    scores_a = [0.0] * len(item.text_a)
    scores_b = [0.0] * len(item.text_b)
    processed_a = [False] * len(item.text_a)
    processed_b = [False] * len(item.text_b)
    tasks, problems = [], []
    for pair in pairs:
        local = _slice_item(item, pair)
        prompt = render_b2(local)
        if len(prompt) > MAX_PROMPT_CHARS:
            problems.append(f"{pair.task_id}:prompt_char_bound")
            break
        intent = {
            "schema": LEDGER_SCHEMA, "event": "intent", "run_id": run_id, "document_id": item.id,
            "task_id": pair.task_id, "sequence": pair.index, "prompt_version": PROMPT_VERSION,
            "prompt_sha256": prompt_sha256(prompt), "max_new_tokens": MAX_NEW_TOKENS,
            "left": {"start": pair.left.start, "end": pair.left.end},
            "right": {"start": pair.right.start, "end": pair.right.end},
            "alignment": {"basis": pair.basis, "shared_anchors": list(pair.shared_anchors)},
            "started_utc": _now(),
        }
        _append(ledger_path, intent)
        if total_deadline is not None and clock() >= total_deadline:
            problems.append(f"{pair.task_id}:total_deadline")
            break
        generation = backend.generate(prompt, MAX_NEW_TOKENS)
        returned = {
            "schema": LEDGER_SCHEMA, "event": "return", "run_id": run_id, "document_id": item.id,
            "task_id": pair.task_id, "sequence": pair.index, "finished_utc": _now(),
            "generation": generation.as_dict(),
        }
        if generation.text is not None:
            returned["response_sha256"] = hashlib.sha256(generation.text.encode()).hexdigest()
        _append(ledger_path, returned)
        if after_call is not None:
            after_call(returned)
        if generation.text is None:
            problems.append(f"{pair.task_id}:{generation.error or 'call_failed'}")
            tasks.append({"task_id": pair.task_id, "status": "call_failed", "error": generation.error})
            continue
        output, error = validate_window_response(local, generation)
        if error:
            problems.append(f"{pair.task_id}:{error}")
            tasks.append({"task_id": pair.task_id, "status": error, "diagnostics": getattr(output, "diagnostics", {}),
                          "prompt_tokens": generation.prompt_tokens, "completion_tokens": generation.completion_tokens,
                          "latency_s": generation.latency_s, "finish_reason": generation.finish_reason})
            continue
        assert output is not None and output.diff_a is not None and output.diff_b is not None
        for local_index, value in enumerate(output.diff_a):
            original = pair.left.start + local_index
            scores_a[original] = max(scores_a[original], float(value))
            processed_a[original] = True
        for local_index, value in enumerate(output.diff_b):
            original = pair.right.start + local_index
            scores_b[original] = max(scores_b[original], float(value))
            processed_b[original] = True
        tasks.append({"task_id": pair.task_id, "status": "ok", "diagnostics": output.diagnostics,
                      "prompt_tokens": generation.prompt_tokens, "completion_tokens": generation.completion_tokens,
                      "latency_s": generation.latency_s, "finish_reason": generation.finish_reason})
    if not all(processed_a) or not all(processed_b):
        problems.append(f"unprocessed_tokens:a={processed_a.count(False)},b={processed_b.count(False)}")
    for side, values in (("a", scores_a), ("b", scores_b)):
        if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in values):
            problems.append(f"invalid_scores:{side}")
    return {
        "id": item.id, "status": "complete" if not problems else "incomplete", "method": METHOD_VERSION,
        "planned_requests": len(pairs), "completed_requests": sum(task["status"] == "ok" for task in tasks),
        "processed_tokens_a": sum(processed_a), "processed_tokens_b": sum(processed_b),
        "total_tokens_a": len(processed_a), "total_tokens_b": len(processed_b),
        "problems": problems, "tasks": tasks,
        "labels_a": scores_a if not problems else None, "labels_b": scores_b if not problems else None,
    }


def replay_document(item: InferenceInput, ledger_records: Sequence[Mapping]) -> dict:
    """Offline deterministic replay of a complete document ledger."""
    pairs = plan_document(item)
    returns = {row["task_id"]: row for row in ledger_records
               if row.get("event") == "return" and row.get("document_id") == item.id}

    class ReplayBackend:
        def generate(self, prompt: str, max_new_tokens: int) -> Generation:
            pair = pairs[len(self.used)]
            row = returns[pair.task_id]
            self.used.append(pair.task_id)
            return Generation(**row["generation"])

        used: list[str] = []

    # Replay into an in-memory-equivalent scratch ledger supplied by caller is
    # intentionally avoided here; reconstruct directly with the same parser and maps.
    scores_a, scores_b = [0.0] * len(item.text_a), [0.0] * len(item.text_b)
    processed_a, processed_b = [False] * len(item.text_a), [False] * len(item.text_b)
    problems = []
    for pair in pairs:
        row = returns.get(pair.task_id)
        if row is None:
            problems.append(f"{pair.task_id}:missing_return")
            continue
        generation = Generation(**row["generation"])
        output, error = validate_window_response(_slice_item(item, pair), generation)
        if error:
            problems.append(f"{pair.task_id}:{error}")
            continue
        assert output is not None and output.diff_a is not None and output.diff_b is not None
        for offset, value in enumerate(output.diff_a):
            index = pair.left.start + offset
            scores_a[index], processed_a[index] = max(scores_a[index], float(value)), True
        for offset, value in enumerate(output.diff_b):
            index = pair.right.start + offset
            scores_b[index], processed_b[index] = max(scores_b[index], float(value)), True
    if not all(processed_a) or not all(processed_b):
        problems.append(f"unprocessed_tokens:a={processed_a.count(False)},b={processed_b.count(False)}")
    return {"id": item.id, "status": "complete" if not problems else "incomplete", "problems": problems,
            "labels_a": scores_a if not problems else None, "labels_b": scores_b if not problems else None}
