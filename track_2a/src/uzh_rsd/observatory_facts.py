"""Literal observations for human inspection. No semantic correspondence claims.

Values present on only one side are NOT automatically differences/omissions.
The versioned output records exact source ranges and extracted-block context.
"""
from __future__ import annotations

import re
from .observatory_capture import verify_document

PATTERN = re.compile(
    r"(?P<phone>\+41(?:[ \u00a0]\d{2,3}){3,5})|"
    r"(?P<date>\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}\.\d{1,2}\.\d{4}\b)|"
    r"(?P<time>\b\d{1,2}[.:]\d{2}[–\-]\d{1,2}[.:]\d{2}\b)|"
    r"(?P<number>\b\d+(?:[.,:]\d+)*\b)"
)


def observe(document):
    verify_document(document)
    observations = []
    for block in document["blocks"]:
        for match in PATTERN.finditer(block["text"]):
            observations.append({"kind": match.lastgroup, "value": match.group(),
                                 "start": block["start"] + match.start(), "end": block["start"] + match.end(),
                                 "block_ids": [block["id"]], "context": block["text"],
                                 "source_url": document["url"], "capture_id": document["capture_id"]})
    return {"schema": "lost-in-switzerland/literal-observations/v1", "source_kind": "observed_source_facts",
            "capture_id": document["capture_id"], "observations": observations,
            "semantic_analysis": False, "confidence": None}


def compare_values(pair):
    observations = {lang: observe(pair[lang])["observations"] for lang in ("de", "en")}
    keys = sorted({(o["kind"], o["value"]) for values in observations.values() for o in values})
    return [{"kind": kind, "value": value,
             "de": [o for o in observations["de"] if (o["kind"], o["value"]) == (kind, value)],
             "en": [o for o in observations["en"] if (o["kind"], o["value"]) == (kind, value)],
             "interpretation": "literal_occurrences_only_not_semantic_difference"} for kind, value in keys]
