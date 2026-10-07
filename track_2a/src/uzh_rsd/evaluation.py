"""Token-level Spearman evaluation with the official SwissGov-RSD semantics.

Semantics reproduced from ``scripts/evaluate_predictions_admin.py`` at the
pinned commit, except that length repair is replaced by a hard failure:

* per language, concatenate every document's ``labels_a`` and, unless the gold
  ``labels_b`` is entirely ``-1``, its ``labels_b``;
* drop positions whose *gold* label is ``-1`` (punctuation);
* compute one global Spearman correlation over the remaining positions.

The official script reports per-language values only. The UZH challenge brief
defines the primary metric as the macro average over EN-DE, EN-FR and EN-IT;
:func:`macro_average` computes it and refuses to average when any language is
missing or undefined.

The official code itself is not vendored (the SwissGov-RSD repository has no
top-level licence; see docs/SOURCES.md). :func:`fetch_official` downloads the
three needed files at the pinned commit into the ignored ``data/`` directory
and verifies their SHA-256; parity tests execute the official functions from
those bytes.
"""

from __future__ import annotations

import ast
import contextlib
import hashlib
import math
import os
import sys
import types
import urllib.request
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .data_adapter import LANGUAGES, TRACK_ROOT, GoldLabels
from .tokens import LengthMismatchError

OFFICIAL_REPO = "ZurichNLP/SwissGov-RSD"
OFFICIAL_COMMIT = "1807a42100e742ed03d337c54c4b9ea86995f565"
OFFICIAL_FILES = {
    "scripts/evaluate_predictions_admin.py": "3e8101661621c51938e62d8d064e737e3e7d9bb16088dad754ba289c0aa083fa",
    "evaluation/utils.py": "8da64aa6ec33f316eec2c65d0cbc3fe36d247c585a033d2ed04a7bebc175df0b",
    "list_to_drop.txt": "3bd489505875ecc0800685f1b732f84dad7b7c25380f63612cadcfbe2732857a",
}
DEFAULT_OFFICIAL_DIR = TRACK_ROOT / "data" / "official" / "swissgov-rsd" / OFFICIAL_COMMIT


class OfficialEvaluatorUnavailable(RuntimeError):
    pass


# --- our implementation -----------------------------------------------------


@dataclass(frozen=True)
class LanguageResult:
    language: str
    documents: int
    positions: int
    masked: int
    spearman: float | None
    undefined_reason: str | None = None


def assemble(items: Iterable[tuple[GoldLabels, Sequence[float], Sequence[float]]]) -> tuple[list[float], list[float], int]:
    """Concatenate predictions and gold exactly as the official script does.

    Returns (predictions, gold, masked_count) with gold ``-1`` removed. Any
    length mismatch raises; nothing is padded or truncated.
    """
    predictions: list[float] = []
    gold: list[float] = []
    for labels, prediction_a, prediction_b in items:
        if len(prediction_a) != len(labels.labels_a):
            raise LengthMismatchError(f"{labels.id}: side a has {len(prediction_a)} predictions for {len(labels.labels_a)} tokens")
        predictions.extend(prediction_a)
        gold.extend(labels.labels_a)
        if not all(label == -1 for label in labels.labels_b):
            if len(prediction_b) != len(labels.labels_b):
                raise LengthMismatchError(f"{labels.id}: side b has {len(prediction_b)} predictions for {len(labels.labels_b)} tokens")
            predictions.extend(prediction_b)
            gold.extend(labels.labels_b)
    kept = [(p, g) for p, g in zip(predictions, gold) if g != -1]
    return [p for p, _ in kept], [g for _, g in kept], len(gold) - len(kept)


def _average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and values[order[end + 1]] == values[order[start]]:
            end += 1
        average = (start + end) / 2 + 1
        for position in range(start, end + 1):
            ranks[order[position]] = average
        start = end + 1
    return ranks


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    """Spearman rho with average ranks for ties; ``None`` when undefined."""
    if len(x) != len(y):
        raise LengthMismatchError(f"{len(x)} != {len(y)}")
    if len(x) < 2:
        return None
    for value in (*x, *y):
        if not math.isfinite(value):
            raise ValueError("non-finite value in correlation input")
    rx, ry = _average_ranks(x), _average_ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def evaluate_language(language: str, items: Sequence[tuple[GoldLabels, Sequence[float], Sequence[float]]]) -> LanguageResult:
    predictions, gold, masked = assemble(items)
    value = spearman(predictions, gold)
    reason = None
    if value is None:
        reason = "fewer than two unmasked positions" if len(gold) < 2 else "constant prediction or gold vector"
    return LanguageResult(language, len(items), len(gold), masked, value, reason)


