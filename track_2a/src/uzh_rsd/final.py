"""Final inference: B2 predictions for an explicitly supplied input, no scoring.

A separate, explicit operation, deliberately not part of ``cli.py``:

* It does not use split names, the dataset loaders, or the development split
  guard. It never downloads anything. Input comes only from ``--input``.
* It runs only when ``--contract`` is a *confirmed* output contract (order,
  dropped-ID policy, layout). The committed template is ``unresolved`` and is
  refused. A contract records what the organisers decided; this code cannot
  verify that, so it requires a non-empty evidence reference and records it.
* The input adapter is gold-blind: each record must have exactly ``id``,
  ``language``, ``text_a`` and ``text_b``. Any other field is rejected and never
  forwarded, so labels bundled with text cannot reach a prompt.
* B2 is frozen: the same prompt (``render_b2``), parser (``parse_b2``),
  projection and 40-token excerpt cap as the pilot. One attempt per call, an
  explicit request timeout, no retries.
* It never imports the official evaluator or the scorer and computes no scores.
* The output directory must not exist. ``final_meta.json`` says ``incomplete``
  until every document has a validated prediction; only then are prediction
  files written and the status set to ``complete``. A failed call or an
  unparseable response leaves the run incomplete with a nonzero exit; nothing
  is zero-filled or dropped.

Usage (after the owner approves a real run)::

    LLM_NAME=… LLM_BASE_URL=… LLM_API_KEY=… \\
    python -m uzh_rsd.final --contract final_contract.json --input final_input.jsonl --out final_runs/<run id>
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

from .data_adapter import LANGUAGES, InferenceInput
from .methods import B2_MAX_EXCERPT_TOKENS, parse_b2
from .prompts import B2_PROMPT_VERSION
from .runner import MAX_NEW_TOKENS, read_raw, run_inference
from .tokens import tokenize

CONTRACT_SCHEMA = "uzh-rsd.final-contract/v1"
META_SCHEMA = "uzh-rsd.final-run-meta/v1"
PREDICTION_SCHEMA = "uzh-rsd.final-predictions/provisional-v1"
INPUT_FIELDS = frozenset({"id", "language", "text_a", "text_b"})
DECISIONS = ("full_set_order", "dropped_ids", "output_layout")
SUPPORTED_LAYOUTS = frozenset({"per_language_jsonl"})
ENDPOINT_ENV = ("LLM_NAME", "LLM_BASE_URL", "LLM_API_KEY")
TRACK_ROOT = Path(__file__).resolve().parents[2]
PROTECTED_DIRS = ("results", "diagnostics", "manifests", "data")
EXIT_OK, EXIT_INVALID, EXIT_BLOCKED, EXIT_INCOMPLETE = 0, 2, 3, 4


class FinalBlocked(Exception):
    """Configuration does not permit a final run (checked before any data access)."""


class InvalidFinalInput(ValueError):
    """Input or prediction violates the contract (no repair is attempted)."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- configuration (validated before input access or backend construction) ---


