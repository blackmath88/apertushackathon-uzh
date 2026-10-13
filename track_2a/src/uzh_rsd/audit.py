"""Audit supplement for a committed run: an accounting diagnostic, not a new result.

Re-reads the frozen ``raw.jsonl`` with the existing parsers (``parse_b0``,
``parse_b2``, ``locate``) and reports, with explicit counting units:

* B2 excerpts, one per item side: located exactly / normalised (ambiguous is a
  subset of located), not found, over the excerpt cap, empty;
* B2 items: projected (at least one side located) or unprojected, and why;
* documents affected;
* B0 parse status, finish reason and fallback tokens per side.

It never writes into the run directory, never changes parsing, the cap or
scores, and contains no correlation. Excerpt text is referenced by sha256 and
token length, not copied. Every file in the run directory is hashed before
and after, and the audit fails if anything changed.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

from .data_adapter import DEFAULT_DATA_DIR
from .evaluation import DEFAULT_OFFICIAL_DIR
from .methods import B2_MAX_EXCERPT_TOKENS, _severity, load_json_object, locate
from .runner import manifest_records, read_raw
from .scoring import parse_run

AUDIT_SCHEMA = "uzh-rsd.audit-supplement/v1"
LOCATED = ("exact", "normalised")


def _sha256(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def tree_hashes(directory: Path) -> dict[str, str]:
    directory = Path(directory)
    return {str(path.relative_to(directory)): _sha256(path.read_bytes())
            for path in sorted(directory.rglob("*")) if path.is_file()}


def code_revision(start: Path) -> dict:
    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=start, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    status = git("status", "--porcelain", "--", "src")
    return {"commit": git("rev-parse", "HEAD"), "src_dirty": None if status is None else bool(status)}


def _excerpt_ref(side: str, tokens: Sequence[str], excerpt: object) -> dict:
    text = excerpt if isinstance(excerpt, str) else ""
    spans, match = locate(tokens, text)
    ref = {"side": side, "match": match, "excerpt_tokens": len(text.split()), "excerpt_sha256": _sha256(text) if text else None}
    if match in LOCATED:
        ref["occurrences"] = len(spans)
    return ref


def _b2_items(inference, text: str) -> list[dict]:
    """Per-item accounting with the same rules as ``parse_b2``."""
    data, _mode = load_json_object(text)
    items = []
    for index, entry in enumerate(data["differences"]):
        if not isinstance(entry, dict) or not isinstance(entry.get("a", ""), str) or not isinstance(entry.get("b", ""), str):
            items.append({"index": index, "status": "invalid_item"})
            continue
        severity = _severity(entry.get("severity"))
        if severity is None:
            items.append({"index": index, "status": "invalid_severity"})
            continue
        sides = [_excerpt_ref("a", inference.text_a.tokens, entry.get("a", "")),
                 _excerpt_ref("b", inference.text_b.tokens, entry.get("b", ""))]
        located = [s for s in sides if s["match"] in LOCATED]
        lost = [s for s in sides if s["match"] not in LOCATED and s["match"] != "empty"]
        # complete: every non-empty excerpt located (an empty side is a one-sided item by design);
        # partial: one side located, the other not found or over the cap; unprojected: nothing located.
        status = "unprojected" if not located else "projected_partial" if lost else "projected_complete"
        items.append({"index": index, "status": status, "severity": severity, "sides": sides})
    return items


def audit_run(run_dir: Path, manifest: Mapping, data_dir: Path = DEFAULT_DATA_DIR, official_dir: Path = DEFAULT_OFFICIAL_DIR) -> dict:
    run_dir = Path(run_dir)
    before = tree_hashes(run_dir)
    raw = read_raw(run_dir / "raw.jsonl")
    records = manifest_records(manifest, data_dir)
    outputs, raw_by_key = parse_run(raw, records, official_dir)

    b0_docs, b2_docs = [], []
    excerpts = Counter()
    items = Counter()
    overlap = Counter()
    for inference, _gold in records:
        b0 = outputs.get((inference.id, "b0"))
        if b0 is not None:
            record = raw_by_key.get((inference.id, "b0"), {})
            doc = {"id": inference.id, "response_sha256": record.get("response_sha256"), "status": b0.status,
                   "finish_reason": b0.diagnostics.get("finish_reason"), "parse": b0.diagnostics.get("parse")}
            if b0.status == "ok":
                doc["strict_valid"] = b0.diagnostics["strict_valid"]
                for side in ("a", "b"):
                    d = b0.diagnostics[side]
                    doc[side] = {k: d[k] for k in ("tokens", "returned_items", "fallback", "model_punctuation_label", "out_of_range")}
            b0_docs.append(doc)

        b2 = outputs.get((inference.id, "b2"))
        if b2 is None:
            continue
        record = raw_by_key.get((inference.id, "b2"), {})
        doc = {"id": inference.id, "response_sha256": record.get("response_sha256"), "status": b2.status}
        if b2.status == "ok":
            doc_items = _b2_items(inference, record["generation"]["text"])
            for item in doc_items:
                items[item["status"]] += 1
                for side in item.get("sides", ()):
                    excerpts[side["match"]] += 1
                    if side.get("occurrences", 0) > 1:
                        excerpts["ambiguous (subset of located)"] += 1
                if "sides" in item:
                    overlap[" + ".join(sorted(s["match"] for s in item["sides"]))] += 1
            # Cross-check against the parser's own counters: same rules, same totals.
            diag = b2.diagnostics
            mine = {"items": len(doc_items),
                    "projected": sum(1 for i in doc_items if i["status"].startswith("projected")),
                    **{f"spans_{m}": sum(1 for i in doc_items for s in i.get("sides", ()) if s["match"] == m)
                       for m in ("exact", "normalised", "not_found", "too_long")},
                    "spans_ambiguous": sum(1 for i in doc_items for s in i.get("sides", ()) if s.get("occurrences", 0) > 1)}
            mismatch = {k: (v, diag[k]) for k, v in mine.items() if diag[k] != v}
            if mismatch:
                raise AssertionError(f"{inference.id}: audit disagrees with parse_b2 counters {mismatch}")
            doc["items"] = doc_items
            doc["affected"] = any(i["status"] != "projected_complete" for i in doc_items)
        b2_docs.append(doc)

    after = tree_hashes(run_dir)
    if before != after:
        raise AssertionError("run directory changed during audit")

    b0_ok = [d for d in b0_docs if d["status"] == "ok"]
    summary = {
        "b0": {
            "documents": len(b0_docs),
            "parseable": len(b0_ok),
            "strictly_valid": sum(1 for d in b0_ok if d["strict_valid"]),
            "status": dict(Counter(d["status"] for d in b0_docs)),
            "finish_reason_of_unparseable": dict(Counter(d["finish_reason"] for d in b0_docs if d["status"] != "ok")),
            "fallback_tokens": sum(d[s]["fallback"] for d in b0_ok for s in ("a", "b")),
            "tokens_in_parseable_documents": sum(d[s]["tokens"] for d in b0_ok for s in ("a", "b")),
            "model_punctuation_labels": sum(d[s]["model_punctuation_label"] for d in b0_ok for s in ("a", "b")),
        },
        "b2": {
            "units": {
                "item": "one entry of the model's `differences` list",
                "excerpt": "one side (a or b) of a valid item; each valid item has exactly two",
                "projected": "an item with at least one located side (as counted by parse_b2) = projected_complete + projected_partial",
                "projected_complete": "every non-empty excerpt located; an empty side is a one-sided item by design, not a loss",
                "projected_partial": "one excerpt located, the other not found or over the cap",
                "ambiguous": "a located excerpt with more than one occurrence; a subset of exact+normalised, not an extra category",
            },
            "excerpt_cap_tokens": B2_MAX_EXCERPT_TOKENS,
            "items": dict(items),
            "items_total": sum(items.values()),
            "excerpts": dict(excerpts),
            "excerpts_total": sum(v for k, v in excerpts.items() if not k.startswith("ambiguous")),
            "item_side_combinations": dict(sorted(overlap.items())),
            "documents_with_unlocated_or_over_cap_excerpts": [d["id"] for d in b2_docs if d.get("affected")],
        },
    }
    return {
        "schema": AUDIT_SCHEMA,
        "note": "Accounting diagnostic re-read from frozen raw responses with unchanged parsers. No scores; not a new experiment.",
        "run_id": run_dir.name,
        "inputs": {
            "raw_jsonl_sha256": before["raw.jsonl"],
            "manifest_sha256": _sha256(json.dumps(manifest, sort_keys=True)),
            "run_directory_files_sha256": before,
            "run_directory_unchanged": True,
        },
        "code": code_revision(Path(__file__).parent),
        "summary": summary,
        "b0_documents": b0_docs,
        "b2_documents": b2_docs,
    }


def render_markdown(audit: Mapping) -> str:
    b0, b2 = audit["summary"]["b0"], audit["summary"]["b2"]
    ex, it = b2["excerpts"], b2["items"]
    lines = [
        f"# Audit supplement — run `{audit['run_id']}`",
        "",
        audit["note"],
        "",
        f"- raw.jsonl sha256 `{audit['inputs']['raw_jsonl_sha256']}`; run directory unchanged: {audit['inputs']['run_directory_unchanged']}",
        f"- code commit `{audit['code']['commit']}` (src dirty: {audit['code']['src_dirty']}); invocation: `{audit.get('invocation', '')}`",
        "",
        "## B0",
        "",
        f"- Documents {b0['documents']}; parseable {b0['parseable']}; strictly valid {b0['strictly_valid']}.",
        f"- Unparseable by finish reason: {b0['finish_reason_of_unparseable']}.",
        f"- In parseable documents, {b0['fallback_tokens']} of {b0['tokens_in_parseable_documents']} tokens fell back to \"no difference\"; "
        f"{b0['model_punctuation_labels']} tokens got a model `-1` label (scored 0).",
        "",
        "## B2 (units: item = one `differences` entry; excerpt = one side of a valid item)",
        "",
        f"- Items {b2['items_total']}: " + ", ".join(f"{k} {v}" for k, v in sorted(it.items())) + ".",
        f"- Excerpts {b2['excerpts_total']} (= 2 × valid items): " + ", ".join(f"{k} {v}" for k, v in sorted(ex.items())) + ".",
        f"- Excerpt cap: {b2['excerpt_cap_tokens']} whitespace tokens; longer excerpts are counted `too_long` and not located.",
        "- `projected_complete`: every non-empty excerpt located. `projected_partial`: one side located, the other not found or over the cap. "
        "`ambiguous` is a subset of located excerpts, not an extra category.",
        "",
        "Item side combinations (each valid item counted once):",
        "",
        "| a + b match | items |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in b2["item_side_combinations"].items()],
        "",
        "| Document | items | complete | partial | unprojected | not_found excerpts | too_long excerpts | ambiguous excerpts |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for doc in audit["b2_documents"]:
        if doc["status"] != "ok":
            lines.append(f"| {doc['id']} | {doc['status']} | | | | | | |")
            continue
        sides = [s for i in doc["items"] for s in i.get("sides", ())]
        count = Counter(i["status"] for i in doc["items"])
        lines.append(f"| {doc['id']} | {len(doc['items'])} | {count['projected_complete']} | {count['projected_partial']} | {count['unprojected']} | "
                     f"{sum(s['match'] == 'not_found' for s in sides)} | {sum(s['match'] == 'too_long' for s in sides)} | "
                     f"{sum(s.get('occurrences', 0) > 1 for s in sides)} |")
    lines += ["", "Per-item detail (excerpt sha256 and token length, no text) is in `audit_supplement.json`.", ""]
    return "\n".join(lines)


def write_audit(run_dir: Path, out_dir: Path, manifest: Mapping, invocation: str, **kwargs) -> dict:
    run_dir, out_dir = Path(run_dir).resolve(), Path(out_dir).resolve()
    if out_dir == run_dir or run_dir in out_dir.parents:
        raise ValueError("audit output must be outside the run directory")
    audit = audit_run(run_dir, manifest, **kwargs)
    audit["invocation"] = invocation
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audit_supplement.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "audit_supplement.md").write_text(render_markdown(audit), encoding="utf-8")
    return audit
