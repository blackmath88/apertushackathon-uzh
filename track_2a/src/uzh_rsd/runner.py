"""Run B0 and B2 on identical manifest documents and keep every raw response.

The runner sees only :class:`InferenceInput` objects (no labels). It writes one
JSON line per (document, method) call to ``raw.jsonl`` immediately after the
call, so a timeout or crash leaves every completed call on disk. Calls that are
not attempted before the deadline are written as ``skipped_deadline``.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import time
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

from .data_adapter import DEFAULT_DATA_DIR, LANGUAGES, GoldLabels, InferenceInput, load_split
from .prompts import B0_PROMPT_VERSION, B2_PROMPT_VERSION, DEFAULT_PROMPT_DIR, load_b0_template, prompt_sha256, render_b0, render_b2
from .splits import assert_development_split

RAW_SCHEMA = "uzh-rsd.raw-call/v1"
METHODS = ("b0", "b2")
MAX_NEW_TOKENS = {"b0": 4096, "b2": 1024}  # b0: upstream predict_llama.py
PROMPT_VERSIONS = {"b0": B0_PROMPT_VERSION, "b2": B2_PROMPT_VERSION}


def load_manifest(path: Path) -> dict:
    manifest = json.loads(Path(path).read_text())
    assert_development_split(manifest.get("split"))
    return manifest


def manifest_records(manifest: Mapping, data_dir: Path = DEFAULT_DATA_DIR, limit: int | None = None) -> list[tuple[InferenceInput, GoldLabels]]:
    """Manifest documents in manifest order; text hashes are verified."""
    split = assert_development_split(manifest["split"])
    by_language: dict[str, dict[str, tuple[InferenceInput, GoldLabels]]] = {}
    entries = list(manifest["entries"])[: limit if limit is not None else None]
    for language in sorted({entry["pair"].split("-")[1] for entry in entries}):
        if language not in LANGUAGES:
            raise ValueError(f"unexpected language {language}")
        by_language[language] = {inference.id: (inference, gold) for inference, gold in load_split(split, language, data_dir)}
    records = []
    for entry in entries:
        inference, gold = by_language[entry["pair"].split("-")[1]][entry["id"]]
        if inference.text_a.sha256 != entry["text_a_sha256"] or inference.text_b.sha256 != entry["text_b_sha256"]:
            raise ValueError(f"{entry['id']}: text differs from manifest")
        records.append((inference, gold))
    return records


def interleave_languages(items: list[InferenceInput]) -> list[InferenceInput]:
    """Round-robin over languages (stable within a language), so a run cut
    short by its deadline still covers EN-DE, EN-FR and EN-IT."""
    queues = {language: [item for item in items if item.language == language] for language in LANGUAGES}
    ordered = []
    while any(queues.values()):
        for language in LANGUAGES:
            if queues[language]:
                ordered.append(queues[language].pop(0))
    return ordered


def build_prompt(method: str, item: InferenceInput, prompt_dir: Path = DEFAULT_PROMPT_DIR) -> str:
    if method == "b0":
        return render_b0(load_b0_template(item.language, prompt_dir), item)
    if method == "b2":
        return render_b2(item)
    raise ValueError(f"unknown method {method!r}")


def run_inference(
    backend,
    items: Iterable[InferenceInput],
    methods: Iterable[str],
    out_path: Path,
    *,
    run_id: str,
    prompt_dir: Path = DEFAULT_PROMPT_DIR,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    after_call: Callable[[dict], None] | None = None,
) -> dict:
    methods = tuple(methods)
    for method in methods:
        if method not in METHODS:
            raise ValueError(f"unknown method {method!r}")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    counts = {"attempted": 0, "call_failed": 0, "skipped_deadline": 0}
    with out_path.open("a", encoding="utf-8") as handle:
        for item in items:
            for method in methods:
                prompt = build_prompt(method, item, prompt_dir)
                record = {
                    "schema": RAW_SCHEMA,
                    "run_id": run_id,
                    "method": method,
                    "prompt_version": PROMPT_VERSIONS[method],
                    "id": item.id,
                    "pair": item.pair,
                    "tokens_a": len(item.text_a),
                    "tokens_b": len(item.text_b),
                    "prompt_sha256": prompt_sha256(prompt),
                    "prompt": prompt,
                    "max_new_tokens": MAX_NEW_TOKENS[method],
                    "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                }
                if deadline is not None and clock() >= deadline:
                    record.update(status="skipped_deadline", generation=None)
                    counts["skipped_deadline"] += 1
                else:
                    generation = backend.generate(prompt, MAX_NEW_TOKENS[method])
                    counts["attempted"] += 1
                    status = "returned" if generation.text is not None else "call_failed"
                    counts["call_failed"] += status == "call_failed"
                    record.update(status=status, generation=generation.as_dict())
                    if generation.text is not None:
                        record["response_sha256"] = hashlib.sha256(generation.text.encode("utf-8")).hexdigest()
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
                if after_call is not None:
                    after_call(record)
    return counts


def read_raw(path: Path) -> list[dict]:
    records = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    for record in records:
        if record.get("schema") != RAW_SCHEMA:
            raise ValueError(f"unexpected raw record schema {record.get('schema')!r}")
    return records
