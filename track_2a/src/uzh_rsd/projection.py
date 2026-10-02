from __future__ import annotations

from collections.abc import Iterable

from .contracts import SemanticDifference, TokenSpan


def _apply_span(scores: list[float], span: TokenSpan | None, severity: float) -> None:
    if span is None:
        return
    if span.end > len(scores):
        raise ValueError(f"Span {span.start}:{span.end} exceeds token vector length {len(scores)}")
    for index in range(span.start, span.end):
        scores[index] = max(scores[index], severity)


def project_differences(source_token_count: int, target_token_count: int, differences: Iterable[SemanticDifference]) -> tuple[list[float], list[float]]:
    """Project sparse span-level differences to token-level severity scores."""
    source_scores = [0.0] * source_token_count
    target_scores = [0.0] * target_token_count
    for difference in differences:
        _apply_span(source_scores, difference.source, difference.severity)
        _apply_span(target_scores, difference.target, difference.severity)
    return source_scores, target_scores
