"""Offline, development-only error analysis for the staged comparison.

This command never calls a model.  It replays saved responses, projects them
with the frozen B2 parser, and joins development gold only for diagnostics.
Exact source text, responses, excerpts, and labels are written only below the
ignored private output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Mapping, Sequence

from .data_adapter import GoldLabels, InferenceInput, LANGUAGES
from .evaluation import assemble, evaluate_language, load_official_compute_correlations, macro_average, spearman
from .methods import B2_MAX_EXCERPT_TOKENS, load_json_object, locate, parse_b2
from .tokens import tokenize

SCHEMA = "uzh-rsd.nebu-staged-error-analysis/v1"
SAMPLE_GROUPS_PER_STRATUM = 2


def _read_json(path: Path):
    return json.loads(path.read_text())


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _sha_text(text: str) -> str:
    return _sha_bytes(text.encode())


def _write_new(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _selected_rows(subset: Mapping) -> list[dict]:
    selected: list[dict] = []
    for stratum in ("short", "medium", "long"):
        rows = [row for row in subset["validation_execution"] if row["stratum"] == stratum]
        groups: list[str] = []
        for row in rows:
            if row["group_key"] not in groups:
                groups.append(row["group_key"])
        keep = set(groups[:SAMPLE_GROUPS_PER_STRATUM])
        selected.extend(row for row in rows if row["group_key"] in keep)
    if len(selected) != 18:
        raise ValueError(f"expected balanced 18-case sample, got {len(selected)}")
    return selected


def _load_private_rows(private_baseline: Path, manifest: Mapping) -> tuple[dict, dict]:
    if manifest.get("split") != "dev":
        raise ValueError("error analysis is restricted to the development split")
    inference, gold = {}, {}
    for language in LANGUAGES:
        inference_path = private_baseline / "inference" / f"dev_{language}.jsonl"
        scoring_path = private_baseline / "scoring" / f"dev_{language}.jsonl"
        expected = manifest["private_artifacts"]
        if _sha_file(inference_path) != expected["inference_jsonl_sha256"][language]:
            raise ValueError(f"inference hash mismatch: {language}")
        if _sha_file(scoring_path) != expected["scoring_jsonl_sha256"][language]:
            raise ValueError(f"scoring hash mismatch: {language}")
        inference.update((row["id"], row) for row in _jsonl(inference_path))
        gold.update((row["id"], row) for row in _jsonl(scoring_path))
    return inference, gold


def _mask_values(gold: GoldLabels, a: Sequence[float], b: Sequence[float]) -> tuple[list[float], list[float]]:
    prediction, labels, _ = assemble([(gold, a, b)])
    return prediction, labels


def _support_stats(prediction: Sequence[float], labels: Sequence[float]) -> dict:
    predicted = {i for i, value in enumerate(prediction) if value > 0}
    positive = {i for i, value in enumerate(labels) if value > 0}
    overlap = predicted & positive
    return {
        "predicted_positive": len(predicted),
        "gold_positive": len(positive),
        "overlap": len(overlap),
        "positive_precision": len(overlap) / len(predicted) if predicted else None,
        "positive_recall": len(overlap) / len(positive) if positive else None,
    }


def _difference_trace(item: InferenceInput, response: str) -> tuple[list[dict], list[dict]]:
    data, _mode = load_json_object(response)
    if data is None or not isinstance(data.get("differences"), list):
        return [], []
    public, private = [], []
    for index, entry in enumerate(data["differences"]):
        if not isinstance(entry, dict):
            public.append({"index": index, "valid_object": False})
            private.append({"index": index, "value": entry})
            continue
        sides = {}
        private_sides = {}
        for key, tokens in (("a", item.text_a.tokens), ("b", item.text_b.tokens)):
            excerpt = entry.get(key, "")
            if not isinstance(excerpt, str):
                sides[key] = {"valid_string": False}
                private_sides[key] = excerpt
                continue
            spans, mode = locate(tokens, excerpt, max_excerpt_tokens=B2_MAX_EXCERPT_TOKENS)
            sides[key] = {
                "excerpt_sha256": _sha_text(excerpt),
                "excerpt_tokens": len(excerpt.split()),
                "locate_mode": mode,
                "spans": [[span.start, span.end] for span in spans],
            }
            private_sides[key] = excerpt
        public.append({
            "index": index,
            "kind": entry.get("kind"),
            "severity": entry.get("severity"),
            "sides": sides,
        })
        private.append({"index": index, "kind": entry.get("kind"), "severity": entry.get("severity"), "sides": private_sides})
    return public, private


def run(*, package: Path, ledger: Path, baseline_manifest: Path, private_baseline: Path,
        classifications: Path, public_out: Path, private_out: Path, official_dir: Path) -> dict:
    manifest = _read_json(baseline_manifest)
    subset = _read_json(package / "subset-manifest.json")
    chosen = _selected_rows(subset)
    chosen_ids = [row["id"] for row in chosen]
    annotations = _read_json(classifications)
    if set(annotations["cases"]) != set(chosen_ids):
        raise ValueError("manual classifications do not exactly match the frozen sample")
    inference_rows, gold_rows = _load_private_rows(private_baseline, manifest)
    result_rows = {row["id"]: row for row in _jsonl(ledger) if row.get("event") == "result" and row.get("candidate") == "C1"}
    saved_rows = {row["id"]: row for row in _jsonl(package / "validation" / "predictions.jsonl") if row["candidate"] == "C1"}
    if set(chosen_ids) - set(result_rows) or set(chosen_ids) - set(saved_rows):
        raise ValueError("sample is not covered by saved validation artifacts")

    entries = {row["id"]: row for row in manifest["entries"]}
    public_cases, private_cases = [], []
    score_rows = defaultdict(list)
    raw_official = defaultdict(lambda: ([], []))
    category_counts = Counter()
    category_by_stratum = defaultdict(Counter)
    category_by_language = defaultdict(Counter)
    fatal_truncations = item_malformed = 0

    for selected in chosen:
        record_id = selected["id"]
        raw = inference_rows[record_id]
        item = InferenceInput(record_id, selected["language"], tokenize(raw["text_a"]), tokenize(raw["text_b"]), raw["page_en"], raw["page_other"])
        expected = entries[record_id]
        if item.text_a.sha256 != expected["text_a_sha256"] or item.text_b.sha256 != expected["text_b_sha256"]:
            raise ValueError(f"token/input identity mismatch: {record_id}")
        result = result_rows[record_id]
        response = result["generation"].get("text") or ""
        parsed = parse_b2(item, response)
        saved = saved_rows[record_id]
        prediction_a = parsed.diff_a if parsed.diff_a is not None else [0.0] * len(item.text_a)
        prediction_b = parsed.diff_b if parsed.diff_b is not None else [0.0] * len(item.text_b)
        if prediction_a != saved["labels_a"] or prediction_b != saved["labels_b"] or parsed.status != saved["parse_status"]:
            raise ValueError(f"offline replay differs from preserved prediction: {record_id}")
        gold = GoldLabels(record_id, tuple(gold_rows[record_id]["labels_a"]), tuple(gold_rows[record_id]["labels_b"]))
        masked_prediction, masked_gold = _mask_values(gold, prediction_a, prediction_b)
        doc_rho = spearman(masked_prediction, masked_gold)
        support = _support_stats(masked_prediction, masked_gold)
        score_rows[item.language].append((gold, prediction_a, prediction_b))
        raw_prediction, raw_gold = raw_official[item.language]
        raw_prediction.extend(prediction_a); raw_gold.extend(gold.labels_a)
        if not all(value == -1 for value in gold.labels_b):
            raw_prediction.extend(prediction_b); raw_gold.extend(gold.labels_b)

        differences, private_differences = _difference_trace(item, response)
        invalid_items = sum(1 for row in differences if row.get("severity") == 0 or row.get("valid_object") is False)
        if result["generation"].get("finish_reason") == "length" and parsed.status == "unparseable":
            fatal_truncations += 1
        if invalid_items:
            item_malformed += 1
        classification = annotations["cases"][record_id]
        for category in classification["labels"]:
            category_counts[category] += 1
            category_by_stratum[category][selected["stratum"]] += 1
            category_by_language[category][item.language] += 1

        public_cases.append({
            "id": record_id,
            "language": item.language,
            "stratum": selected["stratum"],
            "group_key": selected["group_key"],
            "input": {"text_a_sha256": item.text_a.sha256, "text_b_sha256": item.text_b.sha256,
                      "tokens_a": len(item.text_a), "tokens_b": len(item.text_b)},
            "model_response": {"sha256": _sha_text(response), "finish_reason": result["generation"].get("finish_reason"),
                               "completion_tokens": result["generation"].get("completion_tokens")},
            "parsed_difference": {"status": parsed.status, "diagnostics": parsed.diagnostics, "items": differences},
            "projected_token_scores": {"sha256_a": _sha_bytes(json.dumps(prediction_a, separators=(",", ":")).encode()),
                                       "sha256_b": _sha_bytes(json.dumps(prediction_b, separators=(",", ":")).encode()),
                                       "nonzero_a": sum(value > 0 for value in prediction_a),
                                       "nonzero_b": sum(value > 0 for value in prediction_b)},
            "official_evaluation": {"positions": len(masked_gold), "masked": len(prediction_a) + (0 if all(v == -1 for v in gold.labels_b) else len(prediction_b)) - len(masked_gold),
                                    "per_document_diagnostic_spearman": doc_rho, **support},
            "classification": classification,
        })
        private_cases.append({
            "id": record_id,
            "input": {"text_a": item.text_a.text, "text_b": item.text_b.text},
            "response": response,
            "parsed_differences": private_differences,
            "predictions": {"a": prediction_a, "b": prediction_b},
            "gold_diagnostic_only": {"a": list(gold.labels_a), "b": list(gold.labels_b)},
            "classification": classification,
        })

    per_language = {language: evaluate_language(language, score_rows[language]) for language in LANGUAGES}
    macro, reason = macro_average(per_language)
    official = load_official_compute_correlations(official_dir)
    parity = {}
    for language in LANGUAGES:
        predictions, labels = raw_official[language]
        (rho, _interval), _kendall = official(predictions, labels, False)
        parity[language] = {"ours": per_language[language].spearman, "official": float(rho),
                            "absolute_difference": abs(float(rho) - float(per_language[language].spearman))}
    if any(row["absolute_difference"] > 1e-10 for row in parity.values()):
        raise ValueError("official evaluator parity failed")

    provenance_paths = [
        package / "subset-manifest.json", package / "validation" / "predictions.jsonl",
        package / "validation" / "summary.json", ledger, baseline_manifest,
        package.parent / "b2-projection-evidence" / "replay-final" / "report.md",
        package.parent / "b4-alignment-first-sdm" / "report.md",
        package.parent / "b4-alignment-first-sdm" / "oracle-20261013" / "results.json",
    ]
    provenance = {str(path): _sha_file(path) for path in provenance_paths}
    exposure = {
        "schema": SCHEMA,
        "selection_rule": "first two already-frozen validation_execution source groups in each short/medium/long stratum; no outcomes or gold used",
        "groups_per_stratum": SAMPLE_GROUPS_PER_STRATUM,
        "cases": [{"id": row["id"], "language": row["language"], "stratum": row["stratum"],
                   "group_key": row["group_key"], "status": "exposed by post-hoc error analysis; never again eligible as untouched validation"} for row in chosen],
    }
    summary = {
        "schema": SCHEMA,
        "mode": "offline replay of existing C1 development outputs; no inference; no test access",
        "sample": {"documents": len(chosen), "source_groups": 6,
                   "by_language": dict(Counter(row["language"] for row in chosen)),
                   "by_stratum": dict(Counter(row["stratum"] for row in chosen))},
        "category_document_incidence": dict(sorted(category_counts.items())),
        "category_by_stratum": {key: dict(value) for key, value in sorted(category_by_stratum.items())},
        "category_by_language": {key: dict(value) for key, value in sorted(category_by_language.items())},
        "format_failures": {"fatal_truncated_unparseable": fatal_truncations, "additional_item_level_malformed": item_malformed},
        "official_sample_score": {"macro": macro, "undefined_reason": reason,
                                  "per_language": {key: {"documents": value.documents, "positions": value.positions,
                                                          "masked": value.masked, "spearman": value.spearman,
                                                          "undefined_reason": value.undefined_reason} for key, value in per_language.items()}},
        "official_parity": parity,
        "implementation_defects_found": 0,
        "gate_a": "closed",
        "recommendation": "Bound response cardinality and require compact minimal evidence spans before considering any further semantic prompt expansion.",
        "provenance_sha256": provenance,
    }
    _write_new(public_out / "exposure-registry.json", exposure)
    _write_new(public_out / "case-traces.json", {"schema": SCHEMA, "cases": public_cases})
    _write_new(public_out / "summary.json", summary)
    _write_new(private_out / "private-case-traces.json", {"schema": SCHEMA, "cases": private_cases})
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--baseline-manifest", type=Path, required=True)
    parser.add_argument("--private-baseline", type=Path, required=True)
    parser.add_argument("--classifications", type=Path, required=True)
    parser.add_argument("--public-out", type=Path, required=True)
    parser.add_argument("--private-out", type=Path, required=True)
    parser.add_argument("--official-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(package=args.package, ledger=args.ledger, baseline_manifest=args.baseline_manifest,
                 private_baseline=args.private_baseline, classifications=args.classifications,
                 public_out=args.public_out, private_out=args.private_out, official_dir=args.official_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
