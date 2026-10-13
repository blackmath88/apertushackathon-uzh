"""Contract-only adapter for reviewed Zürich page captures.

This module performs no network access and contains no city data.  It only
maps caller-supplied, already-reviewed token arrays into the SDM input shape.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from ..data_adapter import InferenceInput
from ..tokens import tokenize


@dataclass(frozen=True)
class ZurichPair:
    pair_id: str
    english_text: str
    german_text: str
    english_url: str
    german_url: str
    pairing: str = "manually_reviewed_or_reciprocal_hreflang"


def adapt(pair: ZurichPair) -> InferenceInput:
    if pair.pairing != "manually_reviewed_or_reciprocal_hreflang":
        raise ValueError("Zürich pairing must be explicitly reviewed")
    if not pair.pair_id or not pair.english_url or not pair.german_url:
        raise ValueError("source identity and URLs are required")
    # doc_index is intentionally not inferred; city records never enter the benchmark loader.
    stable_id = int(hashlib.sha256(pair.pair_id.encode()).hexdigest()[:12], 16)
    return InferenceInput(
        id=f"zurich_de_{stable_id}", language="de",
        text_a=tokenize(pair.english_text), text_b=tokenize(pair.german_text),
        page_en=pair.english_url, page_other=pair.german_url,
    )