def load_contract(path: Path) -> dict:
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    if contract.get("schema") != CONTRACT_SCHEMA:
        raise FinalBlocked(f"contract schema must be {CONTRACT_SCHEMA!r}")
    if contract.get("status") != "confirmed":
        raise FinalBlocked(f"contract status is {contract.get('status')!r}; a final run needs an organiser-confirmed contract")
    evidence = contract.get("evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        raise FinalBlocked("contract has no evidence reference for the organiser decisions")
    decisions = contract.get("decisions") or {}
    open_items = [key for key in DECISIONS if not isinstance(decisions.get(key), str) or decisions[key] in ("", "unresolved")]
    if open_items:
        raise FinalBlocked(f"unresolved contract decisions: {open_items}")
    if decisions["output_layout"] not in SUPPORTED_LAYOUTS:
        raise FinalBlocked(f"output layout {decisions['output_layout']!r} is not implemented; supported: {sorted(SUPPORTED_LAYOUTS)}")
    order = contract.get("order")
    if not isinstance(order, list) or not order:
        raise FinalBlocked("contract has no document order")
    seen = set()
    for position, entry in enumerate(order):
        if not isinstance(entry, dict) or set(entry) != {"id", "language"}:
            raise FinalBlocked(f"order[{position}] must be exactly {{id, language}}")
        if entry["language"] not in LANGUAGES:
            raise FinalBlocked(f"order[{position}]: unknown language {entry['language']!r}")
        if entry["id"] in seen:
            raise FinalBlocked(f"duplicate id in contract order: {entry['id']!r}")
        seen.add(entry["id"])
    return contract


def check_output_dir(out_dir: Path) -> Path:
    out_dir = Path(out_dir).resolve()
    if out_dir.exists():
        raise FinalBlocked(f"{out_dir} exists; final runs never overwrite or append")
    for name in PROTECTED_DIRS:
        protected = (TRACK_ROOT / name).resolve()
        if out_dir == protected or protected in out_dir.parents:
            raise FinalBlocked(f"{out_dir} is inside protected {name}/")
    return out_dir


# --- gold-blind input adapter -------------------------------------------------


def load_final_input(path: Path, contract: Mapping) -> list[InferenceInput]:
    """Strict adapter: exact fields, exact ID set and order of the contract."""
    items: dict[str, InferenceInput] = {}
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            raise InvalidFinalInput(f"line {number}: not an object")
        extra = sorted(set(record) - INPUT_FIELDS)
        missing = sorted(INPUT_FIELDS - set(record))
        if extra or missing:
            # Field names only: values (possibly labels) are never echoed.
            raise InvalidFinalInput(f"line {number}: fields must be exactly {sorted(INPUT_FIELDS)}; extra {extra}, missing {missing}")
        if not all(isinstance(record[key], str) for key in INPUT_FIELDS):
            raise InvalidFinalInput(f"line {number}: all fields must be strings")
        if record["id"] in items:
            raise InvalidFinalInput(f"line {number}: duplicate id {record['id']!r}")
        text_a, text_b = tokenize(record["text_a"]), tokenize(record["text_b"])
        if not len(text_a) or not len(text_b):
            raise InvalidFinalInput(f"line {number}: empty text")
        items[record["id"]] = InferenceInput(id=record["id"], language=record["language"], text_a=text_a, text_b=text_b, page_en="", page_other="")
    expected = [entry["id"] for entry in contract["order"]]
    if set(items) != set(expected):
        raise InvalidFinalInput(f"input ids differ from contract: missing {sorted(set(expected) - set(items))[:10]}, "
                                f"unexpected {sorted(set(items) - set(expected))[:10]}")
    for entry in contract["order"]:
        if items[entry["id"]].language != entry["language"]:
            raise InvalidFinalInput(f"{entry['id']}: language {items[entry['id']].language!r} differs from contract {entry['language']!r}")
    return [items[identifier] for identifier in expected]


# --- predictions ---------------------------------------------------------------


def validate_prediction(item: InferenceInput, labels_a: Sequence[float], labels_b: Sequence[float]) -> None:
    for side, labels, text in (("a", labels_a, item.text_a), ("b", labels_b, item.text_b)):
        if len(labels) != len(text):
            raise InvalidFinalInput(f"{item.id}.{side}: {len(labels)} values for {len(text)} tokens")
        for position, value in enumerate(labels):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise InvalidFinalInput(f"{item.id}.{side}[{position}]: {value!r} is not a finite difference in [0, 1]")


def _source_commit() -> dict:
    def git(*args):
        try:
            return subprocess.run(["git", "-C", str(TRACK_ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    status = git("status", "--porcelain", "--", "src")
    return {"commit": git("rev-parse", "HEAD"), "src_dirty": None if status is None else bool(status)}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _write_meta(out_dir: Path, meta: Mapping) -> None:
    (out_dir / "final_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_final(backend, contract: Mapping, contract_bytes: bytes, items: Sequence[InferenceInput], input_bytes: bytes,
              out_dir: Path, *, run_id: str, invocation: str, model: Mapping) -> tuple[dict, int]:
    out_dir.mkdir(parents=True, exist_ok=False)
    meta = {
        "schema": META_SCHEMA,
        "status": "incomplete",
        "run_id": run_id,
        "note": "Final inference only: no labels, no scores, no evaluator.",
        "strategy": {"method": "b2", "prompt_version": B2_PROMPT_VERSION, "parser": "uzh_rsd.methods.parse_b2",
                     "projection": "uzh_rsd.projection.project_differences (max severity per token, difference = severity/5)",
                     "excerpt_cap_tokens": B2_MAX_EXCERPT_TOKENS, "max_new_tokens": MAX_NEW_TOKENS["b2"],
                     "decoding": "greedy (temperature 0), one attempt per call, no retries"},
        "model": dict(model),
        "backend": backend.describe(),
        "source": _source_commit(),
        "invocation": invocation,
        "contract": {"sha256": _sha256(contract_bytes), "evidence": contract["evidence"], "decisions": contract["decisions"]},
        "input": {"sha256": _sha256(input_bytes), "documents": len(items),
                  "per_language": dict(Counter(item.language for item in items))},
        "output_schema": PREDICTION_SCHEMA,
        "started_utc": _now(),
    }
    _write_meta(out_dir, meta)

    counts = run_inference(backend, items, ("b2",), out_dir / "raw.jsonl", run_id=run_id)
    raw = {record["id"]: record for record in read_raw(out_dir / "raw.jsonl")}
    documents, predictions, problems = [], {}, []
    for item in items:
        record = raw.get(item.id)
        if record is None or record["status"] != "returned":
            status = "call_failed" if record is not None else "not_run"
            error = ((record or {}).get("generation") or {}).get("error")
            documents.append({"id": item.id, "status": status, "error": error})
            problems.append(f"{item.id}: {status}")
            continue
        output = parse_b2(item, record["generation"]["text"])
        entry = {"id": item.id, "status": output.status, "response_sha256": record.get("response_sha256"),
                 "finish_reason": record["generation"].get("finish_reason"), "diagnostics": output.diagnostics}
        if output.diff_a is None:
            problems.append(f"{item.id}: {output.status}")
        else:
            try:
                validate_prediction(item, output.diff_a, output.diff_b)
            except InvalidFinalInput as error:
                entry["status"] = "invalid_prediction"
                problems.append(str(error))
            else:
                predictions[item.id] = (output.diff_a, output.diff_b)
        documents.append(entry)
    (out_dir / "diagnostics.json").write_text(json.dumps({"counts": counts, "documents": documents}, indent=2, ensure_ascii=False) + "\n",
                                              encoding="utf-8")

    meta.update(counts=counts, problems=problems, finished_utc=_now())
    if problems:
        _write_meta(out_dir, meta)  # still "incomplete": no prediction files are written
        return {"status": "incomplete", "out_dir": str(out_dir), "problems": problems[:20], "counts": counts}, EXIT_INCOMPLETE

    target = out_dir / "predictions"
    target.mkdir()
    files = {}
    for language in LANGUAGES:
        lines = [json.dumps({"id": item.id, "text_a": item.text_a.text, "text_b": item.text_b.text,
                             "labels_a": predictions[item.id][0], "labels_b": predictions[item.id][1]}, ensure_ascii=False)
                 for item in items if item.language == language]
        if lines:
            path = target / f"predictions_{language}.jsonl"
            path.write_text("".join(line + "\n" for line in lines), encoding="utf-8")
            files[path.name] = {"records": len(lines), "sha256": _sha256(path.read_bytes())}
    meta.update(status="complete", prediction_files=files)
    _write_meta(out_dir, meta)
    return {"status": "complete", "out_dir": str(out_dir), "prediction_files": files, "counts": counts}, EXIT_OK


# --- entry point -----------------------------------------------------------------


def main(argv: list[str] | None = None, *, backend_factory=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m uzh_rsd.final", description="Final B2 inference on an explicit, gold-blind input (no scoring).")
    parser.add_argument("--contract", type=Path, required=True, help="organiser-confirmed output contract (JSON)")
    parser.add_argument("--input", type=Path, required=True, help="gold-blind input JSONL: id, language, text_a, text_b")
    parser.add_argument("--out", type=Path, required=True, help="new run directory (must not exist)")
    parser.add_argument("--timeout-s", type=float, default=300.0, help="per-request timeout; one attempt per call")
    parser.add_argument("--model-revision", default=None, help="declared model revision, recorded as declared (not verified)")
    args = parser.parse_args(argv)

    def emit(result: dict, code: int) -> int:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return code

    # 1. Configuration only: contract, endpoint variables, output path. No input read, no backend.
    try:
        contract_bytes = args.contract.read_bytes()
        contract = load_contract(args.contract)
        missing = [name for name in ENDPOINT_ENV if not os.environ.get(name)]
        if missing and backend_factory is None:
            raise FinalBlocked(f"missing environment variables: {missing}")
        if args.timeout_s <= 0:
            raise FinalBlocked("--timeout-s must be positive")
        out_dir = check_output_dir(args.out)
    except FinalBlocked as error:
        return emit({"status": "BLOCKED", "reason": str(error)}, EXIT_BLOCKED)
    except (OSError, ValueError) as error:
        return emit({"status": "BLOCKED", "reason": f"contract unreadable: {type(error).__name__}: {error}"}, EXIT_BLOCKED)

    # 2. Input, validated against the contract before any backend exists.
    try:
        input_bytes = args.input.read_bytes()
        items = load_final_input(args.input, contract)
    except (OSError, ValueError) as error:
        return emit({"status": "invalid_input", "reason": str(error)}, EXIT_INVALID)

    # 3. Backend, then inference.
    if backend_factory is not None:
        backend = backend_factory(args.timeout_s)
    else:
        from .backends import OpenAICompatibleBackend
        backend = OpenAICompatibleBackend(os.environ["LLM_BASE_URL"], os.environ["LLM_NAME"], os.environ["LLM_API_KEY"], timeout_s=args.timeout_s)
    model = {"name": os.environ.get("LLM_NAME") or backend.describe().get("model"),
             "declared_revision": args.model_revision,
             "note": "A model name does not pin weights; the provider-side revision is unknown unless the provider states it."}
    run_id = out_dir.name
    invocation = "python -m uzh_rsd.final " + " ".join(argv if argv is not None else sys.argv[1:])
    result, code = run_final(backend, contract, contract_bytes, items, input_bytes, out_dir, run_id=run_id, invocation=invocation, model=model)
    return emit(result, code)


if __name__ == "__main__":
    sys.exit(main())
