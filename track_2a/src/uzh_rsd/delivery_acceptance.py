"""Freeze, execute, replay, and score the small long-input dev acceptance set.

``freeze`` and ``infer`` are gold-blind.  Only the separate ``score`` command
opens the scoring directory, after predictions already exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

from .data_adapter import GoldLabels, LANGUAGES
from .full_dev_baseline import canonical_digest, load_inference_items
from .scoring import _score
from .windowed_b2 import METHOD_VERSION, execute_document, plan_document, replay_document

SCHEMA = "uzh-rsd.long-input-acceptance/v1"


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n", encoding="utf-8")


def freeze_manifest(full_manifest: dict) -> dict:
    groups: dict[int, list[dict]] = {}
    for entry in full_manifest["entries"]:
        groups.setdefault(int(entry["original_order"]), []).append(entry)
    complete = {index: rows for index, rows in groups.items() if {row["language"] for row in rows} == set(LANGUAGES)}
    if not complete:
        raise ValueError("no complete three-language groups")

    def total(rows):
        return max(row["token_count_a"] + row["token_count_b"] for row in rows)

    def asymmetry(rows):
        return max(max(row["token_count_a"], row["token_count_b"]) /
                   max(1, min(row["token_count_a"], row["token_count_b"])) for row in rows)

    longest = max(complete, key=lambda index: (total(complete[index]), -index))
    totals = sorted(total(rows) for rows in complete.values())
    median = totals[len(totals) // 2]
    candidates = [index for index, rows in complete.items() if index != longest and total(rows) >= median]
    asymmetric = max(candidates, key=lambda index: (asymmetry(complete[index]), total(complete[index]), -index))
    selected = []
    for index, role in ((longest, "longest_group"), (asymmetric, "asymmetric_long_group")):
        for language in LANGUAGES:
            entry = next(row for row in complete[index] if row["language"] == language)
            selected.append({key: entry[key] for key in ("id", "pair", "language", "original_order", "token_count_a",
                                                          "token_count_b", "text_a_sha256", "text_b_sha256")})
            selected[-1]["selection_role"] = role
    body = {
        "schema": SCHEMA, "split": "dev", "method": METHOD_VERSION,
        "selection": "gold-blind: all-language group with maximum total length, plus highest side-ratio group among remaining groups at or above median total length",
        "source_manifest_sha256": full_manifest["manifest_sha256"],
        "private_inference_sha256": full_manifest["private_artifacts"]["inference_jsonl_sha256"],
        "entries": selected,
        "acceptance": {
            "documents_complete": "6/6", "official_tokens_processed": "all", "vector_contract": "exact lengths; finite [0,1]",
            "responses": "no call failure, length finish, malformed JSON, invalid evidence, or unlocated non-empty excerpt",
            "context": "max(prompt_tokens + 1024) <= 8192 when endpoint usage is available",
            "replay": "offline replay vectors byte-equivalent to generated vectors",
            "semantics": "official per-language and macro Spearman measured and disclosed; not a promotion gate",
        },
    }
    body["manifest_sha256"] = canonical_digest(body)
    return body


def _selected_items(manifest: dict, full_manifest: dict, private_dir: Path):
    if manifest["source_manifest_sha256"] != full_manifest["manifest_sha256"]:
        raise ValueError("acceptance manifest does not name this full manifest")
    items = {item.id: item for item in load_inference_items(full_manifest, private_dir)}
    selected = []
    for entry in manifest["entries"]:
        item = items[entry["id"]]
        if item.text_a.sha256 != entry["text_a_sha256"] or item.text_b.sha256 != entry["text_b_sha256"]:
            raise ValueError(f"selected text hash mismatch: {item.id}")
        selected.append(item)
    return selected


def infer(manifest: dict, full_manifest: dict, private_dir: Path, out_dir: Path, backend, *, total_timeout_s: float) -> dict:
    items = _selected_items(manifest, full_manifest, private_dir)
    out_dir.mkdir(parents=True, exist_ok=False)
    ledger = out_dir / "window-ledger.jsonl"
    started, deadline = time.monotonic(), time.monotonic() + total_timeout_s
    predictions, documents = [], []
    for item in items:
        result = execute_document(backend, item, ledger, run_id=out_dir.name, total_deadline=deadline)
        documents.append({key: value for key, value in result.items() if key not in {"labels_a", "labels_b"}})
        if result["status"] == "complete":
            predictions.append({"id": item.id, "language": item.language,
                                "labels_a": result["labels_a"], "labels_b": result["labels_b"]})
    prediction_path = out_dir / "predictions.jsonl"
    prediction_path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in predictions), encoding="utf-8")
    ledger_rows = [json.loads(line) for line in ledger.read_text().splitlines()]
    by_id = {row["id"]: row for row in predictions}
    replay_ok = True
    for item in items:
        replay = replay_document(item, ledger_rows)
        expected = by_id.get(item.id)
        replay_ok &= expected is not None and replay["status"] == "complete" \
            and replay["labels_a"] == expected["labels_a"] and replay["labels_b"] == expected["labels_b"]
    task_rows = [task for document in documents for task in document["tasks"]]
    latencies = [task["latency_s"] for task in task_rows if task.get("latency_s") is not None]
    prompt_tokens = [task["prompt_tokens"] for task in task_rows if task.get("prompt_tokens") is not None]
    context_ok = bool(prompt_tokens) and max(prompt_tokens) + 1024 <= 8192
    complete = len(predictions) == len(items) and all(document["status"] == "complete" for document in documents)
    summary = {
        "schema": SCHEMA, "stage": "dev_inference", "method": METHOD_VERSION,
        "manifest_sha256": manifest["manifest_sha256"], "documents": documents,
        "counts": {"documents": len(items), "complete_documents": len(predictions),
                   "planned_requests": sum(document["planned_requests"] for document in documents),
                   "completed_requests": sum(document["completed_requests"] for document in documents)},
        "usage": {"wall_s": round(time.monotonic() - started, 3), "latency_s_total": round(sum(latencies), 3),
                  "latency_s_median": statistics.median(latencies) if latencies else None,
                  "latency_s_max": max(latencies) if latencies else None,
                  "prompt_tokens_max": max(prompt_tokens) if prompt_tokens else None,
                  "completion_tokens_max": max((task.get("completion_tokens") or 0 for task in task_rows), default=None)},
        "checks": {"complete": complete, "offline_replay_equal": replay_ok, "context_bound": context_ok,
                   "prediction_sha256": hashlib.sha256(prediction_path.read_bytes()).hexdigest()},
    }
    summary["accepted"] = all(summary["checks"][key] for key in ("complete", "offline_replay_equal", "context_bound"))
    _write(out_dir / "inference-summary.json", summary)
    return summary


def score(manifest: dict, run_dir: Path, scoring_dir: Path, official_dir: Path) -> dict:
    predictions = {row["id"]: row for row in (json.loads(line) for line in (run_dir / "predictions.jsonl").read_text().splitlines())}
    selected = {entry["id"]: entry for entry in manifest["entries"]}
    gold = {}
    for language in LANGUAGES:
        for line in (scoring_dir / f"dev_{language}.jsonl").read_text().splitlines():
            row = json.loads(line)
            if row["id"] in selected:
                gold[row["id"]] = GoldLabels(row["id"], tuple(row["labels_a"]), tuple(row["labels_b"]))
    if set(gold) != set(selected) or set(predictions) != set(selected):
        raise ValueError("scoring ids do not exactly match accepted predictions")
    grouped = {language: [] for language in LANGUAGES}
    for entry in manifest["entries"]:
        prediction = predictions[entry["id"]]
        if len(prediction["labels_a"]) != entry["token_count_a"] or len(prediction["labels_b"]) != entry["token_count_b"]:
            raise ValueError(f"prediction length mismatch: {entry['id']}")
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or not 0 <= v <= 1
               for v in prediction["labels_a"] + prediction["labels_b"]):
            raise ValueError(f"invalid prediction value: {entry['id']}")
        grouped[entry["language"]].append((gold[entry["id"]], prediction["labels_a"], prediction["labels_b"]))
    from .evaluation import load_official_compute_correlations
    official = load_official_compute_correlations(official_dir)
    result = _score(grouped, official)
    result.update(schema=SCHEMA, stage="diagnostic_dev_scoring", manifest_sha256=manifest["manifest_sha256"],
                  note="Gold loaded only after frozen prediction generation; never used by prompts or routing.")
    _write(run_dir / "score-summary.json", result)
    return result


def diagnostic_score(manifest: dict, full_manifest: dict, private_dir: Path, run_dir: Path,
                     scoring_dir: Path, official_dir: Path) -> dict:
    """Score permissive partial replay after strict acceptance has failed.

    This never creates candidate predictions. It measures the legacy B2
    parser's usable-window view and an explicitly labelled zero-fallback
    sensitivity view from already saved dev responses.
    """
    from .backends import Generation
    from .methods import parse_b2
    from .windowed_b2 import _slice_item

    items = _selected_items(manifest, full_manifest, private_dir)
    ledger = [json.loads(line) for line in (run_dir / "window-ledger.jsonl").read_text().splitlines()]
    returns = {(row["document_id"], row["task_id"]): row for row in ledger if row["event"] == "return"}
    gold = {}
    for language in LANGUAGES:
        for line in (scoring_dir / f"dev_{language}.jsonl").read_text().splitlines():
            row = json.loads(line)
            if any(entry["id"] == row["id"] for entry in manifest["entries"]):
                gold[row["id"]] = GoldLabels(row["id"], tuple(row["labels_a"]), tuple(row["labels_b"]))
    all_rows = {language: [] for language in LANGUAGES}
    usable_rows = {language: [] for language in LANGUAGES}
    documents, issue_counts = [], Counter()
    latencies, prompt_tokens, completion_tokens = [], [], []
    for item in items:
        a, b = [0.0] * len(item.text_a), [0.0] * len(item.text_b)
        processed_a, processed_b = [False] * len(a), [False] * len(b)
        problems, diagnostics = [], Counter()
        pairs = plan_document(item)
        for pair in pairs:
            row = returns.get((item.id, pair.task_id))
            if row is None:
                problems.append(f"{pair.task_id}:missing_return")
                issue_counts["missing_return"] += 1
                continue
            generation = Generation(**row["generation"])
            if generation.latency_s is not None:
                latencies.append(generation.latency_s)
            if generation.prompt_tokens is not None:
                prompt_tokens.append(generation.prompt_tokens)
            if generation.completion_tokens is not None:
                completion_tokens.append(generation.completion_tokens)
            if generation.finish_reason == "length":
                problems.append(f"{pair.task_id}:truncated")
                issue_counts["truncated"] += 1
                continue
            output = parse_b2(_slice_item(item, pair), generation.text)
            if output.diff_a is None:
                problems.append(f"{pair.task_id}:{output.status}")
                issue_counts[output.status] += 1
                continue
            diagnostics.update({key: value for key, value in output.diagnostics.items() if isinstance(value, int)})
            for offset, value in enumerate(output.diff_a):
                index = pair.left.start + offset
                a[index], processed_a[index] = max(a[index], float(value)), True
            for offset, value in enumerate(output.diff_b):
                index = pair.right.start + offset
                b[index], processed_b[index] = max(b[index], float(value)), True
        usable = not problems and all(processed_a) and all(processed_b)
        row = (gold[item.id], a, b)
        all_rows[item.language].append(row)
        if usable:
            usable_rows[item.language].append(row)
        documents.append({"id": item.id, "language": item.language, "usable": usable, "problems": problems,
                          "processed_tokens_a": sum(processed_a), "total_tokens_a": len(a),
                          "processed_tokens_b": sum(processed_b), "total_tokens_b": len(b),
                          "parser_diagnostics": dict(diagnostics)})
    from .evaluation import load_official_compute_correlations
    official = load_official_compute_correlations(official_dir)
    result = {
        "schema": SCHEMA, "stage": "post_generation_dev_diagnostic_scoring", "method": METHOD_VERSION,
        "manifest_sha256": manifest["manifest_sha256"],
        "warning": "NOT candidate predictions: permissive legacy B2 parsing; failed/unprocessed windows are zero only in the labelled sensitivity view",
        "strict_acceptance": False, "documents": documents,
        "coverage": {"usable_documents": sum(document["usable"] for document in documents),
                     "total_documents": len(documents), "issues": dict(sorted(issue_counts.items()))},
        "usable_only": _score(usable_rows, official),
        "zero_fallback_sensitivity": _score(all_rows, official),
        "usage": {"requests_returned": len(returns), "latency_s_total": round(sum(latencies), 3),
                  "latency_s_median": statistics.median(latencies), "latency_s_max": max(latencies),
                  "prompt_tokens_total": sum(prompt_tokens), "prompt_tokens_max": max(prompt_tokens),
                  "completion_tokens_total": sum(completion_tokens), "completion_tokens_max": max(completion_tokens),
                  "context_plus_reserved_output_max": max(prompt_tokens) + 1024},
    }
    _write(run_dir / "diagnostic-score-summary.json", result)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--full-manifest", type=Path, required=True)
    freeze.add_argument("--out", type=Path, required=True)
    run = sub.add_parser("infer")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--full-manifest", type=Path, required=True)
    run.add_argument("--private-dir", type=Path, required=True)
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--timeout-s", type=float, default=300)
    run.add_argument("--total-timeout-s", type=float, default=3600)
    scoring = sub.add_parser("score")
    scoring.add_argument("--manifest", type=Path, required=True)
    scoring.add_argument("--run-dir", type=Path, required=True)
    scoring.add_argument("--scoring-dir", type=Path, required=True)
    scoring.add_argument("--official-dir", type=Path, required=True)
    diagnostic = sub.add_parser("diagnose-score")
    diagnostic.add_argument("--manifest", type=Path, required=True)
    diagnostic.add_argument("--full-manifest", type=Path, required=True)
    diagnostic.add_argument("--private-dir", type=Path, required=True)
    diagnostic.add_argument("--run-dir", type=Path, required=True)
    diagnostic.add_argument("--scoring-dir", type=Path, required=True)
    diagnostic.add_argument("--official-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "freeze":
        body = freeze_manifest(json.loads(args.full_manifest.read_text()))
        _write(args.out, body)
    elif args.command == "infer":
        from .backends import OpenAICompatibleBackend
        missing = [name for name in ("LLM_BASE_URL", "LLM_NAME", "LLM_API_KEY") if not os.environ.get(name)]
        if missing:
            raise SystemExit(f"missing endpoint variables: {missing}")
        backend = OpenAICompatibleBackend(os.environ["LLM_BASE_URL"], os.environ["LLM_NAME"], os.environ["LLM_API_KEY"],
                                          timeout_s=args.timeout_s)
        body = infer(json.loads(args.manifest.read_text()), json.loads(args.full_manifest.read_text()),
                     args.private_dir, args.out, backend, total_timeout_s=args.total_timeout_s)
        print(json.dumps(body, indent=2))
        return 0 if body["accepted"] else 4
    elif args.command == "score":
        body = score(json.loads(args.manifest.read_text()), args.run_dir, args.scoring_dir, args.official_dir)
        print(json.dumps(body, indent=2))
    else:
        body = diagnostic_score(json.loads(args.manifest.read_text()), json.loads(args.full_manifest.read_text()),
                                args.private_dir, args.run_dir, args.scoring_dir, args.official_dir)
        print(json.dumps(body, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
