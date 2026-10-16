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
# "confirmed": decisions confirmed by the organisers. "owner_approved_provisional": the owner
# approved running with the stated decisions and their basis; NOT organiser-confirmed.
ACCEPTED_STATUSES = frozenset({"confirmed", "owner_approved_provisional"})
META_SCHEMA = "uzh-rsd.final-run-meta/v1"
PREDICTION_SCHEMA = "uzh-rsd.final-predictions/provisional-v1"
INPUT_FIELDS = frozenset({"id", "language", "text_a", "text_b"})
DECISIONS = ("full_set_order", "dropped_ids", "output_layout")
SUPPORTED_LAYOUTS = frozenset({"per_language_jsonl"})
ENDPOINT_ENV = ("LLM_NAME", "LLM_BASE_URL", "LLM_API_KEY")
TRACK_ROOT = Path(__file__).resolve().parents[2]
PROTECTED_DIRS = ("results", "diagnostics", "manifests", "data")
EXIT_OK, EXIT_INVALID, EXIT_BLOCKED, EXIT_INCOMPLETE, EXIT_INTERRUPTED = 0, 2, 3, 4, 130


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
    status = contract.get("status")
    if status not in ACCEPTED_STATUSES:
        raise FinalBlocked(f"contract status is {status!r}; a final run needs status 'confirmed' (organiser-confirmed) "
                           f"or 'owner_approved_provisional' (owner-approved, not organiser-confirmed)")
    evidence = contract.get("evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        raise FinalBlocked("contract has no evidence reference for its decisions")
    if status == "owner_approved_provisional":
        approval = contract.get("owner_approval") or {}
        basis = contract.get("decision_basis") or {}
        if not all(isinstance(approval.get(key), str) and approval[key].strip() for key in ("approved_by", "approved_utc", "scope")):
            raise FinalBlocked("owner_approved_provisional needs owner_approval {approved_by, approved_utc, scope}")
        if not all(isinstance(basis.get(key), str) and basis[key].strip() for key in DECISIONS):
            raise FinalBlocked(f"owner_approved_provisional needs decision_basis for {list(DECISIONS)}")
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
    commit = git("rev-parse", "HEAD")
    if commit is None and os.environ.get("UZH_SOURCE_COMMIT", "").strip():
        # Docker image without git: the host passes its checkout's commit; recorded as declared.
        dirty = {"true": True, "false": False}.get(os.environ.get("UZH_SOURCE_DIRTY", ""))
        return {"commit": os.environ["UZH_SOURCE_COMMIT"], "src_dirty": dirty, "source": "declared by host via UZH_SOURCE_COMMIT"}
    status = git("status", "--porcelain", "--", "src")
    return {"commit": commit, "src_dirty": None if status is None else bool(status), "source": "git" if commit else "unavailable"}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def _write_meta(out_dir: Path, meta: Mapping) -> None:
    """Atomic replace: ``final_meta.json`` is the run's single commit point."""
    staging = out_dir / "final_meta.json.partial"
    staging.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(staging, out_dir / "final_meta.json")


def run_final(backend, contract: Mapping, contract_bytes: bytes, items: Sequence[InferenceInput], input_bytes: bytes,
              out_dir: Path, *, run_id: str, invocation: str, model: Mapping, method: str = "b2",
              total_timeout_s: float | None = None, clock=None, after_call=None,
              extra_meta: Mapping | None = None) -> tuple[dict, int]:
    if method not in {"b2", "b2-windowed-v2"}:
        raise ValueError(f"unsupported final method {method!r}")
    if method == "b2-windowed-v2":
        from .windowed_b2 import (MAX_NEW_TOKENS as WINDOWED_MAX_NEW_TOKENS,
                                  METHOD_VERSION, PROMPT_VERSION, WINDOW_OVERLAP,
                                  WINDOW_TOKENS)
        strategy = {
            "method": METHOD_VERSION, "prompt_version": PROMPT_VERSION,
            "segmentation": {"unit": "official whitespace tokens", "window_tokens": WINDOW_TOKENS,
                             "overlap_tokens": WINDOW_OVERLAP, "sentence_boundary_preferred": True},
            "alignment": "bidirectional deterministic best match; shared structural anchors dominate proportional fallback; crossings allowed",
            "projection": "local B2 max-severity scores mapped by exact original token index; overlaps merged by max",
            "completion": "all planned calls valid and every token processed; explicit empty differences is processed zero; failures are never filled",
            "excerpt_cap_tokens": B2_MAX_EXCERPT_TOKENS, "max_new_tokens": WINDOWED_MAX_NEW_TOKENS,
            "decoding": "greedy (temperature 0), one attempt per window, no retries",
        }
    else:
        strategy = {"method": "b2", "prompt_version": B2_PROMPT_VERSION, "parser": "uzh_rsd.methods.parse_b2",
                    "projection": "uzh_rsd.projection.project_differences (max severity per token, difference = severity/5)",
                    "excerpt_cap_tokens": B2_MAX_EXCERPT_TOKENS, "max_new_tokens": MAX_NEW_TOKENS["b2"],
                    "decoding": "greedy (temperature 0), one attempt per call, no retries"}
    out_dir.mkdir(parents=True, exist_ok=False)
    meta = {
        "schema": META_SCHEMA,
        "status": "incomplete",
        "run_id": run_id,
        "note": "Final inference only: no labels, no scores, no evaluator.",
        "strategy": strategy,
        "model": dict(model),
        "backend": backend.describe(),
        "source": _source_commit(),
        "invocation": invocation,
        "contract": {"sha256": _sha256(contract_bytes), "status": contract["status"], "evidence": contract["evidence"],
                     "decisions": contract["decisions"], "decision_basis": contract.get("decision_basis"),
                     "owner_approval": contract.get("owner_approval")},
        "input": {"sha256": _sha256(input_bytes), "documents": len(items),
                  "per_language": dict(Counter(item.language for item in items)),
                  "order": [item.id for item in items],
                  "language_order": {language: [item.id for item in items if item.language == language]
                                     for language in LANGUAGES}},
        "output_schema": PREDICTION_SCHEMA,
        "started_utc": _now(),
        **dict(extra_meta or {}),
    }
    _write_meta(out_dir, meta)
    try:
        if method == "b2-windowed-v2":
            import time
            deadline = None if total_timeout_s is None else (clock or time.monotonic)() + total_timeout_s
            return _execute_windowed(backend, items, out_dir, run_id, meta, deadline, clock, after_call)
        return _execute(backend, items, out_dir, run_id, meta, after_call)
    except BaseException as error:
        # Any exception or interrupt before the final metadata commit leaves the run
        # incomplete. Evidence already on disk (raw.jsonl, diagnostics, even a renamed
        # predictions/ directory) is kept for diagnosis; final_meta.json decides.
        meta.update(status="incomplete", interrupted={"type": type(error).__name__}, finished_utc=_now())
        try:
            _write_meta(out_dir, meta)
        except Exception:  # pragma: no cover - best effort; the earlier "incomplete" meta remains
            pass
        if isinstance(error, Exception):
            return {"status": "incomplete", "out_dir": str(out_dir), "interrupted": type(error).__name__}, EXIT_INCOMPLETE
        raise


def _execute(backend, items: Sequence[InferenceInput], out_dir: Path, run_id: str, meta: dict, after_call=None) -> tuple[dict, int]:
    counts = run_inference(backend, items, ("b2",), out_dir / "raw.jsonl", run_id=run_id, after_call=after_call)
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

    # Written to a staging directory and renamed only after every file is written;
    # the atomic metadata write right after it is the commit point. Readers must
    # trust ``final_meta.json`` status, never the mere presence of files.
    target = out_dir / "predictions.partial"
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
    target.rename(out_dir / "predictions")
    # An interruption here leaves predictions/ present with an "incomplete" meta;
    # verify_run() rejects that state.
    _write_meta(out_dir, {**meta, "status": "complete", "prediction_files": files})
    return {"status": "complete", "out_dir": str(out_dir), "prediction_files": files, "counts": counts}, EXIT_OK


def _write_predictions(items: Sequence[InferenceInput], predictions: Mapping[str, tuple[Sequence[float], Sequence[float]]],
                       out_dir: Path, meta: dict) -> dict:
    target = out_dir / "predictions.partial"
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
    target.rename(out_dir / "predictions")
    _write_meta(out_dir, {**meta, "status": "complete", "prediction_files": files})
    return files


def _execute_windowed(backend, items: Sequence[InferenceInput], out_dir: Path, run_id: str, meta: dict,
                      deadline: float | None, clock=None, after_call=None) -> tuple[dict, int]:
    import time
    from .windowed_b2 import execute_document

    ledger = out_dir / "window-ledger.jsonl"
    predictions: dict[str, tuple[Sequence[float], Sequence[float]]] = {}
    documents, problems = [], []
    counts = {"documents": len(items), "complete_documents": 0, "planned_requests": 0,
              "completed_requests": 0, "call_failed_or_invalid": 0}
    for item in items:
        result = execute_document(backend, item, ledger, run_id=run_id, total_deadline=deadline,
                                  clock=clock or time.monotonic, after_call=after_call)
        counts["planned_requests"] += result["planned_requests"]
        counts["completed_requests"] += result["completed_requests"]
        counts["call_failed_or_invalid"] += len(result["problems"])
        document = {key: value for key, value in result.items() if key not in {"labels_a", "labels_b"}}
        documents.append(document)
        if result["status"] != "complete":
            problems.extend(f"{item.id}:{problem}" for problem in result["problems"])
            continue
        validate_prediction(item, result["labels_a"], result["labels_b"])
        predictions[item.id] = (result["labels_a"], result["labels_b"])
        counts["complete_documents"] += 1
    (out_dir / "diagnostics.json").write_text(json.dumps({"counts": counts, "documents": documents}, indent=2,
                                                           ensure_ascii=False) + "\n", encoding="utf-8")
    meta.update(counts=counts, problems=problems, finished_utc=_now())
    if problems:
        _write_meta(out_dir, meta)
        return {"status": "incomplete", "out_dir": str(out_dir), "problems": problems[:20], "counts": counts}, EXIT_INCOMPLETE
    files = _write_predictions(items, predictions, out_dir, meta)
    return {"status": "complete", "out_dir": str(out_dir), "prediction_files": files, "counts": counts}, EXIT_OK


# --- acceptance ------------------------------------------------------------------


def verify_run(out_dir: Path) -> tuple[bool, list[str]]:
    """Verify the committed metadata plus every official-format record.

    This is intentionally self-contained: the exported records carry the exact
    tokenized texts, so counts, order, vector lengths, ranges and hashes can be
    checked without reopening protected source inputs.
    """
    out_dir = Path(out_dir)
    reasons: list[str] = []
    meta_path = out_dir / "final_meta.json"
    if not meta_path.exists():
        return False, ["final_meta.json missing"]
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("schema") != META_SCHEMA:
        reasons.append("unexpected metadata schema")
    if meta.get("status") != "complete":
        reasons.append(f"status is {meta.get('status')!r}, not 'complete'")
    if (out_dir / "predictions.partial").exists():
        reasons.append("staging directory predictions.partial/ present")
    listed = meta.get("prediction_files") or {}
    target = out_dir / "predictions"
    actual = {path.name for path in target.glob("*")} if target.exists() else set()
    if set(listed) != actual:
        reasons.append(f"prediction files differ from metadata: listed {sorted(listed)}, present {sorted(actual)}")
    order = (meta.get("input") or {}).get("order") or []
    seen = []
    for name, info in sorted(listed.items()):
        path = target / name
        if not path.exists():
            continue
        if _sha256(path.read_bytes()) != info.get("sha256"):
            reasons.append(f"{name}: sha256 differs from metadata")
        try:
            records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            if any(not isinstance(record, dict) or set(record) != {"id", "text_a", "text_b", "labels_a", "labels_b"}
                   for record in records):
                raise InvalidFinalInput("unexpected prediction fields")
            ids = [record["id"] for record in records]
        except (ValueError, KeyError, TypeError, InvalidFinalInput):
            reasons.append(f"{name}: malformed prediction record")
            continue
        if len(ids) != info.get("records"):
            reasons.append(f"{name}: {len(ids)} records, metadata says {info.get('records')}")
        expected = [identifier for identifier in order if identifier in set(ids)]
        if ids != expected:
            reasons.append(f"{name}: record order differs from the contract order")
        language = name.removeprefix("predictions_").removesuffix(".jsonl")
        expected_language_ids = ((meta.get("input") or {}).get("language_order") or {}).get(language)
        if expected_language_ids and ids != expected_language_ids:
            reasons.append(f"{name}: ids differ from recorded language order")
        for position, record in enumerate(records, 1):
            try:
                if not all(isinstance(record[key], str) for key in ("id", "text_a", "text_b")):
                    raise InvalidFinalInput("id/text fields are not strings")
                item = InferenceInput(record["id"], language, tokenize(record["text_a"]), tokenize(record["text_b"]), "", "")
                validate_prediction(item, record["labels_a"], record["labels_b"])
            except (KeyError, TypeError, InvalidFinalInput) as error:
                reasons.append(f"{name}:{position}: invalid prediction: {error}")
        seen.extend(ids)
    if listed and sorted(seen) != sorted(order):
        reasons.append("predicted ids differ from the input order recorded in metadata")
    return not reasons, reasons


# --- entry point -----------------------------------------------------------------


def main(argv: list[str] | None = None, *, backend_factory=None, after_call=None, extra_meta: Mapping | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m uzh_rsd.final", description="Final B2 inference on an explicit, gold-blind input (no scoring).")
    parser.add_argument("--verify", type=Path, default=None, metavar="RUN_DIR",
                        help="only check an existing run: accepted iff final_meta.json is complete and the files match it")
    parser.add_argument("--contract", type=Path, help="organiser-confirmed output contract (JSON)")
    parser.add_argument("--input", type=Path, help="gold-blind input JSONL: id, language, text_a, text_b")
    parser.add_argument("--out", type=Path, help="new run directory (must not exist)")
    parser.add_argument("--timeout-s", type=float, default=300.0, help="per-request timeout; one attempt per call")
    parser.add_argument("--total-timeout-s", type=float, default=None,
                        help="optional total inference wall-clock ceiling; checked before each request")
    parser.add_argument("--method", choices=("b2", "b2-windowed-v2"), default="b2",
                        help="preserved original B2 or bounded long-input candidate")
    parser.add_argument("--model-revision", default=None, help="declared model revision, recorded as declared (not verified)")
    args = parser.parse_args(argv)

    def emit(result: dict, code: int) -> int:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return code

    if args.verify is not None:
        accepted, reasons = verify_run(args.verify)
        return emit({"status": "accepted" if accepted else "rejected", "run_dir": str(args.verify), "reasons": reasons},
                    EXIT_OK if accepted else EXIT_INCOMPLETE)
    if not (args.contract and args.input and args.out):
        parser.error("--contract, --input and --out are required (or use --verify RUN_DIR)")

    # 1. Configuration only: contract, endpoint variables, output path. No input read, no backend.
    try:
        contract_bytes = args.contract.read_bytes()
        contract = load_contract(args.contract)
        missing = [name for name in ENDPOINT_ENV if not os.environ.get(name)]
        if missing and backend_factory is None:
            raise FinalBlocked(f"missing environment variables: {missing}")
        if args.timeout_s <= 0:
            raise FinalBlocked("--timeout-s must be positive")
        if args.total_timeout_s is not None and args.total_timeout_s <= 0:
            raise FinalBlocked("--total-timeout-s must be positive")
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
    described = backend.describe()
    if described.get("backend") == "transformers" and described.get("revision"):
        model = {"name": described.get("model"), "revision": described["revision"],
                 "note": "Weights loaded locally from the Hugging Face Hub at this exact revision."}
    else:
        model = {"name": os.environ.get("LLM_NAME") or described.get("model"),
                 "declared_revision": args.model_revision,
                 "note": "A model name does not pin weights; the provider-side revision is unknown unless the provider states it."}
    run_id = out_dir.name
    invocation = "python -m uzh_rsd.final " + " ".join(argv if argv is not None else sys.argv[1:])
    try:
        result, code = run_final(backend, contract, contract_bytes, items, input_bytes, out_dir, run_id=run_id, invocation=invocation,
                                 model=model, method=args.method, total_timeout_s=args.total_timeout_s,
                                 after_call=after_call, extra_meta=extra_meta)
    except KeyboardInterrupt:
        return emit({"status": "interrupted", "out_dir": str(out_dir), "note": "final_meta.json marked incomplete"}, EXIT_INTERRUPTED)
    return emit(result, code)


if __name__ == "__main__":
    sys.exit(main())
