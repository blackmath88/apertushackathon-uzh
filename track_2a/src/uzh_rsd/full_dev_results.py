"""Offline, text-free result materialization for the frozen full-dev B0 run."""

from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path

from .data_adapter import GoldLabels, LANGUAGES
from .evaluation import DEFAULT_OFFICIAL_DIR, load_official_function
from .full_dev_baseline import canonical_digest, ledger_state, load_inference_items
from .methods import parse_b0
from .scoring import _score


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_gold(manifest: dict, private_dir: Path) -> dict[str, GoldLabels]:
    rows: dict[str, GoldLabels] = {}
    expected = {entry["id"]: entry for entry in manifest["entries"]}
    for language in LANGUAGES:
        path = private_dir / "scoring" / f"dev_{language}.jsonl"
        if _sha(path) != manifest["private_artifacts"]["scoring_jsonl_sha256"][language]:
            raise ValueError(f"private scoring artifact hash mismatch: {language}")
        for line in path.read_text().splitlines():
            row = json.loads(line)
            entry = expected.get(row["id"])
            if entry is None or row["pair"] != entry["pair"]:
                raise ValueError("unfrozen scoring row")
            if canonical_digest({"labels_a": row["labels_a"], "labels_b": row["labels_b"]}) != entry["gold_sha256"]:
                raise ValueError(f"gold hash mismatch: {row['id']}")
            rows[row["id"]] = GoldLabels(row["id"], tuple(row["labels_a"]), tuple(row["labels_b"]))
    if list(rows) != [entry["id"] for entry in manifest["entries"]]:
        raise ValueError("scoring identity/order differs from manifest")
    return rows


