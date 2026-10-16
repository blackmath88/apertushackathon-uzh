"""Bounded, post-submission C0/C1 comparison on the SwissGov-RSD dev split.

The module deliberately separates the three phases which may see different
data: ``freeze`` reads inference-only rows, ``run`` sends prompts without
labels, and ``score`` opens gold only after a stage ledger is complete.
Source text, prompts, raw responses, cache entries and gold remain below an
ignored private directory.  The public package contains identities, hashes,
numeric predictions and text-free summaries only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import random
import statistics
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .backends import OpenAICompatibleBackend
from .data_adapter import GoldLabels, InferenceInput, LANGUAGES
from .evaluation import evaluate_language, macro_average
from .methods import MethodOutput, parse_b2
from .prompts import B2_PROMPT_VERSION, B2_TEMPLATE, prompt_sha256, render_b2
from .tokens import tokenize

SCHEMA = "uzh-rsd.nebu-staged-comparison/v1"
SUBSET_RULE = "nebu-subset-v1"
P1_BLOCK = """Additional comparison guidance:
Different words can convey the same information. Compare the actor, action, affected object, permission or obligation, negation, conditions, exceptions, quantities and time expressed by each version. These are a checklist, not an exhaustive list of possible differences.
Do not infer facts that neither passage states. Use surrounding sentences to understand what a condition or exception governs. Report only differences supported by the two supplied texts.
Distinguish a changed assertion from a faithful paraphrase. An extra qualification can be a difference even when most words correspond. Select the smallest exact excerpts that carry the change; retain necessary negation and qualifiers. Keep the existing severity scale and JSON contract unchanged.
"""
INSERTION_MARKER = "Version A (English):"
FALLBACK = 0.0
REQUEST_LIMIT = 120
REQUEST_TIMEOUT_S = 600.0
INFERENCE_LIMIT_S = 3600.0
BOOTSTRAP_SEED = 0
BOOTSTRAP_REPLICATES = 2000
EXPECTED_MODEL_SHA256 = "dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d"
EXPECTED_SERVER_SHA256 = "d0538ae0a50a97ede6c4fece9054ed8d3b891a82e230a1defe810249ee7b93f1"
EXPECTED_LLAMA_CPP_COMMIT = "7ab4ee7baad2d920464cbacfad4f4b07cf111fd2"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def _private_inference(private_dir: Path, manifest: Mapping) -> tuple[list[InferenceInput], dict[str, dict]]:
    expected = {entry["id"]: entry for entry in manifest["entries"]}
    rows: list[dict] = []
    for language in LANGUAGES:
        path = private_dir / "inference" / f"dev_{language}.jsonl"
        if file_sha256(path) != manifest["private_artifacts"]["inference_jsonl_sha256"][language]:
            raise ValueError(f"private inference artifact hash mismatch: {language}")
        rows.extend(_load_jsonl(path))
    if [row["id"] for row in rows] != [entry["id"] for entry in manifest["entries"]]:
        raise ValueError("private inference identity/order differs from baseline manifest")
    items, raw = [], {}
    for row in rows:
        entry = expected[row["id"]]
        a, b = tokenize(row["text_a"]), tokenize(row["text_b"])
        if a.sha256 != entry["text_a_sha256"] or b.sha256 != entry["text_b_sha256"]:
            raise ValueError(f"input hash mismatch: {row['id']}")
        item = InferenceInput(row["id"], row["language"], a, b, row["page_en"], row["page_other"])
        items.append(item)
        raw[item.id] = row
    return items, raw


def render_candidate(candidate_id: str, item: InferenceInput) -> str:
    base = render_b2(item)
    if candidate_id == "C0":
        return base
    if candidate_id != "C1":
        raise ValueError(f"unknown candidate {candidate_id}")
    if base.count(INSERTION_MARKER) != 1:
        raise ValueError("B2 insertion marker must occur exactly once")
    return base.replace(INSERTION_MARKER, P1_BLOCK + "\n" + INSERTION_MARKER)


def _strata(groups: list[dict]) -> dict[str, list[dict]]:
    groups = sorted(groups, key=lambda group: (group["max_combined_official_tokens"], group["group_key"]))
    base, remainder = divmod(len(groups), 3)
    sizes = [base + (index < remainder) for index in range(3)]
    result, offset = {}, 0
    for name, size in zip(("short", "medium", "long"), sizes):
        result[name] = groups[offset:offset + size]
        offset += size
    return result


def freeze(*, manifest_path: Path, private_dir: Path, package_dir: Path, base_commit: str) -> dict:
    if package_dir.exists():
        raise FileExistsError(package_dir)
    manifest = read_json(manifest_path)
    items, raw = _private_inference(private_dir, manifest)
    by_source: dict[str, list[InferenceInput]] = defaultdict(list)
    source_values: dict[str, str] = {}
    for item in items:
        normalized = item.page_en.strip()
        key = hashlib.sha256(normalized.encode()).hexdigest()
        by_source[key].append(item)
        source_values[key] = normalized
    entries = {entry["id"]: entry for entry in manifest["entries"]}
    groups = []
    incomplete = []
    for key, members in by_source.items():
        languages = sorted(member.language for member in members)
        group = {
            "group_key": key,
            "source_identity_kind": "sha256(exact stripped upstream page_en)",
            "languages": languages,
            "ids": [member.id for member in sorted(members, key=lambda item: LANGUAGES.index(item.language))],
            "max_combined_official_tokens": max(
                entries[member.id]["token_count_a"] + entries[member.id]["token_count_b"] for member in members
            ),
        }
        if languages == list(LANGUAGES) and len(members) == 3:
            groups.append(group)
        else:
            incomplete.append(group)
    strata = _strata(groups)
    exploration, validation_pool, validation_execution = [], [], []
    for stratum, members in strata.items():
        ordered = sorted(members, key=lambda group: hashlib.sha256(f"{SUBSET_RULE}|{group['group_key']}".encode()).hexdigest())
        for group in ordered:
            group["stratum"] = stratum
        exploration.extend(ordered[:4])
        validation_pool.extend(ordered[4:10])
        validation_execution.extend(ordered[4:8])
    if len(exploration) != 12 or len(validation_execution) != 12:
        raise ValueError("insufficient complete source groups for frozen 12/12 schedule")

    def public_rows(selected: Sequence[dict]) -> list[dict]:
        rows = []
        for group in selected:
            for record_id in group["ids"]:
                entry = entries[record_id]
                rows.append({
                    "group_key": group["group_key"], "stratum": group["stratum"],
                    "id": record_id, "language": entry["language"], "pair": entry["pair"],
                    "original_order": entry["original_order"],
                    "text_a_sha256": entry["text_a_sha256"], "text_b_sha256": entry["text_b_sha256"],
                    "token_count_a": entry["token_count_a"], "token_count_b": entry["token_count_b"],
                    "exposure": "dev source family; potentially exposed to B0-B8; reserved validation is not pristine",
                })
        return rows

    subset = {
        "schema": SCHEMA, "kind": "source-grouped-subsets", "rule": SUBSET_RULE,
        "base_commit": base_commit, "baseline_manifest_sha256": manifest["manifest_sha256"],
        "normalization": "page_en.strip(); exact UTF-8 bytes; SHA-256 published, URL kept private",
        "stratum_remainder": "allocate one extra group to short, then medium, then long",
        "eligible_complete_groups": len(groups), "incomplete_groups": incomplete,
        "stratum_counts": {name: len(value) for name, value in strata.items()},
        "exploration": public_rows(exploration), "validation_pool": public_rows(validation_pool),
        "validation_execution": public_rows(validation_execution),
    }
    subset["subset_digest"] = digest(subset)
    candidates = {
        "schema": SCHEMA, "kind": "candidate-freeze", "max_new_tokens": 1024,
        "decoding": {"temperature": 0.0, "attempts": 1},
        "parser": "uzh_rsd.methods.parse_b2", "projection": "max severity; uncovered tokens are predicted no-difference",
        "segmentation": "none; full document", "alignment": "exact then case/quote-normalized excerpt matching",
        "failure_policy": "zero-difference fallback only in explicitly labelled all-subset score",
        "candidates": [
            {"id": "C0", "name": "unchanged B2", "prompt_version": B2_PROMPT_VERSION,
             "template_sha256": hashlib.sha256(B2_TEMPLATE.encode()).hexdigest(), "added_block_sha256": None},
            {"id": "C1", "name": "B2 plus P1 semantic commitments", "prompt_version": B2_PROMPT_VERSION + "+p1-semantic-commitments-v1",
             "template_sha256": hashlib.sha256(B2_TEMPLATE.encode()).hexdigest(),
             "added_block_sha256": hashlib.sha256(P1_BLOCK.encode()).hexdigest(), "added_block": P1_BLOCK},
        ],
        "omitted": {"C2": "no existing safely supported chunk/aligned-span merge implementation"},
    }
    candidates["candidate_digest"] = digest(candidates)
    schedule = {
        "schema": SCHEMA, "kind": "request-schedule", "request_ceiling": REQUEST_LIMIT,
        "per_request_timeout_s": REQUEST_TIMEOUT_S, "total_inference_limit_s": INFERENCE_LIMIT_S,
        "exploration": {"candidates": ["C0", "C1"], "pairs": 36, "requests": 72},
        "validation": {"candidate": "winner frozen after exploration", "pairs": 36, "requests": 36},
        "reserved_unused_requests": 12, "global_concurrency": 1, "automatic_retries": 0,
    }
    schedule["schedule_digest"] = digest(schedule)
    package_dir.mkdir(parents=True)
    write_json(package_dir / "subset-manifest.json", subset)
    write_json(package_dir / "candidates.json", candidates)
    write_json(package_dir / "schedule.json", schedule)
    ledger = {"schema": SCHEMA, "base_commit": base_commit, "stage": "stage0-frozen",
              "subset_digest": subset["subset_digest"], "candidate_digest": candidates["candidate_digest"],
              "schedule_digest": schedule["schedule_digest"], "status": "post-submission research; no inference yet"}
    write_json(package_dir / "TASK_LEDGER.json", ledger)
    return ledger


def _load_items_for_stage(package_dir: Path, private_dir: Path, baseline_manifest: Path, stage: str) -> list[InferenceInput]:
    manifest = read_json(baseline_manifest)
    items, _ = _private_inference(private_dir, manifest)
    wanted_rows = read_json(package_dir / "subset-manifest.json")["exploration" if stage == "exploration" else "validation_execution"]
    wanted = [row["id"] for row in wanted_rows]
    lookup = {item.id: item for item in items}
    if set(wanted) - set(lookup):
        raise ValueError("frozen subset ids missing from private inference data")
    return [lookup[record_id] for record_id in wanted]


def runtime_identity(model_path: Path, server_binary: Path, base_url: str) -> dict:
    with urllib.request.urlopen(base_url.rstrip("/") + "/props", timeout=10) as response:
        props = json.loads(response.read())
    model_hash = file_sha256(model_path)
    server_hash = file_sha256(server_binary)
    if model_hash != EXPECTED_MODEL_SHA256:
        raise ValueError(f"unexpected installed model hash: {model_hash}")
    if server_hash != EXPECTED_SERVER_SHA256:
        raise ValueError(f"unexpected installed llama.cpp binary hash: {server_hash}")
    chat_template = props.get("chat_template", "")
    return {
        "model_sha256": model_hash, "model_size": model_path.stat().st_size,
        "server_binary_sha256": server_hash, "llama_cpp_commit": EXPECTED_LLAMA_CPP_COMMIT,
        "endpoint_model_alias": props.get("model_alias"), "context_tokens": props.get("n_ctx"),
        "chat_template_sha256": hashlib.sha256(str(chat_template).encode()).hexdigest(),
        "endpoint_props_sha256": digest(props),
    }


def _cache_key(item: InferenceInput, candidate: dict, prompt: str, runtime: dict) -> str:
    return digest({"schema": SCHEMA, "id": item.id, "input": [item.text_a.sha256, item.text_b.sha256],
                   "official_tokens": [list(item.text_a.tokens), list(item.text_b.tokens)], "runtime": runtime,
                   "prompt_sha256": prompt_sha256(prompt), "candidate": candidate,
                   "parser_projection": "parse_b2|max-severity|uncovered-zero", "max_new_tokens": 1024,
                   "decoding": {"temperature": 0.0}})


def _ledger_state(path: Path) -> tuple[dict[str, dict], set[str]]:
    results, intents = {}, set()
    if not path.exists():
        return results, intents
    for row in _load_jsonl(path):
        key = row["task_key"]
        if row["event"] == "intent":
            if key in intents:
                raise ValueError(f"duplicate intent {key}")
            intents.add(key)
        elif row["event"] == "result":
            if key not in intents or key in results:
                raise ValueError(f"invalid terminal result {key}")
            results[key] = row
    return results, intents


def run_stage(*, stage: str, package_dir: Path, private_dir: Path, baseline_manifest: Path,
              run_dir: Path, base_url: str, model: str, api_key: str,
              model_path: Path, server_binary: Path, candidate_ids: Sequence[str]) -> dict:
    if stage not in {"exploration", "validation"}:
        raise ValueError(stage)
    run_dir.mkdir(parents=True, exist_ok=True)
    ledger_path, cache_dir = run_dir / "ledger.jsonl", private_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    results, intents = _ledger_state(ledger_path)
    unsettled = intents - set(results)
    if unsettled:
        raise RuntimeError(f"unsettled prior intents; refusing resume: {sorted(unsettled)[:3]}")
    if any(row["status"] == "call_failed" for row in results.values()):
        raise RuntimeError("prior transport/runtime failure requires diagnosis; refusing resume")
    items = _load_items_for_stage(package_dir, private_dir, baseline_manifest, stage)
    candidates = {row["id"]: row for row in read_json(package_dir / "candidates.json")["candidates"]}
    if any(candidate_id not in candidates for candidate_id in candidate_ids):
        raise ValueError("unfrozen candidate")
    runtime = runtime_identity(model_path, server_binary, base_url)
    write_json(run_dir / "runtime-identity.json", runtime)
    backend = OpenAICompatibleBackend(base_url, model, api_key, timeout_s=REQUEST_TIMEOUT_S)
    started = time.monotonic()
    attempted = cache_hits = 0
    with ledger_path.open("a", encoding="utf-8") as ledger:
        for item in items:
            for candidate_id in candidate_ids:
                task_key = f"{candidate_id}:{item.id}"
                if task_key in results:
                    continue
                if time.monotonic() - started >= INFERENCE_LIMIT_S:
                    raise TimeoutError("total inference-stage limit reached before next request")
                prompt = render_candidate(candidate_id, item)
                cache_key = _cache_key(item, candidates[candidate_id], prompt, runtime)
                intent = {"schema": SCHEMA, "event": "intent", "task_key": task_key, "stage": stage,
                          "candidate": candidate_id, "id": item.id, "pair": item.pair,
                          "prompt_sha256": prompt_sha256(prompt), "cache_key": cache_key,
                          "max_new_tokens": 1024, "created_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
                ledger.write(json.dumps(intent, separators=(",", ":")) + "\n"); ledger.flush()
                cache_path = cache_dir / f"{cache_key}.json"
                if cache_path.exists():
                    generation = read_json(cache_path)
                    status, cache_hit = "returned", True
                    cache_hits += 1
                else:
                    generated = backend.generate(prompt, 1024)
                    generation = generated.as_dict()
                    attempted += 1
                    status, cache_hit = ("returned" if generated.text is not None else "call_failed"), False
                    if generated.text is not None:
                        write_json(cache_path, generation)
                result = {"schema": SCHEMA, "event": "result", "task_key": task_key, "stage": stage,
                          "candidate": candidate_id, "id": item.id, "pair": item.pair, "status": status,
                          "cache_hit": cache_hit, "cache_key": cache_key, "generation": generation,
                          "response_sha256": hashlib.sha256((generation.get("text") or "").encode()).hexdigest(),
                          "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
                ledger.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n"); ledger.flush()
                if status == "call_failed":
                    write_json(run_dir / "run-summary.json", {"status": "paused_on_transport_failure", "task_key": task_key})
                    return {"status": "paused_on_transport_failure", "attempted": attempted, "cache_hits": cache_hits}
    summary = {"schema": SCHEMA, "stage": stage, "status": "settled", "intended": len(items) * len(candidate_ids),
               "endpoint_attempted": attempted, "cache_hits": cache_hits, "wall_s": round(time.monotonic() - started, 3),
               "ledger_sha256": file_sha256(ledger_path)}
    write_json(run_dir / "run-summary.json", summary)
    return summary


def _load_gold(private_dir: Path, manifest: Mapping) -> dict[str, GoldLabels]:
    rows, expected = {}, {entry["id"]: entry for entry in manifest["entries"]}
    for language in LANGUAGES:
        path = private_dir / "scoring" / f"dev_{language}.jsonl"
        if file_sha256(path) != manifest["private_artifacts"]["scoring_jsonl_sha256"][language]:
            raise ValueError(f"private scoring artifact hash mismatch: {language}")
        for row in _load_jsonl(path):
            if row["id"] in expected:
                rows[row["id"]] = GoldLabels(row["id"], tuple(row["labels_a"]), tuple(row["labels_b"]))
    return rows


def _score_rows(rows: Sequence[tuple[str, GoldLabels, Sequence[float], Sequence[float]]]) -> dict:
    by_language = {language: [] for language in LANGUAGES}
    for language, gold, a, b in rows:
        by_language[language].append((gold, a, b))
    per = {language: evaluate_language(language, by_language[language]) for language in LANGUAGES}
    macro, reason = macro_average(per)
    return {"macro": macro, "undefined_reason": reason,
            "per_language": {language: {"documents": result.documents, "positions": result.positions,
                                         "spearman": result.spearman, "undefined_reason": result.undefined_reason}
                             for language, result in per.items()}}


def _candidate_prediction(item: InferenceInput, result: dict) -> tuple[MethodOutput, dict]:
    generation = result["generation"]
    parsed = parse_b2(item, generation.get("text") if result["status"] == "returned" else None)
    d = parsed.diagnostics
    partial = parsed.status == "ok" and bool(d.get("items", 0) != d.get("projected", 0) or
        d.get("invalid_item", 0) or d.get("invalid_severity", 0) or d.get("unknown_kind", 0) or
        d.get("spans_not_found", 0) or d.get("spans_too_long", 0))
    strict = parsed.status == "ok" and not partial
    return parsed, {"strict": strict, "partial": partial}


def _bootstrap_delta(group_rows: dict[str, dict[str, list]], candidate: str, baseline: str) -> dict:
    keys, rng, deltas, undefined = sorted(group_rows), random.Random(BOOTSTRAP_SEED), [], 0
    for _ in range(BOOTSTRAP_REPLICATES):
        selected = [rng.choice(keys) for _ in keys]
        c_rows, b_rows = [], []
        for key in selected:
            c_rows.extend(group_rows[key][candidate]); b_rows.extend(group_rows[key][baseline])
        c, b = _score_rows(c_rows)["macro"], _score_rows(b_rows)["macro"]
        if c is None or b is None:
            undefined += 1
        else:
            deltas.append(c - b)
    deltas.sort()
    if not deltas:
        return {"seed": BOOTSTRAP_SEED, "replicates": BOOTSTRAP_REPLICATES, "defined": 0, "undefined": undefined, "ci95": None}
    lo, hi = deltas[int(.025 * (len(deltas) - 1))], deltas[int(.975 * (len(deltas) - 1))]
    return {"seed": BOOTSTRAP_SEED, "replicates": BOOTSTRAP_REPLICATES, "defined": len(deltas),
            "undefined": undefined, "ci95": [lo, hi]}


def score_stage(*, stage: str, package_dir: Path, private_dir: Path, baseline_manifest: Path,
                baseline_predictions: Path, run_dir: Path, out_dir: Path, candidate_ids: Sequence[str]) -> dict:
    if out_dir.exists():
        raise FileExistsError(out_dir)
    run_summary = read_json(run_dir / "run-summary.json")
    if run_summary.get("status") != "settled":
        raise RuntimeError("stage outputs are not settled; scoring refused")
    manifest = read_json(baseline_manifest)
    gold = _load_gold(private_dir, manifest)
    items = _load_items_for_stage(package_dir, private_dir, baseline_manifest, stage)
    item_by_id = {item.id: item for item in items}
    results, intents = _ledger_state(run_dir / "ledger.jsonl")
    expected = {f"{candidate}:{item.id}" for item in items for candidate in candidate_ids}
    if intents != expected or set(results) != expected:
        raise RuntimeError("ledger does not exactly match frozen stage schedule")
    subset_rows = read_json(package_dir / "subset-manifest.json")["exploration" if stage == "exploration" else "validation_execution"]
    group_for = {row["id"]: row["group_key"] for row in subset_rows}
    baseline_all = {row["id"]: row for row in _load_jsonl(baseline_predictions)}
    missing = set(item_by_id) - set(baseline_all)
    if missing:
        raise ValueError(f"baseline predictions missing {sorted(missing)[:3]}")

    predictions, metrics = [], {}
    scored: dict[str, dict[str, tuple]] = {candidate: {} for candidate in candidate_ids}
    scored["B0-saved"] = {}
    for item in items:
        base = baseline_all[item.id]
        scored["B0-saved"][item.id] = (item.language, gold[item.id], base["labels_a"], base["labels_b"], base["parse_status"] == "ok")
        for candidate in candidate_ids:
            parsed, flags = _candidate_prediction(item, results[f"{candidate}:{item.id}"])
            usable = parsed.diff_a is not None
            a = parsed.diff_a if usable else [FALLBACK] * len(item.text_a)
            b = parsed.diff_b if usable else [FALLBACK] * len(item.text_b)
            scored[candidate][item.id] = (item.language, gold[item.id], a, b, usable)
            predictions.append({"id": item.id, "pair": item.pair, "candidate": candidate,
                                "parse_status": parsed.status, "strictly_valid": flags["strict"],
                                "partially_projected": flags["partial"], "fallback_document": not usable,
                                "labels_a": a, "labels_b": b})

    for name, values in scored.items():
        all_rows = [(v[0], v[1], v[2], v[3]) for v in values.values()]
        coverage = Counter()
        latencies, prompt_tokens, completion_tokens, cache_hits = [], 0, 0, 0
        if name == "B0-saved":
            coverage.update(intended=len(values), attempted=sum(baseline_all[i]["generation_status"] != "context_overflow" for i in values),
                            returned=sum(baseline_all[i]["generation_status"] == "returned" for i in values),
                            parseable=sum(baseline_all[i]["parse_status"] == "ok" for i in values),
                            strictly_valid=sum(bool(baseline_all[i]["strict_valid"]) for i in values),
                            usable=sum(v[4] for v in values.values()), context_overflow=sum(baseline_all[i]["generation_status"] == "context_overflow" for i in values),
                            malformed=sum(baseline_all[i]["parse_status"] == "unparseable" for i in values),
                            transport_failure=sum(baseline_all[i]["generation_status"] == "transport_or_runtime_failure" for i in values))
        else:
            for item in items:
                result = results[f"{name}:{item.id}"]; generation = result["generation"]
                parsed, flags = _candidate_prediction(item, result)
                coverage["intended"] += 1; coverage["attempted"] += not result["cache_hit"]
                coverage["returned"] += result["status"] == "returned"; coverage["parseable"] += parsed.status == "ok"
                coverage["strictly_valid"] += flags["strict"]; coverage["usable"] += parsed.diff_a is not None
                coverage["partially_projected"] += flags["partial"]; coverage["malformed"] += parsed.status == "unparseable"
                coverage["transport_failure"] += result["status"] == "call_failed"; coverage["unresolved"] += 0
                cache_hits += result["cache_hit"]
                if generation.get("latency_s") is not None: latencies.append(generation["latency_s"])
                prompt_tokens += generation.get("prompt_tokens") or 0; completion_tokens += generation.get("completion_tokens") or 0
        metrics[name] = {"all_subset_fallback_based": _score_rows(all_rows), "coverage": dict(coverage),
                         "cost": {"calls": coverage.get("attempted", 0), "cache_hits": cache_hits,
                                  "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
                                  "inference_s": round(sum(latencies), 3),
                                  "latency_median_s": statistics.median(latencies) if latencies else None,
                                  "latency_p95_s": sorted(latencies)[math.ceil(.95 * len(latencies)) - 1] if latencies else None}}

    baseline_usable = {record_id for record_id, value in scored["B0-saved"].items() if value[4]}
    for candidate in candidate_ids:
        shared = [record_id for record_id in item_by_id if record_id in baseline_usable and scored[candidate][record_id][4]]
        metrics[candidate]["shared_usable_with_B0"] = {
            "documents": {language: sum(item_by_id[i].language == language for i in shared) for language in LANGUAGES},
            "candidate": _score_rows([(scored[candidate][i][0], scored[candidate][i][1], scored[candidate][i][2], scored[candidate][i][3]) for i in shared]),
            "baseline": _score_rows([(scored["B0-saved"][i][0], scored["B0-saved"][i][1], scored["B0-saved"][i][2], scored["B0-saved"][i][3]) for i in shared]),
            "fallback_tokens": 0,
        }
        grouped = defaultdict(lambda: {candidate: [], "B0-saved": []})
        for record_id in item_by_id:
            for name in (candidate, "B0-saved"):
                v = scored[name][record_id]
                grouped[group_for[record_id]][name].append((v[0], v[1], v[2], v[3]))
        metrics[candidate]["delta_vs_B0_bootstrap"] = _bootstrap_delta(grouped, candidate, "B0-saved")

    selection = None
    if stage == "exploration":
        c0_coverage = metrics["C0"]["coverage"]["usable"]
        eligible = [candidate for candidate in candidate_ids if metrics[candidate]["coverage"]["usable"] >= c0_coverage]
        if eligible:
            eligible.sort(key=lambda candidate: (-(metrics[candidate]["all_subset_fallback_based"]["macro"] or -999),
                                                 metrics[candidate]["cost"]["inference_s"], candidate))
            best = eligible[0]
            if len(eligible) > 1:
                a, b = eligible[0], eligible[1]
                ma, mb = metrics[a]["all_subset_fallback_based"]["macro"], metrics[b]["all_subset_fallback_based"]["macro"]
                if ma is not None and mb is not None and abs(ma - mb) <= .01:
                    best = min((a, b), key=lambda candidate: (metrics[candidate]["cost"]["inference_s"], candidate))
            selection = {"selected": best, "rule": "coverage >= C0; highest all-subset macro; within 0.01 lower uncached inference time",
                         "frozen_before_validation": True}
    out_dir.mkdir(parents=True)
    prediction_path = out_dir / "predictions.jsonl"
    prediction_path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in predictions))
    summary = {"schema": SCHEMA, "stage": stage, "subset_digest": read_json(package_dir / "subset-manifest.json")["subset_digest"],
               "baseline_predictions_sha256": file_sha256(baseline_predictions), "metrics": metrics, "selection": selection,
               "predictions_sha256": file_sha256(prediction_path), "ledger_sha256": file_sha256(run_dir / "ledger.jsonl")}
    write_json(out_dir / "summary.json", summary)
    if selection:
        write_json(package_dir / "selected-candidate.json", {**selection, "exploration_summary_sha256": file_sha256(out_dir / "summary.json")})
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    freeze_p = sub.add_parser("freeze")
    freeze_p.add_argument("--manifest", type=Path, required=True); freeze_p.add_argument("--private-dir", type=Path, required=True)
    freeze_p.add_argument("--package", type=Path, required=True); freeze_p.add_argument("--base-commit", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--stage", choices=("exploration", "validation"), required=True); run_p.add_argument("--package", type=Path, required=True)
    run_p.add_argument("--private-dir", type=Path, required=True); run_p.add_argument("--manifest", type=Path, required=True)
    run_p.add_argument("--run-dir", type=Path, required=True); run_p.add_argument("--base-url", required=True); run_p.add_argument("--model", required=True)
    run_p.add_argument("--api-key", default="local-only"); run_p.add_argument("--model-path", type=Path, required=True)
    run_p.add_argument("--server-binary", type=Path, required=True); run_p.add_argument("--candidates", nargs="+", required=True)
    score_p = sub.add_parser("score")
    score_p.add_argument("--stage", choices=("exploration", "validation"), required=True); score_p.add_argument("--package", type=Path, required=True)
    score_p.add_argument("--private-dir", type=Path, required=True); score_p.add_argument("--manifest", type=Path, required=True)
    score_p.add_argument("--baseline-predictions", type=Path, required=True); score_p.add_argument("--run-dir", type=Path, required=True)
    score_p.add_argument("--out-dir", type=Path, required=True); score_p.add_argument("--candidates", nargs="+", required=True)
    args = parser.parse_args(argv)
    if args.command == "freeze":
        result = freeze(manifest_path=args.manifest, private_dir=args.private_dir, package_dir=args.package, base_commit=args.base_commit)
    elif args.command == "run":
        result = run_stage(stage=args.stage, package_dir=args.package, private_dir=args.private_dir, baseline_manifest=args.manifest,
                           run_dir=args.run_dir, base_url=args.base_url, model=args.model, api_key=args.api_key,
                           model_path=args.model_path, server_binary=args.server_binary, candidate_ids=args.candidates)
    else:
        result = score_stage(stage=args.stage, package_dir=args.package, private_dir=args.private_dir, baseline_manifest=args.manifest,
                             baseline_predictions=args.baseline_predictions, run_dir=args.run_dir, out_dir=args.out_dir,
                             candidate_ids=args.candidates)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
