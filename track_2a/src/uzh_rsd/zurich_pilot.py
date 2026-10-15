"""Compatibility facade for the original Stadt Zürich Scout API."""
from __future__ import annotations

from pathlib import Path

from .government_scout import (
    Captured,
    PageLinks,
    get_profile,
    normalize_url as _normalize_url,
    parse_page as _parse_page,
    potential_pairs as _potential_pairs,
    scout as _scout,
)

HOST = "www.stadt-zuerich.ch"


def normalize_url(value: str, base: str | None = None) -> str:
    return _normalize_url(value, "zurich-city", base)


def parse_page(html: bytes, url: str):
    return _parse_page(html, url, "zurich-city")


def potential_pairs(pages: list[Captured]):
    pairs = _potential_pairs(pages, "de", "en")
    return [{
        "de": pair["de"], "en": pair["en"],
        "pairing": "reciprocal_hreflang", "review": "candidate",
    } for pair in pairs]


def scout(seed: str, *, max_pages: int = 15, max_depth: int = 2,
          delay_seconds: float = 2.0, timeout: float = 12.0,
          out: str | Path | None = None):
    result = _scout(get_profile("zurich-city"), seeds=[seed], max_pages=max_pages,
                    max_depth=max_depth, delay_seconds=delay_seconds, timeout=timeout)
    captures = [Captured(**item) for item in result["captured"]]
    pairs = potential_pairs(captures)
    paired = {url for pair in pairs for url in (pair["de"], pair["en"])}
    legacy = {
        "schema": "lost-in-switzerland/zurich-scout/v1",
        "seed": normalize_url(seed),
        "retrieval_policy": {**result.get("retrieval_policy", {}), "host": HOST},
        "captured": result["captured"], "pairs": pairs,
        "unpaired_count": len(captures) - len(paired),
        "failures": [item for item in result["audit"] if item.get("state") != "FETCHED"],
        "model_calls": 0, "disclaimer": result.get("disclaimer"),
    }
    if out is not None:
        from .government_scout import _write_json
        _write_json(out, legacy)
    return legacy
