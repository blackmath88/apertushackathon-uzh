"""Frozen, dev-only B0 paper-baseline preparation and resumable runner.

The committed manifest contains hashes and lengths, never source text or labels.
Preparation writes two ignored private artifact sets: inference JSONL without any
label field, and scoring JSONL.  The generation runner can only open the former.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable, Iterable, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

from .backends import Generation
from .data_adapter import DATASET_REPO, DATASET_REVISION, LANGUAGES, InferenceInput, load_split
from .evaluation import OFFICIAL_COMMIT, OFFICIAL_FILES, official_excluded_ids
from .prompts import OFFICIAL_PROMPTS, load_b0_template, prompt_sha256, render_b0
from .splits import assert_development_split
from .tokens import tokenize

SCHEMA = "uzh-rsd.full-dev-b0-manifest/v1"
LEDGER_SCHEMA = "uzh-rsd.full-dev-b0-ledger/v1"
OUTPUT_TOKENS = 4096
CONTEXT_TOKENS = 8192
REQUEST_TIMEOUT_SECONDS = 600
TOTAL_WALL_SECONDS = 115_200
EXPECTED_ENDPOINT = "http://127.0.0.1:11436"
EXPECTED_MODEL_ALIAS = "Apertus-v1.5-8B-Q8_0"
RUN_ORDER = "language order de,fr,it; original row order within language"
PRIVATE_FIELDS = frozenset({"labels", "labels_a", "labels_b", "gold", "gold_sha256"})


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value: Mapping) -> str:
    return _sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


def _write_jsonl(path: Path, rows: Iterable[Mapping]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = b"".join((json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode() for row in rows)
    path.write_bytes(data)
    return _sha(data)


def build_freeze(
    *,
    split: str,
    source_data_dir: Path,
    official_dir: Path,
    private_dir: Path,
) -> dict:
    """Build the complete manifest and private stage-separated inputs.

    The split guard is deliberately the first operation, before path coercion or
    filesystem access.  This function never downloads anything.
    """
    split = assert_development_split(split)
    if split != "dev":
        raise ValueError("the full baseline is frozen for dev only")
    records = {language: load_split(split, language, source_data_dir) for language in LANGUAGES}
    excluded_ids, exclusion_sha = official_excluded_ids(official_dir)
    excluded_set = set(excluded_ids)
    if len(excluded_ids) != len(excluded_set):
        raise ValueError("official exclusion list contains duplicates")

    entries: list[dict] = []
    exclusions: list[dict] = []
    inference_hashes: dict[str, str] = {}
    scoring_hashes: dict[str, str] = {}
    present_ids: set[str] = set()
    for language in LANGUAGES:
        inference_rows, scoring_rows = [], []
        for order, (item, gold) in enumerate(records[language]):
            present_ids.add(item.id)
            common = {"id": item.id, "pair": item.pair, "language": language, "original_order": order}
            if item.id in excluded_set:
                exclusions.append({**common, "reason": "pinned official list_to_drop.txt"})
                continue
            input_row = {
                **common,
                "text_a": item.text_a.text,
                "text_b": item.text_b.text,
                "page_en": item.page_en,
                "page_other": item.page_other,
            }
            scoring_row = {**common, "labels_a": list(gold.labels_a), "labels_b": list(gold.labels_b)}
            inference_rows.append(input_row)
            scoring_rows.append(scoring_row)
            entries.append({
                **common,
                "token_count_a": len(item.text_a),
                "token_count_b": len(item.text_b),
                "text_a_sha256": item.text_a.sha256,
                "text_b_sha256": item.text_b.sha256,
                "gold_sha256": canonical_digest({"labels_a": scoring_row["labels_a"], "labels_b": scoring_row["labels_b"]}),
            })
        inference_hashes[language] = _write_jsonl(private_dir / "inference" / f"dev_{language}.jsonl", inference_rows)
        scoring_hashes[language] = _write_jsonl(private_dir / "scoring" / f"dev_{language}.jsonl", scoring_rows)

    source_files = {}
    from .data_adapter import _SPLIT_FILES, git_blob_sha1, local_path  # package-private pins are the contract
    for language in LANGUAGES:
        path = local_path("dev", language, source_data_dir)
        data = path.read_bytes()
        pin = _SPLIT_FILES["dev"][language]
        source_files[language] = {
            "path": pin.path,
            "size": len(data),
            "git_blob_sha1": git_blob_sha1(data),
            "sha256": _sha(data),
        }

    body = {
        "schema": SCHEMA,
        "split": "dev",
        "order": RUN_ORDER,
        "dataset": {"repo": DATASET_REPO, "revision": DATASET_REVISION, "files": source_files},
        "official": {
            "repo": "ZurichNLP/SwissGov-RSD",
            "commit": OFFICIAL_COMMIT,
            "files_sha256": OFFICIAL_FILES,
            "prompts_sha256": {language: digest for language, (_path, digest) in OFFICIAL_PROMPTS.items()},
            "exclusion_lines": len(excluded_ids),
            "exclusion_ids_absent_from_pinned_dev": sorted(excluded_set - present_ids),
        },
        "private_artifacts": {
            "policy": "ignored local files; source text and labels must never be committed or published",
            "inference_jsonl_sha256": inference_hashes,
            "scoring_jsonl_sha256": scoring_hashes,
        },
        "counts": {
            "source_rows": sum(len(rows) for rows in records.values()),
            "included": len(entries),
            "officially_excluded": len(exclusions),
            "by_pair": {f"en-{language}": sum(e["language"] == language for e in entries) for language in LANGUAGES},
        },
        "entries": entries,
        "exclusions": exclusions,
    }
    if body["counts"]["source_rows"] != len(entries) + len(exclusions):
        raise AssertionError("each pinned dev row must be included or excluded exactly once")
    body["manifest_sha256"] = canonical_digest(body)
    return body


def load_inference_items(manifest: Mapping, private_dir: Path, *, split: str = "dev") -> list[InferenceInput]:
    """Load only gold-free private inputs and verify them against the freeze."""
    split = assert_development_split(split)  # must precede every filesystem operation
    if split != "dev" or manifest.get("split") != "dev":
        raise ValueError("full baseline accepts dev only")
    expected = {(e["id"], e["pair"]): e for e in manifest["entries"]}
    items: list[InferenceInput] = []
    for language in LANGUAGES:
        path = Path(private_dir) / "inference" / f"dev_{language}.jsonl"
        data = path.read_bytes()
        if _sha(data) != manifest["private_artifacts"]["inference_jsonl_sha256"][language]:
            raise ValueError(f"private inference artifact hash mismatch: {language}")
        for line in data.decode().splitlines():
            row = json.loads(line)
            if PRIVATE_FIELDS.intersection(row):
                raise ValueError("gold-bearing field in generation input")
            key = (row["id"], row["pair"])
            entry = expected.get(key)
            if entry is None:
                raise ValueError(f"unfrozen input {key}")
            a, b = tokenize(row["text_a"]), tokenize(row["text_b"])
            if a.sha256 != entry["text_a_sha256"] or b.sha256 != entry["text_b_sha256"]:
                raise ValueError(f"text hash mismatch: {row['id']}")
            items.append(InferenceInput(row["id"], language, a, b, row["page_en"], row["page_other"]))
    if [(x.id, x.pair) for x in items] != [(e["id"], e["pair"]) for e in manifest["entries"]]:
        raise ValueError("private input identity/order differs from manifest")
    return items


def request_plan(items: Iterable[InferenceInput], prompt_dir: Path, manifest_sha256: str, config_sha256: str) -> list[dict]:
    plan = []
    for sequence, item in enumerate(items):
        prompt = render_b0(load_b0_template(item.language, prompt_dir), item)
        plan.append({
            "sequence": sequence,
            "id": item.id,
            "pair": item.pair,
            "prompt_sha256": prompt_sha256(prompt),
            "manifest_sha256": manifest_sha256,
            "config_sha256": config_sha256,
            "max_new_tokens": OUTPUT_TOKENS,
        })
    return plan


def context_preflight(plan: Iterable[Mapping], token_counter: Callable[[str], int], prompts: Mapping[str, str]) -> dict:
    """Fail closed rather than ask llama.cpp to truncate an overlong prompt."""
    checked, overflow = 0, []
    for row in plan:
        count = token_counter(prompts[row["prompt_sha256"]])
        checked += 1
        if count + OUTPUT_TOKENS > CONTEXT_TOKENS:
            overflow.append({"id": row["id"], "prompt_tokens": count, "required": count + OUTPUT_TOKENS})
    return {"checked": checked, "context_tokens": CONTEXT_TOKENS, "output_tokens": OUTPUT_TOKENS, "overflow": overflow, "ok": not overflow}


def validate_backend_contract(description: Mapping) -> None:
    """Reject runtime drift before a prompt can be sent."""
    expected = {
        "backend": "openai-compatible",
        "endpoint": EXPECTED_ENDPOINT,
        "model": EXPECTED_MODEL_ALIAS,
        "timeout_s": float(REQUEST_TIMEOUT_SECONDS),
        "max_attempts": 1,
    }
    drift = {key: (description.get(key), value) for key, value in expected.items() if description.get(key) != value}
    if drift:
        raise ValueError(f"backend differs from frozen contract: {drift}")


def _append_fsync(path: Path, row: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def ledger_state(path: Path) -> dict:
    intents, terminal = {}, {}
    if not path.exists():
        return {"intents": intents, "terminal": terminal, "unresolved": []}
    for line in path.read_text().splitlines():
        row = json.loads(line)
        if row.get("schema") != LEDGER_SCHEMA:
            raise ValueError("unknown ledger schema")
        sequence = row["sequence"]
        if row["event"] == "intent":
            if sequence in intents:
                raise ValueError("duplicate request intent")
            intents[sequence] = row
        elif row["event"] == "result":
            if sequence not in intents or sequence in terminal:
                raise ValueError("result without one unique intent")
            generation = row.get("generation")
            if not isinstance(generation, dict):
                raise ValueError("result has no generation record")
            text = generation.get("text")
            if text is not None and row.get("response_sha256") != _sha(text.encode()):
                raise ValueError("raw response integrity failure")
            terminal[sequence] = row
        else:
            raise ValueError("unknown ledger event")
    return {"intents": intents, "terminal": terminal, "unresolved": sorted(set(intents) - set(terminal))}


def reconcile_unresolved_failure(run_dir: Path, sequence: int, *, error: str) -> None:
    """Terminate one interrupted intent without ever resending it.

    This recovery operation is deliberately narrower than ``run_resumable``:
    it accepts only an already persisted, uniquely unresolved intent and writes
    one auditable no-response result under the runner lock.
    """
    ledger = Path(run_dir) / "ledger.jsonl"
    with exclusive_runner(Path(run_dir) / "runner.lock"):
        state = ledger_state(ledger)
        if state["unresolved"] != [sequence]:
            raise ValueError(f"expected sole unresolved intent {sequence}, got {state['unresolved']}")
        intent = state["intents"][sequence]
        result = {
            "schema": LEDGER_SCHEMA,
            "event": "result",
            "sequence": sequence,
            "id": intent["id"],
            "status": "transport_or_runtime_failure",
            "generation": asdict(Generation(None, error, token_count_source="unavailable")),
        }
        _append_fsync(ledger, result)


@contextmanager
def exclusive_runner(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise RuntimeError("another baseline runner may be active; establish settlement before removing the lock") from error
    try:
        os.write(fd, f"pid={os.getpid()}\n".encode())
        os.fsync(fd)
        yield
    finally:
        os.close(fd)
        lock_path.unlink()


def run_resumable(
    backend,
    plan: list[Mapping],
    prompts: Mapping[str, str],
    run_dir: Path,
    *,
    prompt_tokens: Mapping[int, int] | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> dict:
    """Run never-started requests once, sequentially; never resend intents."""
    ledger = Path(run_dir) / "ledger.jsonl"
    deadline = clock() + TOTAL_WALL_SECONDS
    intended = attempted = returned = failed = context_overflow = 0
    with exclusive_runner(Path(run_dir) / "runner.lock"):
        existing = ledger_state(ledger)
        for row in plan:
            sequence = row["sequence"]
            if sequence in existing["intents"]:  # terminal or unresolved: never resend
                continue
            if clock() >= deadline:
                break
            intent = {"schema": LEDGER_SCHEMA, "event": "intent", **row}
            _append_fsync(ledger, intent)
            intended += 1
            exact_prompt_tokens = None if prompt_tokens is None else prompt_tokens.get(sequence)
            if exact_prompt_tokens is not None and exact_prompt_tokens + OUTPUT_TOKENS > CONTEXT_TOKENS:
                generation = Generation(
                    None,
                    "context_overflow",
                    prompt_tokens=exact_prompt_tokens,
                    completion_tokens=0,
                    token_count_source="endpoint tokenizer",
                )
                status = "context_overflow"
                context_overflow += 1
            else:
                attempted += 1
                generation = backend.generate(prompts[row["prompt_sha256"]], OUTPUT_TOKENS)
                status = "returned" if generation.text is not None else "transport_or_runtime_failure"
            result = {"schema": LEDGER_SCHEMA, "event": "result", "sequence": sequence, "id": row["id"], "status": status,
                      "generation": asdict(generation)}
            if generation.text is not None:
                result["response_sha256"] = _sha(generation.text.encode())
                returned += 1
            elif status == "transport_or_runtime_failure":
                failed += 1
            _append_fsync(ledger, result)
            if status == "transport_or_runtime_failure":  # checkpoint and pause; no self-retry
                break
    final = ledger_state(ledger)
    return {"planned": len(plan), "intended_this_invocation": intended,
            "attempted_this_invocation": attempted, "returned_this_invocation": returned,
            "failed_this_invocation": failed, "context_overflow_this_invocation": context_overflow,
            "resolved_total": len(final["terminal"]), "unresolved": final["unresolved"],
            "unstarted": len(plan) - len(final["intents"])}
