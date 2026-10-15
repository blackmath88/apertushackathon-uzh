"""Deterministic integrity and result analysis for a completed B8 local-only run."""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from .b8 import _jsonl, _read_json, _write_json, canonical_sha256, evaluate_rows, sha256


def _rate(rows, predicate):
    return sum(bool(predicate(row)) for row in rows) / len(rows) if rows else None


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _family_bootstrap(rows: list[dict], *, samples: int, seed: int) -> dict:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["source_family_id"]].append(row)
    families = sorted(grouped)
    rng = random.Random(seed)
    draws = []
    for _ in range(samples):
        sample = [rng.choice(families) for _ in families]
        sampled_rows = [row for family in sample for row in grouped[family]]
        draws.append(_rate(sampled_rows, lambda row: row.get("label") == row.get("expected_relation")))
    return {
        "method": "source-family clustered bootstrap with replacement",
        "families": len(families),
        "samples": samples,
        "seed": seed,
        "accuracy": _rate(rows, lambda row: row.get("label") == row.get("expected_relation")),
        "ci95": [_quantile(draws, 0.025), _quantile(draws, 0.975)],
    }


def analyze(protocol: dict, schedule: list[dict], rows: list[dict], *, ledger_path: Path) -> dict:
    if len(schedule) != len(rows):
        raise ValueError("schedule/ledger row count mismatch")
    integrity_failures = []
    for index, (plan, row) in enumerate(zip(schedule, rows), 1):
        if row.get("sequence") != index or row.get("call_id") != plan.get("call_id"):
            integrity_failures.append({"sequence": index, "error": "order/call id mismatch"})
        if row.get("plan_sha256") != canonical_sha256(plan):
            integrity_failures.append({"sequence": index, "error": "plan hash mismatch"})
        if row.get("prompt_sha256") != plan.get("prompt_sha256"):
            integrity_failures.append({"sequence": index, "error": "prompt hash mismatch"})
    if integrity_failures:
        raise ValueError(f"ledger integrity failure: {integrity_failures[:3]}")

    base = evaluate_rows(protocol, rows)
    direct = {rep: [row for row in rows if row["arm"] == "matched_direct" and row["representation"] == rep]
              for rep in ("R0", "R1", "R2", "R3")}
    deterministic = [row for row in rows if row["arm"] == "transfer"
                     and row.get("transfer_contract") == "deterministic_no_teacher"]
    bootstrap = {rep: _family_bootstrap(values, samples=10000, seed=20261014 + index)
                 for index, (rep, values) in enumerate(direct.items())}
    bootstrap["deterministic_no_teacher"] = _family_bootstrap(deterministic, samples=10000, seed=20261018)
    latencies = [row["latency_seconds"] for row in rows]
    language = {}
    for name, values in (("R2", direct["R2"]), ("deterministic_no_teacher", deterministic)):
        language[name] = {
            lang: {
                "count": len(group),
                "accuracy": _rate(group, lambda row: row.get("label") == row.get("expected_relation")),
                "valid_rate": _rate(group, lambda row: row.get("valid") is True),
            }
            for lang in sorted({row["language_pair"] for row in values})
            for group in [[row for row in values if row["language_pair"] == lang]]
        }
    raw_outputs = Counter(row["raw_output"] for row in rows)
    finish_reasons = Counter(row["backend_response"]["choices"][0].get("finish_reason") for row in rows)
    return {
        "schema": "uzh-rsd.b8-local-analysis/v1",
        "verdict": "INCONCLUSIVE",
        "verdict_reason": "Frontier teacher and teacher-derived transfer arms were not authorized or run; the frozen promotion gate is not evaluable.",
        "teacher_status": "NOT RUN — AUTHORIZATION/PROVIDER",
        "official_benchmark_gain": "NOT_MEASURED",
        "integrity": {
            "schedule_rows": len(schedule),
            "ledger_rows": len(rows),
            "ordered_call_ids_match": True,
            "plan_hashes_match": True,
            "prompt_hashes_match": True,
            "ledger_sha256": sha256(ledger_path),
        },
        "usage": {
            "calls": len(rows),
            "failures": sum(row.get("error") is not None for row in rows),
            "estimated_prompt_tokens": sum(plan["estimated_prompt_tokens"] for plan in schedule),
            "reported_prompt_tokens": sum(row.get("usage", {}).get("prompt_tokens", 0) or 0 for row in rows),
            "reported_completion_tokens": sum(row.get("usage", {}).get("completion_tokens", 0) or 0 for row in rows),
            "latency_seconds": {
                "sum": sum(latencies),
                "min": min(latencies),
                "median": statistics.median(latencies),
                "mean": statistics.mean(latencies),
                "p95": _quantile(latencies, 0.95),
                "max": max(latencies),
            },
        },
        "output_quality": {
            "valid_outputs": sum(row.get("valid") is True for row in rows),
            "valid_rate": _rate(rows, lambda row: row.get("valid") is True),
            "raw_output_counts": dict(sorted(raw_outputs.items())),
            "finish_reason_counts": dict(sorted(finish_reasons.items())),
            "http_status_counts": dict(sorted(Counter(str(row.get("http_status")) for row in rows).items())),
        },
        "direct_representations": {
            rep: {
                "count": len(values),
                "accuracy": _rate(values, lambda row: row.get("label") == row.get("expected_relation")),
                "valid_rate": _rate(values, lambda row: row.get("valid") is True),
            }
            for rep, values in direct.items()
        },
        "deterministic_no_teacher": {
            "count": len(deterministic),
            "accuracy": _rate(deterministic, lambda row: row.get("label") == row.get("expected_relation")),
            "valid_rate": _rate(deterministic, lambda row: row.get("valid") is True),
            "accuracy_delta_vs_R2": _rate(deterministic, lambda row: row.get("label") == row.get("expected_relation"))
            - _rate(direct["R2"], lambda row: row.get("label") == row.get("expected_relation")),
        },
        "per_language": language,
        "family_clustered_bootstrap": bootstrap,
        "frozen_gate_inputs": base["checks"],
        "frozen_metrics": base["metrics"],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = analyze(_read_json(args.package / "protocol.json"), _jsonl(args.schedule), _jsonl(args.ledger), ledger_path=args.ledger)
    _write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