def score_execution(*, manifest_path: Path, private_dir: Path, run_dir: Path, out_dir: Path,
                    official_dir: Path = DEFAULT_OFFICIAL_DIR) -> dict:
    """Score only after generation, emitting no source text or raw response."""
    manifest = json.loads(manifest_path.read_text())
    items = load_inference_items(manifest, private_dir)
    gold = _load_gold(manifest, private_dir)
    state = ledger_state(run_dir / "ledger.jsonl")
    if state["unresolved"] or len(state["terminal"]) != len(manifest["entries"]):
        raise RuntimeError("generation ledger is incomplete; scoring is not permitted")
    parse_token_labels = load_official_function("parse_token_labels", official_dir)

    predictions = []
    all_manifest: dict[str, list] = {language: [] for language in LANGUAGES}
    available: dict[str, list] = {language: [] for language in LANGUAGES}
    generation_status = Counter()
    parse_status = Counter()
    strict_valid = fallback_documents = fallback_tokens = parsed_tokens = 0
    latencies, prompt_tokens, completion_tokens = [], 0, 0
    for sequence, item in enumerate(items):
        result = state["terminal"][sequence]
        generation_status[result["status"]] += 1
        generation = result["generation"]
        if generation.get("latency_s") is not None:
            latencies.append(generation["latency_s"])
        if result["status"] in {"returned", "transport_or_runtime_failure"}:
            prompt_tokens += generation.get("prompt_tokens") or 0
            completion_tokens += generation.get("completion_tokens") or 0
        parsed = parse_b0(item, generation.get("text") if result["status"] == "returned" else None, parse_token_labels)
        if parsed.diff_a is None:
            status = result["status"] if result["status"] != "returned" else parsed.status
            diff_a, diff_b = [0.0] * len(item.text_a), [0.0] * len(item.text_b)
            fallback_documents += 1
            fallback_tokens += len(diff_a) + len(diff_b)
            strict = False
        else:
            status = parsed.status
            diff_a, diff_b = parsed.diff_a, parsed.diff_b
            strict = bool(parsed.diagnostics.get("strict_valid"))
            strict_valid += strict
            parsed_tokens += len(diff_a) + len(diff_b)
            fallback_tokens += sum(
                parsed.diagnostics[side]["fallback"] + parsed.diagnostics[side]["out_of_range"]
                for side in ("a", "b")
            )
            available[item.language].append((gold[item.id], diff_a, diff_b))
        parse_status[status] += 1
        all_manifest[item.language].append((gold[item.id], diff_a, diff_b))
        predictions.append({
            "sequence": sequence, "id": item.id, "pair": item.pair,
            "generation_status": result["status"], "parse_status": status,
            "strict_valid": strict, "fallback_document": parsed.diff_a is None,
            "labels_a": diff_a, "labels_b": diff_b,
        })

    out_dir.mkdir(parents=True, exist_ok=False)
    prediction_path = out_dir / "predictions.jsonl"
    prediction_path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in predictions))
    # The pinned official implementation is mandatory here, not an optional cross-check.
    from .evaluation import load_official_compute_correlations
    official = load_official_compute_correlations(official_dir)
    all_score = _official_scores(_score(all_manifest, official))
    available_score = _official_scores(_score(available, official))
    generation_summary = json.loads((run_dir / "generation-summary.json").read_text())
    attempted = generation_status["returned"] + generation_status["transport_or_runtime_failure"]
    summary = {
        "schema": "uzh-rsd.full-dev-b0-results/v1",
        "manifest_sha256": manifest["manifest_sha256"],
        "counts": {
            "intended": len(state["intents"]), "attempted": attempted,
            "returned": generation_status["returned"], "unstarted": len(items) - len(state["intents"]),
            "generation_status": dict(sorted(generation_status.items())),
            "parse_status": dict(sorted(parse_status.items())),
            "parseable": sum(len(rows) for rows in available.values()),
            "strictly_valid": strict_valid, "fallback_documents": fallback_documents,
            "fallback_tokens": fallback_tokens, "parsed_tokens": parsed_tokens,
        },
        "all_manifest": all_score,
        "available_only": {**available_score, "denominators": {language: len(available[language]) for language in LANGUAGES}},
        "usage": {
            "prompt_tokens_total": prompt_tokens, "completion_tokens_total": completion_tokens,
            "combined_tokens_total": prompt_tokens + completion_tokens,
            "latency_s_total": round(sum(latencies), 3),
            "latency_s_median": round(statistics.median(latencies), 3) if latencies else None,
            "generation_wall_s": generation_summary["wall_s"],
        },
        "integrity": {
            "ledger_sha256": _sha(run_dir / "ledger.jsonl"),
            "predictions_sha256": _sha(prediction_path),
            "response_hashes_verified": True,
            "official_evaluator_pinned": True,
        },
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    report = render_report(summary)
    (out_dir / "REPORT.md").write_text(report)
    return summary


def _official_scores(score: dict) -> dict:
    """Make the pinned official evaluator authoritative after parity checking."""
    official_values = []
    for language in LANGUAGES:
        entry = score["per_language"][language]
        official = entry.get("official_spearman")
        if not isinstance(official, float):
            raise RuntimeError(f"official evaluator did not return a numeric {language} Spearman: {official}")
        local = entry["spearman"]
        if local is None or abs(local - official) > 1e-12:
            raise RuntimeError(f"official/local Spearman mismatch for {language}: {official} != {local}")
        entry["implementation_spearman"] = local
        entry["spearman"] = official
        official_values.append(official)
    score["implementation_macro"] = score["macro"]
    score["macro"] = sum(official_values) / len(official_values)
    return score


def render_report(summary: dict) -> str:
    counts, usage = summary["counts"], summary["usage"]
    lines = [
        "# Frozen full-dev B0 execution", "",
        f"Intended {counts['intended']}; attempted {counts['attempted']}; returned {counts['returned']}; unstarted {counts['unstarted']}.",
        f"Parseable {counts['parseable']}; strictly valid {counts['strictly_valid']}; fallback documents {counts['fallback_documents']}; fallback tokens {counts['fallback_tokens']}.",
        "", "## Official Spearman", "", "| View | EN-DE | EN-FR | EN-IT | Macro |", "|---|---:|---:|---:|---:|",
    ]
    for label, key in (("All manifest", "all_manifest"), ("Available only", "available_only")):
        score = summary[key]
        cells = [score["per_language"][language]["spearman"] for language in LANGUAGES]
        lines.append(f"| {label} | {cells[0]:.6f} | {cells[1]:.6f} | {cells[2]:.6f} | {score['macro']:.6f} |")
    den = summary["available_only"]["denominators"]
    lines += ["", f"Available-only denominators: EN-DE {den['de']}, EN-FR {den['fr']}, EN-IT {den['it']}.", "",
              "## Accounting", "",
              f"Prompt tokens {usage['prompt_tokens_total']}; completion tokens {usage['completion_tokens_total']}; combined {usage['combined_tokens_total']}.",
              f"Endpoint latency total {usage['latency_s_total']:.3f} s; median {usage['latency_s_median']:.3f} s; generation wall {usage['generation_wall_s']:.3f} s.", "",
              "Missing or unparseable documents use the frozen upstream similarity-5 (zero-difference) fallback only in the all-manifest view. Raw prompts, responses, and gold-bearing scoring inputs remain private; committed predictions contain no source text.", ""]
    return "\n".join(lines)


def write_checksums(out_dir: Path, private_run_dir: Path) -> None:
    names = ("predictions.jsonl", "summary.json", "REPORT.md")
    lines = [f"{_sha(out_dir / name)}  {name}" for name in names]
    lines.append(f"{_sha(private_run_dir / 'ledger.jsonl')}  PRIVATE:ledger.jsonl")
    (out_dir / "checksums.sha256").write_text("\n".join(lines) + "\n")
