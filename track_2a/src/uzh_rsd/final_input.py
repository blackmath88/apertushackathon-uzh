"""Convert official-shaped SwissGov-RSD JSONL into the gold-blind final input.

Reads one file per language (``--source de=PATH`` …), in the order given, and
writes:

* ``final_input.jsonl``: ``{id, language, text_a, text_b}`` per record, in
  mechanical source order. ``text_a``/``text_b`` are the official
  *tokenized* fields copied verbatim. ``final.py`` splits them with the same
  ``tokenize`` as the development adapter, so prediction vectors align with
  the official tokens. The untokenized fields are never used.
* ``final_input.provenance.json``: source file digests, record counts and the
  mechanical source order.
* ``contract.draft.json``: an *unresolved* contract whose ``order`` is that
  source order. Mechanical source order is not the organisers' "full-set
  order", and the draft carries no evidence, so ``uzh_rsd.final`` refuses it
  until someone fills it from the organiser answer.

Annotation fields (``labels_a``/``labels_b``) are recognised but their values
are never read, copied or logged. Unknown fields, malformed records, duplicate
IDs and language mismatches are rejected with line numbers and field names
only. No development exclusion (``list_to_drop.txt``) is applied: every record
in the sources is kept.

This module never downloads anything and does not touch the development split
guard; it reads only the files it is given.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .data_adapter import LANGUAGES
from .final import CONTRACT_SCHEMA
from .tokens import tokenize

PROVENANCE_SCHEMA = "uzh-rsd.final-input-provenance/v1"
CONVERTER_VERSION = "final-input-v1"
TEXT_FIELDS = ("id", "text_a", "text_b")
IGNORED_FIELDS = frozenset({"labels_a", "labels_b", "text_a_untokenized", "text_b_untokenized", "page_en", "page_other", "subset"})
KNOWN_FIELDS = frozenset(TEXT_FIELDS) | IGNORED_FIELDS


class ConversionError(ValueError):
    """Source record rejected. Messages carry line numbers and field names, never values."""


def convert_source(path: Path, language: str) -> tuple[list[dict], dict]:
    if language not in LANGUAGES:
        raise ConversionError(f"unknown language {language!r}")
    data = Path(path).read_bytes()
    records = []
    for number, line in enumerate(data.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except ValueError:
            raise ConversionError(f"{Path(path).name}:{number}: not valid JSON") from None
        if not isinstance(raw, dict):
            raise ConversionError(f"{Path(path).name}:{number}: not an object")
        unknown = sorted(set(raw) - KNOWN_FIELDS)
        missing = [field for field in TEXT_FIELDS if field not in raw]
        if unknown or missing:
            raise ConversionError(f"{Path(path).name}:{number}: unknown fields {unknown}, missing fields {missing}")
        identifier, text_a, text_b = raw["id"], raw["text_a"], raw["text_b"]
        if not all(isinstance(value, str) for value in (identifier, text_a, text_b)):
            raise ConversionError(f"{Path(path).name}:{number}: id/text_a/text_b must be strings")
        if not identifier.startswith(f"admin_{language}_"):
            raise ConversionError(f"{Path(path).name}:{number}: id does not belong to language {language!r}")
        if not len(tokenize(text_a)) or not len(tokenize(text_b)):
            raise ConversionError(f"{Path(path).name}:{number}: empty tokenized text")
        records.append({"id": identifier, "language": language, "text_a": text_a, "text_b": text_b})
    if not records:
        raise ConversionError(f"{Path(path).name}: no records")
    return records, {"file": Path(path).name, "language": language, "sha256": hashlib.sha256(data).hexdigest(),
                     "bytes": len(data), "records": len(records)}


def convert(sources: list[tuple[str, Path]], out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    targets = [out_dir / name for name in ("final_input.jsonl", "final_input.provenance.json", "contract.draft.json")]
    existing = [str(path) for path in targets if path.exists()]
    if existing:
        raise ConversionError(f"refusing to overwrite {existing}")
    languages = [language for language, _ in sources]
    if len(set(languages)) != len(languages):
        raise ConversionError("each language may be given once")
    records, provenance_sources, seen = [], [], set()
    for language, path in sources:
        converted, info = convert_source(path, language)
        for record in converted:
            if record["id"] in seen:
                raise ConversionError(f"duplicate id {record['id']!r}")
            seen.add(record["id"])
        records.extend(converted)
        provenance_sources.append(info)

    out_dir.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records).encode("utf-8")
    targets[0].write_bytes(payload)
    order = [{"id": record["id"], "language": record["language"]} for record in records]
    provenance = {
        "schema": PROVENANCE_SCHEMA,
        "converter": CONVERTER_VERSION,
        "sources": provenance_sources,
        "output": {"file": targets[0].name, "sha256": hashlib.sha256(payload).hexdigest(), "records": len(records)},
        "fields_copied": ["id", "text_a (tokenized, verbatim)", "text_b (tokenized, verbatim)"],
        "fields_ignored_unread": sorted(IGNORED_FIELDS),
        "development_exclusions_applied": False,
        "source_order": order,
        "note": "source_order is the mechanical order of the given files and lines; it is not an organiser-confirmed full-set order.",
    }
    targets[1].write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    draft = {
        "schema": CONTRACT_SCHEMA,
        "status": "unresolved",
        "evidence": "",
        "decisions": {"full_set_order": "unresolved", "dropped_ids": "unresolved", "output_layout": "unresolved"},
        "order": order,
        "_comment": "Draft from mechanical source order. Edit order and decisions to match the organiser answer, "
                    "record that answer in evidence, then set status to confirmed. uzh_rsd.final refuses this draft as is.",
    }
    targets[2].write_text(json.dumps(draft, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"status": "ok", "records": len(records), "out_dir": str(out_dir), "input_sha256": provenance["output"]["sha256"],
            "per_language": {info["language"]: info["records"] for info in provenance_sources}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m uzh_rsd.final_input",
                                     description="Official-shaped SwissGov-RSD JSONL → gold-blind final input (no download).")
    parser.add_argument("--source", action="append", required=True, metavar="LANG=PATH", help="one per language, in output order")
    parser.add_argument("--out", type=Path, required=True, help="directory for final_input.jsonl, provenance and contract draft")
    args = parser.parse_args(argv)
    try:
        sources = []
        for spec in args.source:
            language, sep, path = spec.partition("=")
            if not sep or not path:
                raise ConversionError(f"--source must be LANG=PATH, got {spec!r}")
            sources.append((language, Path(path)))
        result = convert(sources, args.out)
    except (ConversionError, OSError) as error:
        print(json.dumps({"status": "error", "reason": str(error)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
