"""B5 competitive semantic alignment experiments.

Experiment A deliberately has two commands. ``freeze-a`` consumes only the
gold-free B4 evidence records and fixes official-token regions and their rank
before ``score-a`` is allowed to load development gold.  No command accepts a
split other than ``dev`` and output directories/files are never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path

from .b4 import FROZEN_MANIFEST_SHA256, _metrics, load_frozen_records
from .data_adapter import LANGUAGES, GoldLabels, InferenceInput
from .evaluation import evaluate_language
from .splits import assert_development_split

B5_SCHEMA = "uzh-rsd.b5/v1"
BASELINE_MACRO = 0.1871166580894296
GATE_A_DELTA = 0.020000
BUDGETS = (1, 3, 5, 10)
WINDOW_RADIUS = 2
RANDOM_SEED = "b5-a-random-control-v1"
POLICIES = ("suspicious_v1", "highest_anomaly_v1", "cue_first_v1", "random_v1")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, values: Sequence[Mapping]) -> None:
    path.write_text("".join(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n" for value in values), encoding="utf-8")


def _stable_unit(text: str) -> float:
    return int(hashlib.sha256(text.encode()).hexdigest(), 16) / (2**256 - 1)


def _lexical(token: str) -> str:
    return token.casefold().strip(".,;:!?()[]{}<>\"'«»“”/\\|_-–—")


def _cue(token: str, counts: Counter[str]) -> float:
    lexical = _lexical(token)
    if not lexical:
        return 0.0
    numeric = any(character.isdigit() for character in lexical)
    url = lexical.startswith(("http:", "https:", "www.")) or "@" in lexical
    repeated = counts[lexical] > 1 and len(lexical) >= 3
    return 1.0 if numeric or url or repeated else 0.0


def candidate_universe(record: Mapping) -> list[dict]:
    """Build fixed-radius original-token regions using no gold or counterpart data."""
    tokens = [str(token) for token in record["tokens"]]
    anomaly = [float(value) for value in record["anomaly_scores"]]
    if len(tokens) != len(anomaly) or any(not math.isfinite(value) for value in anomaly):
        raise ValueError(f"{record.get('id')}.{record.get('side')}: invalid B4 evidence")
    counts = Counter(filter(None, (_lexical(token) for token in tokens)))
    result = []
    for center, center_value in enumerate(anomaly):
        start, end = max(0, center - WINDOW_RADIUS), min(len(tokens), center + WINDOW_RADIUS + 1)
        region = anomaly[start:end]
        neighbors = anomaly[max(0, center - 1):center] + anomaly[center + 1:min(len(tokens), center + 2)]
        discontinuity = abs(center_value - statistics.fmean(neighbors)) if neighbors else 0.0
        cue_density = statistics.fmean(_cue(tokens[index], counts) for index in range(start, end))
        mean_anomaly = statistics.fmean(region)
        features = {
            "center_anomaly": center_value,
            "mean_anomaly": mean_anomaly,
            "local_discontinuity": discontinuity,
            "cue_density": cue_density,
        }
        result.append({
            "group_id": f"{record['id']}:{record['side']}:{start}:{end}:{center}",
            "side": record["side"], "start": start, "end": end, "center": center,
            "token_sha256": _sha256("\u241f".join(tokens[start:end]).encode()),
            "features": features,
        })
    return result


def _priority(candidate: Mapping, policy: str) -> tuple[float, str]:
    features = candidate["features"]
    if policy == "suspicious_v1":
        value = (0.55 * features["center_anomaly"] + 0.20 * features["mean_anomaly"]
                 + 0.15 * features["local_discontinuity"] + 0.10 * features["cue_density"])
    elif policy == "highest_anomaly_v1":
        value = features["center_anomaly"]
    elif policy == "cue_first_v1":
        value = features["cue_density"] + 0.01 * features["center_anomaly"]
    elif policy == "random_v1":
        value = _stable_unit(f"{RANDOM_SEED}|{candidate['group_id']}")
    else:
        raise ValueError(f"unknown policy {policy!r}")
    return value, str(candidate["group_id"])


def select_groups(universe: Sequence[Mapping], policy: str, budget: int) -> list[dict]:
    """Rank then greedily enforce non-overlap separately on each original side."""
    if budget not in BUDGETS:
        raise ValueError(f"unsupported budget {budget}")
    ordered = sorted(universe, key=lambda candidate: (-_priority(candidate, policy)[0], _priority(candidate, policy)[1]))
    selected: list[dict] = []
    occupied: dict[str, set[int]] = defaultdict(set)
    for candidate in ordered:
        positions = set(range(int(candidate["start"]), int(candidate["end"])))
        if positions & occupied[str(candidate["side"])]:
            continue
        row = dict(candidate)
        row["priority"] = _priority(candidate, policy)[0]
        row["rank"] = len(selected) + 1
        selected.append(row)
        occupied[str(candidate["side"])].update(positions)
        if len(selected) == budget:
            break
    if len(selected) != budget:
        raise ValueError(f"only {len(selected)} non-overlapping regions available for budget {budget}")
    return selected


def freeze_a(evidence_path: Path, out_path: Path, *, split: str = "dev") -> dict:
    """Freeze selections from B4's gold-free token evidence only."""
    assert_development_split(split)
    if out_path.exists():
        raise FileExistsError(f"refusing to overwrite frozen selector manifest {out_path}")
    raw = evidence_path.read_bytes()
    evidence = _jsonl(evidence_path)
    if len(evidence) != 60 or any(row.get("experiment") != "B" for row in evidence):
        raise ValueError("B5 A requires the 60 gold-free B4 side evidence records")
    by_id: dict[str, list[dict]] = defaultdict(list)
    for record in evidence:
        if record.get("counterpart_indices") is not None:
            raise ValueError("B4 evidence unexpectedly contains counterpart indices")
        by_id[str(record["id"])].extend(candidate_universe(record))
    if len(by_id) != 30:
        raise ValueError("B5 A requires exactly 30 documents")
    selections = []
    for record_id in sorted(by_id):
        for policy in POLICIES:
            maximum = select_groups(by_id[record_id], policy, max(BUDGETS))
            selections.append({"id": record_id, "policy": policy, "groups": maximum})
    manifest = {
        "schema": B5_SCHEMA, "experiment": "A", "stage": "gold_blind_selection_freeze",
        "split": split, "documents": len(by_id), "budgets": list(BUDGETS),
        "primary_policy": "suspicious_v1", "control_policies": list(POLICIES[1:]),
        "selector": {
            "version": "suspicious-regions-v1", "window_radius": WINDOW_RADIUS,
            "group": "five-token clipped window centred on an original official-token position",
            "non_overlap": "greedy after policy ranking, independently within each side",
            "suspicious_formula": "0.55*center_anomaly + 0.20*region_mean + 0.15*local_discontinuity + 0.10*cue_density",
            "cue": "digit, URL/email-like token, or repeated case-folded lexical token; only B4 tokens are used",
            "random_control": f"SHA-256 deterministic order seeded by {RANDOM_SEED}",
            "absent_fields_not_used": ["embedding", "similarity_matrix", "counterpart_index", "alignment_margin", "gold"],
        },
        "source": {"path": str(evidence_path), "sha256": _sha256(raw), "records": len(evidence)},
        "selections": selections,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(out_path, manifest)
    return manifest


def _selection_positions(groups: Sequence[Mapping], budget: int) -> dict[str, set[int]]:
    positions: dict[str, set[int]] = defaultdict(set)
    for group in groups[:budget]:
        positions[str(group["side"])].update(range(int(group["start"]), int(group["end"])))
    return positions


def _intervene(baseline: Mapping, gold: GoldLabels, positions: Mapping[str, set[int]]) -> dict[str, list[float]]:
    result = {"prediction_a": list(baseline["prediction_a"]), "prediction_b": list(baseline["prediction_b"])}
    for side, labels in (("a", gold.labels_a), ("b", gold.labels_b)):
        for index in positions.get(side, set()):
            if labels[index] != -1:
                result[f"prediction_{side}"][index] = float(labels[index])
    return result


def _metric_bundle(records: Sequence[tuple[InferenceInput, GoldLabels]], predictions: Mapping[str, Mapping]) -> dict:
    grouped: dict[str, list] = defaultdict(list)
    for item, gold in records:
        prediction = predictions[item.id]
        grouped[item.language].append((gold, prediction["prediction_a"], prediction["prediction_b"]))
    return _metrics(grouped)


def _percentile(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    point = (len(ordered) - 1) * q
    lower, upper = math.floor(point), math.ceil(point)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - point) + ordered[upper] * (point - lower)


def _cluster_key(record_id: str) -> str:
    return record_id.rsplit("_", 1)[1]


def _bootstrap(records: Sequence[tuple[InferenceInput, GoldLabels]], baseline: Mapping[str, Mapping],
               method: Mapping[str, Mapping], *, iterations: int = 1000) -> dict:
    clusters: dict[str, list] = defaultdict(list)
    for record in records:
        clusters[_cluster_key(record[0].id)].append(record)
    keys = sorted(clusters)
    rng = random.Random(20261013)
    deltas, macros = [], []
    for _ in range(iterations):
        sample = [key for key in (rng.choice(keys) for _ in keys)]
        sampled = [record for key in sample for record in clusters[key]]
        base_metric = _metric_bundle(sampled, baseline)["macro_spearman"]
        method_metric = _metric_bundle(sampled, method)["macro_spearman"]
        if base_metric is not None and method_metric is not None:
            macros.append(method_metric)
            deltas.append(method_metric - base_metric)
    return {
        "unit": "shared English document index across languages", "clusters": len(keys),
        "iterations_requested": iterations, "iterations_valid": len(deltas), "seed": 20261013,
        "macro_ci95": [_percentile(macros, 0.025), _percentile(macros, 0.975)],
        "delta_ci95": [_percentile(deltas, 0.025), _percentile(deltas, 0.975)],
    }


def _selection_quality(records: Sequence[tuple[InferenceInput, GoldLabels]], selections: Mapping[str, Mapping[str, set[int]]]) -> dict:
    selected = selected_positive = all_positive = all_positions = 0
    per_language = {language: {"selected": 0, "selected_positive": 0, "all_positive": 0, "all_positions": 0} for language in LANGUAGES}
    for item, gold in records:
        language = per_language[item.language]
        for side, labels in (("a", gold.labels_a), ("b", gold.labels_b)):
            chosen = selections[item.id].get(side, set())
            for index, label in enumerate(labels):
                if label == -1:
                    continue
                all_positions += 1
                language["all_positions"] += 1
                if label > 0:
                    all_positive += 1
                    language["all_positive"] += 1
                if index in chosen:
                    selected += 1
                    language["selected"] += 1
                    if label > 0:
                        selected_positive += 1
                        language["selected_positive"] += 1
    def finish(counts: Mapping[str, int]) -> dict:
        return {
            **counts,
            "reachable_gold_positive_fraction": counts["selected_positive"] / counts["all_positive"] if counts["all_positive"] else None,
            "selection_precision": counts["selected_positive"] / counts["selected"] if counts["selected"] else None,
            "token_coverage": counts["selected"] / counts["all_positions"] if counts["all_positions"] else None,
        }
    total = {"selected": selected, "selected_positive": selected_positive, "all_positive": all_positive, "all_positions": all_positions}
    return {"overall": finish(total), "per_language": {language: finish(counts) for language, counts in per_language.items()}}


def _sensitivity(records: Sequence[tuple[InferenceInput, GoldLabels]], baseline: Mapping[str, Mapping], method: Mapping[str, Mapping]) -> dict:
    full_delta = _metric_bundle(records, method)["macro_spearman"] - _metric_bundle(records, baseline)["macro_spearman"]
    leave_one = []
    per_document = []
    for item, gold in records:
        reduced = [record for record in records if record[0].id != item.id]
        reduced_delta = _metric_bundle(reduced, method)["macro_spearman"] - _metric_bundle(reduced, baseline)["macro_spearman"]
        base_rho = evaluate_language(item.language, [(gold, baseline[item.id]["prediction_a"], baseline[item.id]["prediction_b"])]).spearman
        method_rho = evaluate_language(item.language, [(gold, method[item.id]["prediction_a"], method[item.id]["prediction_b"])]).spearman
        leave_one.append({"id": item.id, "delta_without_document": reduced_delta, "influence": full_delta - reduced_delta})
        per_document.append({"id": item.id, "baseline_spearman": base_rho, "method_spearman": method_rho,
                             "delta": None if base_rho is None or method_rho is None else method_rho - base_rho})
    leave_one.sort(key=lambda row: abs(row["influence"]), reverse=True)
    return {"full_delta": full_delta, "leave_one_document_top_absolute_influence": leave_one[:10],
            "per_document": per_document}


def score_a(selector_path: Path, baseline_path: Path, frozen_manifest_path: Path, out_dir: Path,
            *, split: str = "dev") -> dict:
    """Join development gold only after validating the frozen selection manifest."""
    assert_development_split(split)
    if out_dir.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact directory {out_dir}")
    selector_bytes = selector_path.read_bytes()
    selector = json.loads(selector_bytes)
    if selector.get("stage") != "gold_blind_selection_freeze" or selector.get("split") != split:
        raise ValueError("invalid or non-development selector manifest")
    _source_manifest, records = load_frozen_records(frozen_manifest_path, split=split)
    baseline_rows = _jsonl(baseline_path)
    baseline = {row["id"]: row for row in baseline_rows}
    if set(baseline) != {item.id for item, _ in records}:
        raise ValueError("baseline does not exactly cover the frozen 30 documents")
    by_selection = {(row["id"], row["policy"]): row["groups"] for row in selector["selections"]}
    baseline_metrics = _metric_bundle(records, baseline)
    methods, prediction_rows = [], []
    for policy in POLICIES:
        for budget in BUDGETS:
            positions = {item.id: _selection_positions(by_selection[(item.id, policy)], budget) for item, _ in records}
            predictions = {item.id: _intervene(baseline[item.id], gold, positions[item.id]) for item, gold in records}
            metrics = _metric_bundle(records, predictions)
            macro = metrics["macro_spearman"]
            row = {
                "policy": policy, "budget_groups_per_document": budget, "coverage": "30/30",
                "metrics": metrics, "delta_over_unmodified": macro - baseline_metrics["macro_spearman"],
                "selection_quality": _selection_quality(records, positions),
                "bootstrap": _bootstrap(records, baseline, predictions),
                "document_sensitivity": _sensitivity(records, baseline, predictions),
            }
            methods.append(row)
            for item, _gold in records:
                prediction_rows.append({"schema": B5_SCHEMA, "experiment": "A", "policy": policy,
                                        "budget_groups_per_document": budget, "id": item.id,
                                        **predictions[item.id]})
    unrestricted = {}
    for item, gold in records:
        unrestricted[item.id] = {
            "prediction_a": [0.0 if value == -1 else float(value) for value in gold.labels_a],
            "prediction_b": [0.0 if value == -1 else float(value) for value in gold.labels_b],
        }
    unrestricted_metrics = _metric_bundle(records, unrestricted)
    primary = [row for row in methods if row["policy"] == "suspicious_v1"]
    passing = [row for row in primary if row["delta_over_unmodified"] >= GATE_A_DELTA]
    selected = min(passing, key=lambda row: row["budget_groups_per_document"]) if passing else max(primary, key=lambda row: row["delta_over_unmodified"])
    result = {
        "schema": B5_SCHEMA, "experiment": "A", "split": split, "coverage": "30/30",
        "selector_manifest": {"path": str(selector_path), "sha256": _sha256(selector_bytes), "frozen_before_gold_scoring": True},
        "frozen_sample_sha256": FROZEN_MANIFEST_SHA256,
        "baseline": {"name": "unmodified B4 DiffAlign", "metrics": baseline_metrics},
        "finite_action_set": {
            "definition": "replace B4 scores by permitted dev gold only at official-token positions in pre-frozen selected regions",
            "methods": methods,
        },
        "unrestricted_gold_replacement_ceiling": {
            "definition": "replace every unmasked official-token score with gold; not part of the finite action set",
            "metrics": unrestricted_metrics,
        },
        "gate_a": {
            "threshold_absolute_delta": GATE_A_DELTA,
            "predeclared_primary_policy": "suspicious_v1",
            "selected_condition": {"policy": selected["policy"], "budget_groups_per_document": selected["budget_groups_per_document"],
                                   "macro_spearman": selected["metrics"]["macro_spearman"],
                                   "delta": selected["delta_over_unmodified"], "bootstrap": selected["bootstrap"]},
            "passes": bool(passing),
        },
        "leakage_checks": [
            "selector input is B4 evidence.jsonl containing tokens and scalar anomaly scores but no gold",
            "selector rejects any non-null counterpart_indices and declares unavailable fields unused",
            "candidate positions and all policy rankings were frozen in the hashed selector manifest before score-a loaded gold",
            "gold enters only score-a interventions and evaluation; oracle predictions are diagnostic and not deployable",
        ],
    }
    out_dir.mkdir(parents=True)
    _write_jsonl(out_dir / "interventions.jsonl", prediction_rows)
    _write_json(out_dir / "results.json", result)
    _write_json(out_dir / "checksums.json", {
        "interventions.jsonl": _sha256((out_dir / "interventions.jsonl").read_bytes()),
        "results.json": _sha256((out_dir / "results.json").read_bytes()),
        "selector_manifest": _sha256(selector_bytes),
        "baseline_predictions": _sha256(baseline_path.read_bytes()),
    })
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze-a")
    freeze.add_argument("--evidence", type=Path, required=True)
    freeze.add_argument("--out", type=Path, required=True)
    freeze.add_argument("--split", default="dev")
    score = commands.add_parser("score-a")
    score.add_argument("--selector", type=Path, required=True)
    score.add_argument("--baseline", type=Path, required=True)
    score.add_argument("--manifest", type=Path, required=True)
    score.add_argument("--out", type=Path, required=True)
    score.add_argument("--split", default="dev")
    args = parser.parse_args(argv)
    if args.command == "freeze-a":
        result = freeze_a(args.evidence, args.out, split=args.split)
    else:
        result = score_a(args.selector, args.baseline, args.manifest, args.out, split=args.split)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
