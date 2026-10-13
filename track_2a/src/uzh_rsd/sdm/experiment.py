"""Freeze, execute and deterministically re-score the B3 SDM experiment."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Mapping, Sequence

from ..backends import OpenAICompatibleBackend
from ..data_adapter import LANGUAGES
from ..evaluation import evaluate_language, macro_average
from ..methods import parse_b2
from ..runner import manifest_records, read_raw
from .contracts import DifferenceKind, Relation
from .pipeline import (POLICY, build_tasks, classifier_prompt, project_decisions,
                       structural_response, validate_response)

TASK_MANIFEST_SCHEMA = "uzh-rsd.sdm-task-manifest/v1"
RUN_SCHEMA = "uzh-rsd.sdm-run/v1"
MODEL_SHA256 = "dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d"
LLAMA_COMMIT = "7ab4ee7"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def freeze(source_manifest: Path, output: Path) -> dict:
    source = _load(source_manifest)
    records = manifest_records(source)
    documents, all_tasks = [], []
    totals = Counter()
    for item, _gold in records:
        tasks, diagnostics = build_tasks(item)
        documents.append({"id": item.id, "pair": item.pair,
                          "text_a_sha256": item.text_a.sha256, "text_b_sha256": item.text_b.sha256,
                          "tokens_a": len(item.text_a), "tokens_b": len(item.text_b),
                          "diagnostics": diagnostics, "task_ids": [task.task_id for task in tasks]})
        all_tasks.extend(task.as_dict() for task in tasks)
        totals.update({"documents": 1, "tasks": len(tasks),
                       "model_routes": sum(task.route == "model" for task in tasks),
                       "structural_routes": sum(task.route != "model" for task in tasks),
                       "overflow_documents": int(diagnostics["overflow"])})
    prompt_estimate = sum((len(classifier_prompt(task)) + 3) // 4 for item, _ in records
                          for task in build_tasks(item)[0] if task.route == "model")
    expected_completion = totals["model_routes"] * POLICY["max_completion_tokens"]
    conservative_runtime = totals["model_routes"] * (POLICY["max_completion_tokens"] / 29.0 + 0.75)
    result = {
        "schema": TASK_MANIFEST_SCHEMA,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source_manifest": str(source_manifest),
        "source_manifest_sha256": hashlib.sha256(source_manifest.read_bytes()).hexdigest(),
        "source_manifest_declared_sha256": source.get("manifest_sha256"),
        "split": "dev",
        "policy": POLICY,
        "limits": {"documents": 30, "languages": {f"en-{x}": 10 for x in LANGUAGES},
                   "max_tasks_per_document": 12, "max_calls_total": 300,
                   "max_completion_tokens": 96, "attempts": 1, "request_timeout_s": 90,
                   "global_wall_s": 2100},
        "estimate": {**totals, "expected_prompt_tokens_approx": prompt_estimate,
                     "expected_completion_tokens_ceiling": expected_completion,
                     "observed_completion_tokens_per_s_basis": 29.0,
                     "conservative_runtime_s": round(conservative_runtime, 3)},
        "documents": documents, "tasks": all_tasks,
        "gold_isolation": "gold absent from task records, segmentation, alignment, routing and prompts; loaded only by score",
    }
    if totals["documents"] != 30 or any(sum(d["pair"] == f"en-{lang}" for d in documents) != 10 for lang in LANGUAGES):
        raise ValueError("source manifest is not the fixed 30-ID, 10/language sample")
    if totals["overflow_documents"] or totals["model_routes"] > 300 or conservative_runtime > POLICY["global_wall_s"]:
        result["preflight"] = "BLOCKED"
    else:
        result["preflight"] = "FIT"
    result["manifest_sha256"] = _digest(result)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def _task_map(records: Sequence[tuple]) -> dict[str, object]:
    return {task.task_id: task for item, _ in records for task in build_tasks(item)[0]}


def infer(task_manifest_path: Path, out_dir: Path, *, base_url: str, model: str, api_key: str) -> dict:
    frozen = _load(task_manifest_path)
    if frozen.get("schema") != TASK_MANIFEST_SCHEMA or frozen.get("preflight") != "FIT":
        raise ValueError("refusing inference: task manifest is not a FIT frozen SDM manifest")
    if frozen.get("manifest_sha256") != _digest({k: v for k, v in frozen.items() if k != "manifest_sha256"}):
        raise ValueError("task manifest digest mismatch")
    source_path = Path(frozen["source_manifest"])
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != frozen["source_manifest_sha256"]:
        raise ValueError("source manifest changed after freeze")
    records = manifest_records(_load(source_path))
    items = {item.id: item for item, _ in records}
    task_map = _task_map(records)
    if [task_map[value["task_id"]].as_dict() for value in frozen["tasks"]] != frozen["tasks"]:
        raise ValueError("deterministic task reconstruction differs from frozen manifest")
    if out_dir.exists():
        raise FileExistsError(f"refusing to overwrite {out_dir}")
    out_dir.mkdir(parents=True)
    backend = OpenAICompatibleBackend(base_url, model, api_key, timeout_s=POLICY["timeout_s"])
    started = time.monotonic()
    raw_path, decision_path, evidence_path = out_dir / "raw.jsonl", out_dir / "decisions.jsonl", out_dir / "evidence.jsonl"
    counters = Counter()
    systemic_failure = None
    with raw_path.open("w", encoding="utf-8") as raw_handle, decision_path.open("w", encoding="utf-8") as decisions, evidence_path.open("w", encoding="utf-8") as evidence:
        for frozen_task in frozen["tasks"]:
            if time.monotonic() - started >= POLICY["global_wall_s"]:
                systemic_failure = "global_wall_ceiling"
                break
            task = task_map[frozen_task["task_id"]]
            prompt = classifier_prompt(task) if task.route == "model" else None
            if task.route == "model":
                generation = backend.generate(prompt, POLICY["max_completion_tokens"])
                counters["calls"] += 1
                parsed, failure = validate_response(generation)
                raw_text = generation.text
                raw_record = {"schema": RUN_SCHEMA, "task_id": task.task_id, "document_id": task.document_id,
                              "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "prompt": prompt,
                              "response": raw_text, "generation": generation.as_dict()}
                raw_handle.write(json.dumps(raw_record, ensure_ascii=False) + "\n"); raw_handle.flush()
                if generation.error and counters["calls"] == 1:
                    systemic_failure = f"first_call:{generation.error}"
            else:
                parsed, failure = structural_response(task), None
                generation, raw_text = None, None
            status = "resolved" if parsed else "unresolved"
            if parsed and parsed.relation is Relation.UNCERTAIN:
                status = "abstained"
            counters[status] += 1
            if parsed:
                counters[f"relation_{parsed.relation.value}"] += 1
            else:
                counters["unknown"] += 1
            decision = {
                "schema": "uzh-rsd.sdm-decision/v1", "task_id": task.task_id, "document_id": task.document_id,
                "route": task.route, "status": status, "relation": parsed.relation.value if parsed else None,
                "kind": parsed.kind.value if parsed else DifferenceKind.UNKNOWN.value, "failure": failure,
                "raw_response_sha256": hashlib.sha256(raw_text.encode()).hexdigest() if raw_text is not None else None,
                "prompt_version": POLICY["prompt_version"], "schema_version": POLICY["schema_version"], "model": model if generation else None,
                "finish_reason": generation.finish_reason if generation else None,
                "prompt_tokens": generation.prompt_tokens if generation else 0,
                "completion_tokens": generation.completion_tokens if generation else 0,
                "latency_s": generation.latency_s if generation else 0.0,
                "left": task.left.__dict__ if task.left else None, "right": task.right.__dict__ if task.right else None,
            }
            decisions.write(json.dumps(decision, ensure_ascii=False) + "\n"); decisions.flush()
            evidence.write(json.dumps({"schema": "uzh-rsd.sdm-evidence/v1", "task_id": task.task_id,
                                       "observation": task.route, "alignment_basis": task.alignment_basis,
                                       "alignment_status": task.alignment_status, "left": decision["left"], "right": decision["right"],
                                       "provenance": "deterministic_source_offsets"}, ensure_ascii=False) + "\n"); evidence.flush()
            if systemic_failure:
                break
    meta = {
        "schema": RUN_SCHEMA, "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "task_manifest_sha256": frozen["manifest_sha256"], "policy": POLICY,
        "model": {"name": model, "gguf_sha256": MODEL_SHA256, "llama_cpp_commit": LLAMA_COMMIT,
                  "backend": backend.describe()},
        "runtime": {"wall_s": round(time.monotonic() - started, 3), "systemic_failure": systemic_failure,
                    "cost_usd": 0, "device_requested": "SYCL0", "gpu_layers": 99, "ctx": 8192, "parallel": 1,
                    "flash_attention": True},
        "counts": dict(counters),
    }
    for path in (raw_path, decision_path, evidence_path):
        meta.setdefault("artifacts", {})[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    if systemic_failure:
        raise RuntimeError(systemic_failure)
    return meta


def _language_score(grouped: Mapping[str, list]) -> dict:
    results = {lang: evaluate_language(lang, grouped[lang]) for lang in LANGUAGES if grouped.get(lang)}
    macro, reason = macro_average(results)
    return {"per_language": {lang: {"documents": value.documents, "positions": value.positions,
                                     "spearman": value.spearman} for lang, value in results.items()},
            "macro": macro, "macro_undefined_reason": reason}


def score(task_manifest_path: Path, run_dir: Path) -> dict:
    frozen = _load(task_manifest_path)
    records = manifest_records(_load(Path(frozen["source_manifest"])))
    task_map = _task_map(records)
    decisions = [json.loads(line) for line in (run_dir / "decisions.jsonl").read_text().splitlines() if line]
    by_task = {entry["task_id"]: entry for entry in decisions}
    complete_grouped, full_grouped = defaultdict(list), defaultdict(list)
    documents, all_relations = [], Counter()
    b2_root = task_manifest_path.parent.parent / "b2-projection-evidence"
    b2_raw = {row["id"]: row for row in read_raw(b2_root / "local-q8-20261013" / "raw.jsonl")
              if row["method"] == "b2"}
    b2_groups = {"P0_parseable": defaultdict(list), "P1_parseable": defaultdict(list),
                 "P0_full": defaultdict(list), "P1_full": defaultdict(list)}
    for item, gold in records:
        tasks = [task_map[tid] for doc in frozen["documents"] if doc["id"] == item.id for tid in doc["task_ids"]]
        responses = []
        complete = True
        for task in tasks:
            row = by_task.get(task.task_id)
            if not row or row["status"] in ("unresolved", "abstained"):
                responses.append(None); complete = False
                all_relations["UNKNOWN" if not row or row["status"] == "unresolved" else "ABSTAIN"] += 1
            else:
                response = type("R", (), {"relation": Relation(row["relation"]), "kind": DifferenceKind(row["kind"])})()
                responses.append(response); all_relations[row["relation"]] += 1
        projection = project_decisions(item, tasks, responses)
        full_grouped[item.language].append((gold, projection["prediction_a"], projection["prediction_b"]))
        if complete and projection["semantic_complete"]:
            complete_grouped[item.language].append((gold, projection["prediction_a"], projection["prediction_b"]))
        b2_doc_scores = {}
        for variant, cap in (("P0", 40), ("P1", 160)):
            raw = b2_raw[item.id]
            text = raw.get("generation", {}).get("text") if raw.get("status") == "returned" else None
            output = parse_b2(item, text, max_excerpt_tokens=cap)
            if output.diff_a is not None:
                b2_groups[f"{variant}_parseable"][item.language].append((gold, output.diff_a, output.diff_b))
            pa = output.diff_a if output.diff_a is not None else [0.0] * len(item.text_a)
            pb = output.diff_b if output.diff_b is not None else [0.0] * len(item.text_b)
            b2_groups[f"{variant}_full"][item.language].append((gold, pa, pb))
            b2_doc_scores[variant] = evaluate_language(item.language, [(gold, pa, pb)]).spearman
        b3_doc_score = evaluate_language(item.language, [(gold, projection["prediction_a"], projection["prediction_b"])]).spearman
        positive_gold = any(x > 0 for x in (*gold.labels_a, *gold.labels_b) if x != -1)
        predicted_difference = any(projection["prediction_a"]) or any(projection["prediction_b"])
        documents.append({"id": item.id, "pair": item.pair, "tasks": len(tasks), "complete_decisions": complete,
                          "semantic_complete": projection["semantic_complete"], "exact_vector_lengths":
                          len(projection["prediction_a"]) == len(item.text_a) and len(projection["prediction_b"]) == len(item.text_b),
                          "scores": {"b2_p0_full_default": b2_doc_scores["P0"], "b2_p1_full_default": b2_doc_scores["P1"],
                                     "b3_full_default": b3_doc_score},
                          "likely_missed_semantic_difference": positive_gold and not predicted_difference,
                          "prediction_a": projection["prediction_a"], "prediction_b": projection["prediction_b"],
                          "gold_a": list(gold.labels_a), "gold_b": list(gold.labels_b)})
    meta = _load(run_dir / "run_meta.json")
    gens = [json.loads(line)["generation"] for line in (run_dir / "raw.jsonl").read_text().splitlines() if line]
    result = {
        "schema": "uzh-rsd.sdm-results/v1", "task_manifest_sha256": frozen["manifest_sha256"],
        "coverage": {"documents": len(documents), "exact_output_vectors": sum(x["exact_vector_lengths"] for x in documents),
                     "complete_semantic_decisions": sum(x["complete_decisions"] for x in documents),
                     "valid_classifier_responses": sum(row["status"] in ("resolved", "abstained") and row["route"] == "model" for row in decisions),
                     "classifier_calls": meta["counts"].get("calls", 0)},
        "counts": {**dict(all_relations), "tasks": len(frozen["tasks"]),
                   "model_routes": frozen["estimate"]["model_routes"], "structural_routes": frozen["estimate"]["structural_routes"],
                   "overflow_documents": frozen["estimate"]["overflow_documents"]},
        "scores": {"complete_decision_only": _language_score(complete_grouped),
                   "full_sample_evaluation_default_zero": _language_score(full_grouped)},
        "b2_q8_comparison": {
            "P0_parseable_only": _language_score(b2_groups["P0_parseable"]),
            "P1_parseable_only": _language_score(b2_groups["P1_parseable"]),
            "P0_full_sample_evaluation_default_zero": _language_score(b2_groups["P0_full"]),
            "P1_full_sample_evaluation_default_zero": _language_score(b2_groups["P1_full"]),
        },
        "usage": {"prompt_tokens": sum(x.get("prompt_tokens") or 0 for x in gens),
                  "completion_tokens": sum(x.get("completion_tokens") or 0 for x in gens),
                  "latency_s": round(sum(x.get("latency_s") or 0 for x in gens), 3),
                  "median_latency_s": statistics.median([x["latency_s"] for x in gens if x.get("latency_s") is not None]) if gens else None,
                  "cost_usd": 0},
        "documents": documents,
        "likely_missed_semantic_difference_documents": sum(x["likely_missed_semantic_difference"] for x in documents),
        "policy_note": "Zero is an evaluation default for unresolved tokens, never semantic equivalence.",
    }
    deltas = [{"id": x["id"], "pair": x["pair"], "b2_p1": x["scores"]["b2_p1_full_default"],
               "b3": x["scores"]["b3_full_default"],
               "delta": (x["scores"]["b3_full_default"] - x["scores"]["b2_p1_full_default"])
               if x["scores"]["b3_full_default"] is not None and x["scores"]["b2_p1_full_default"] is not None else None}
              for x in documents]
    comparable = [x for x in deltas if x["delta"] is not None]
    both_undefined = [x for x in deltas if x["b2_p1"] is None and x["b3"] is None]
    result["case_analysis"] = {
        "improvement": max(comparable, key=lambda x: x["delta"]) if comparable else None,
        "regression": min(comparable, key=lambda x: x["delta"]) if comparable else None,
        "unchanged_failure": both_undefined[0] if both_undefined else None,
        "attribution": {
            "improvement": "partial projection effect under the zero evaluation default; document decisions are incomplete",
            "regression": "alignment/classification on split URL tokens created false DIFFERENT spans; decisions are incomplete",
            "unchanged_failure": "constant/default vector and unresolved decisions; no complete semantic comparison",
        },
    }
    (run_dir / "results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    result["artifact_sha256"] = {name: hashlib.sha256((run_dir / name).read_bytes()).hexdigest()
                                 for name in ("raw.jsonl", "decisions.jsonl", "evidence.jsonl", "run_meta.json", "results.json")}
    (run_dir / "checksums.json").write_text(json.dumps(result["artifact_sha256"], indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("freeze"); p.add_argument("--source", type=Path, required=True); p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("infer"); p.add_argument("--manifest", type=Path, required=True); p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("score"); p.add_argument("--manifest", type=Path, required=True); p.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "freeze": result = freeze(args.source, args.out)
    elif args.command == "infer": result = infer(args.manifest, args.out, base_url=os.environ["LLM_BASE_URL"], model=os.environ["LLM_NAME"], api_key=os.environ.get("LLM_API_KEY", "local"))
    else: result = score(args.manifest, args.run)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