def macro_average(results: Mapping[str, LanguageResult]) -> tuple[float | None, str | None]:
    missing = [language for language in LANGUAGES if language not in results]
    if missing:
        return None, f"missing languages: {missing}"
    undefined = [language for language in LANGUAGES if results[language].spearman is None]
    if undefined:
        return None, f"undefined Spearman for: {undefined}"
    return sum(results[language].spearman for language in LANGUAGES) / len(LANGUAGES), None  # type: ignore[misc]


# --- pinned official code ---------------------------------------------------


def fetch_official(dest: Path = DEFAULT_OFFICIAL_DIR, opener: Callable[..., object] = urllib.request.urlopen) -> Path:
    for relative, digest in OFFICIAL_FILES.items():
        target = Path(dest) / relative
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == digest:
            continue
        url = f"https://raw.githubusercontent.com/{OFFICIAL_REPO}/{OFFICIAL_COMMIT}/{relative}"
        with opener(url, timeout=60) as response:  # type: ignore[operator]
            data = response.read()
        if hashlib.sha256(data).hexdigest() != digest:
            raise OfficialEvaluatorUnavailable(f"{url} does not match pinned sha256")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return Path(dest)


def _read_pinned(official_dir: Path, relative: str) -> bytes:
    path = Path(official_dir) / relative
    if not path.exists():
        raise OfficialEvaluatorUnavailable(f"{path} missing; run `make s1-fetch`")
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != OFFICIAL_FILES[relative]:
        raise OfficialEvaluatorUnavailable(f"{path} does not match pinned sha256")
    return data


def official_excluded_ids(official_dir: Path = DEFAULT_OFFICIAL_DIR) -> tuple[list[str], str]:
    data = _read_pinned(official_dir, "list_to_drop.txt")
    return [line.strip() for line in data.decode().splitlines() if line.strip()], OFFICIAL_FILES["list_to_drop.txt"]


@contextlib.contextmanager
def _isolated_import_context(official_dir: Path):
    """Stub the official loaders (they pull torch) and chdir for list_to_drop.txt."""
    saved = {name: sys.modules.get(name) for name in ("evaluation", "evaluation.utils")}
    package = types.ModuleType("evaluation")
    utils = types.ModuleType("evaluation.utils")

    def _unavailable(*_args, **_kwargs):
        raise OfficialEvaluatorUnavailable("official file loaders are intentionally not executed")

    utils.load_predictions = _unavailable  # type: ignore[attr-defined]
    utils.load_gold_data = _unavailable  # type: ignore[attr-defined]
    package.utils = utils  # type: ignore[attr-defined]
    sys.modules["evaluation"], sys.modules["evaluation.utils"] = package, utils
    previous = os.getcwd()
    os.chdir(official_dir)
    try:
        yield
    finally:
        os.chdir(previous)
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


def load_official_compute_correlations(official_dir: Path = DEFAULT_OFFICIAL_DIR) -> Callable:
    """Execute the pinned official evaluator module and return ``compute_correlations``.

    Requires ``nlpstats`` (see requirements-s1.lock).
    """
    source = _read_pinned(official_dir, "scripts/evaluate_predictions_admin.py")
    _read_pinned(official_dir, "list_to_drop.txt")
    try:
        import nlpstats  # noqa: F401
    except ImportError as error:
        raise OfficialEvaluatorUnavailable("nlpstats not installed; run `make s1-setup`") from error
    namespace: dict[str, object] = {"__name__": "swissgov_official_evaluator"}
    with _isolated_import_context(Path(official_dir)):
        exec(compile(source, "evaluate_predictions_admin.py", "exec"), namespace)
    return namespace["compute_correlations"]  # type: ignore[return-value]


def load_official_function(name: str, official_dir: Path = DEFAULT_OFFICIAL_DIR) -> Callable:
    """Extract one dependency-free function from the pinned ``evaluation/utils.py``."""
    source = _read_pinned(official_dir, "evaluation/utils.py").decode()
    tree = ast.parse(source)
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(nodes) != 1:
        raise OfficialEvaluatorUnavailable(f"function {name} not found in pinned evaluation/utils.py")
    namespace: dict[str, object] = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "evaluation/utils.py", "exec"), namespace)
    return namespace[name]  # type: ignore[return-value]
