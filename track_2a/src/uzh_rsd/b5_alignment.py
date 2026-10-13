"""B5 Experiment B: regenerate one embedding cache and compare frozen matchers."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import random
import statistics
import time
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path

from .b4 import _metrics, average_precision, load_frozen_records
from .splits import assert_development_split

B5_ALIGNMENT_SCHEMA = "uzh-rsd.b5-alignment/v1"
MODEL_ID = "Qwen/Qwen3-Embedding-4B"
MODEL_REVISION = "5cf2132abc99cad020ac570b19d031efec650f2b"
MODEL_LAYER = 20
NULL_THRESHOLD = 0.35
GAP_OPEN = -0.20
GAP_EXTEND = -0.05
METHODS = ("M0", "M1", "M2", "M3")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, values: Sequence[Mapping]) -> None:
    path.write_text("".join(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n" for value in values), encoding="utf-8")


def _model_files(model_dir: Path) -> dict[str, str]:
    required = ("config.json", "tokenizer.json", "tokenizer_config.json", "model.safetensors.index.json",
                "model-00001-of-00002.safetensors", "model-00002-of-00002.safetensors")
    missing = [name for name in required if not (model_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"model cache incomplete: {missing}")
    return {name: _sha256((model_dir / name).read_bytes()) for name in required}


def _gold_free_documents(evidence_path: Path) -> list[dict]:
    rows = _jsonl(evidence_path)
    if len(rows) != 60 or any(row.get("experiment") != "B" or row.get("counterpart_indices") is not None for row in rows):
        raise ValueError("encoding requires the 60 gold-free B4 evidence sides with absent counterpart indices")
    documents: dict[str, dict] = defaultdict(dict)
    for row in rows:
        documents[row["id"]][row["side"]] = list(row["tokens"])
    if len(documents) != 30 or any(set(sides) != {"a", "b"} for sides in documents.values()):
        raise ValueError("encoding requires 30 complete documents")
    return [{"id": record_id, "tokens_a": sides["a"], "tokens_b": sides["b"]} for record_id, sides in sorted(documents.items())]


def official_word_ids(tokens: Sequence[str], offsets: Sequence[Sequence[int]]) -> list[int]:
    """Map model offsets onto the exact whitespace tokens joined for encoding."""
    spans = []
    cursor = 0
    for token in tokens:
        spans.append((cursor, cursor + len(token)))
        cursor += len(token) + 1
    result = []
    for raw_start, raw_end in offsets:
        start, end = int(raw_start), int(raw_end)
        if end <= start:
            result.append(-1)
            continue
        overlaps = [max(0, min(end, token_end) - max(start, token_start)) for token_start, token_end in spans]
        best = max(overlaps, default=0)
        result.append(overlaps.index(best) if best > 0 else -1)
    if set(value for value in result if value >= 0) != set(range(len(tokens))):
        raise ValueError("tokenizer offsets do not cover every official whitespace token")
    return result


def encode_b(evidence_path: Path, model_dir: Path, cache_dir: Path, provenance_path: Path,
             *, split: str = "dev") -> dict:
    """Encode gold-free B4 tokens once on XPU and persist matrices outside VCS."""
    assert_development_split(split)
    if cache_dir.exists() or provenance_path.exists():
        raise FileExistsError("B5 embedding cache/provenance never overwrites")
    import numpy as np
    import torch
    import transformers
    from transformers import AutoModel, AutoTokenizer

    if not torch.xpu.is_available():
        raise RuntimeError("pinned local XPU route is unavailable")
    files = _model_files(model_dir)
    documents = _gold_free_documents(evidence_path)
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
    model = AutoModel.from_pretrained(model_dir, local_files_only=True, torch_dtype=torch.bfloat16)
    model.eval().to("xpu")
    cache_dir.mkdir(parents=True)
    started = time.monotonic()
    records = []
    with torch.inference_mode():
        for position, document in enumerate(documents, 1):
            encoded_sides = []
            for side in ("a", "b"):
                text = " ".join(document[f"tokens_{side}"])
                inputs = tokenizer(text, return_tensors="pt", truncation=False, return_offsets_mapping=True)
                offsets = inputs.pop("offset_mapping")
                word_ids = official_word_ids(document[f"tokens_{side}"], offsets[0].tolist())
                device_inputs = {key: value.to("xpu") for key, value in inputs.items()}
                output = model(**device_inputs, output_hidden_states=True)
                embedding = output.hidden_states[MODEL_LAYER][0].float()
                embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)
                encoded_sides.append((embedding, np.asarray(word_ids, dtype=np.int32),
                                      offsets[0].numpy().astype(np.int32)))
            similarity = torch.clamp(encoded_sides[0][0] @ encoded_sides[1][0].T, min=0, max=1).cpu().numpy().astype(np.float32)
            target = cache_dir / f"{document['id']}.npz"
            np.savez_compressed(target, similarity=similarity, word_ids_a=encoded_sides[0][1], word_ids_b=encoded_sides[1][1],
                                offsets_a=encoded_sides[0][2], offsets_b=encoded_sides[1][2])
            records.append({"id": document["id"], "path": target.name, "sha256": _sha256(target.read_bytes()),
                            "shape": list(similarity.shape), "official_tokens_a": len(document["tokens_a"]),
                            "official_tokens_b": len(document["tokens_b"])})
            print(f"encoded {position}/30 {document['id']} {similarity.shape}", flush=True)
    result = {
        "schema": B5_ALIGNMENT_SCHEMA, "stage": "embedding_regeneration", "split": split,
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION, "layer": MODEL_LAYER, "files": files},
        "software": {"python": __import__("sys").version, "torch": torch.__version__, "transformers": transformers.__version__,
                     "device": torch.xpu.get_device_name(0)},
        "source": {"path": str(evidence_path), "sha256": _sha256(evidence_path.read_bytes()), "gold_fields": False},
        "records": records, "coverage": "30/30", "wall_s": time.monotonic() - started,
        "cache_bytes": sum((cache_dir / row["path"]).stat().st_size for row in records),
    }
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(provenance_path, result)
    return result


def _top_two(matrix, axis: int):
    import numpy as np
    if matrix.shape[axis] == 1:
        best = np.max(matrix, axis=axis)
        return best, np.zeros_like(best)
    partition = np.partition(matrix, -2, axis=axis)
    best = np.take(partition, -1, axis=axis)
    second = np.take(partition, -2, axis=axis)
    return best, second


def match_m0(similarity):
    import numpy as np
    best_a = np.argmax(similarity, axis=1)
    best_b = np.argmax(similarity, axis=0)
    return 1 - similarity[np.arange(similarity.shape[0]), best_a], 1 - similarity[best_b, np.arange(similarity.shape[1])], best_a, best_b


def match_m1(similarity):
    import numpy as np
    best_a = np.argmax(similarity, axis=1)
    best_b = np.argmax(similarity, axis=0)
    top_a, second_a = _top_two(similarity, 1)
    top_b, second_b = _top_two(similarity, 0)
    mutual_a = (best_b[best_a] == np.arange(similarity.shape[0])).astype(float)
    mutual_b = (best_a[best_b] == np.arange(similarity.shape[1])).astype(float)
    confidence_a = top_a * (0.75 + 0.25 * mutual_a) * (0.75 + 0.25 * (top_a - second_a))
    confidence_b = top_b * (0.75 + 0.25 * mutual_b) * (0.75 + 0.25 * (top_b - second_b))
    return 1 - confidence_a, 1 - confidence_b, best_a, best_b


def match_m2(similarity):
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    n, m = similarity.shape
    weights = np.full((n + m, n + m), -1e6, dtype=np.float32)
    weights[:n, :m] = similarity
    weights[np.arange(n), m + np.arange(n)] = NULL_THRESHOLD
    weights[n + np.arange(m), np.arange(m)] = NULL_THRESHOLD
    weights[n:, m:] = 0.0
    rows, columns = linear_sum_assignment(weights, maximize=True)
    counterpart_a = np.full(n, -1, dtype=np.int32)
    counterpart_b = np.full(m, -1, dtype=np.int32)
    for row, column in zip(rows, columns):
        if row < n and column < m:
            counterpart_a[row] = column
            counterpart_b[column] = row
    anomaly_a = np.ones(n, dtype=np.float32)
    anomaly_b = np.ones(m, dtype=np.float32)
    matched_a = np.flatnonzero(counterpart_a >= 0)
    matched_b = np.flatnonzero(counterpart_b >= 0)
    anomaly_a[matched_a] = 1 - similarity[matched_a, counterpart_a[matched_a]]
    anomaly_b[matched_b] = 1 - similarity[counterpart_b[matched_b], matched_b]
    return anomaly_a, anomaly_b, counterpart_a, counterpart_b


def match_m3(similarity):
    """One Smith-Waterman local alignment with affine gaps and explicit NULLs."""
    import numpy as np
    n, m = similarity.shape
    h = np.zeros((n + 1, m + 1), dtype=np.float32)
    e = np.full_like(h, -np.inf)
    f = np.full_like(h, -np.inf)
    trace = np.zeros((n + 1, m + 1), dtype=np.uint8)
    best_value, best_position = 0.0, (0, 0)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            e[i, j] = max(h[i - 1, j] + GAP_OPEN, e[i - 1, j] + GAP_EXTEND)
            f[i, j] = max(h[i, j - 1] + GAP_OPEN, f[i, j - 1] + GAP_EXTEND)
            diagonal = h[i - 1, j - 1] + similarity[i - 1, j - 1] - NULL_THRESHOLD
            choices = (0.0, diagonal, e[i, j], f[i, j])
            state = max(range(4), key=choices.__getitem__)
            h[i, j] = choices[state]
            trace[i, j] = state
            if h[i, j] > best_value:
                best_value, best_position = float(h[i, j]), (i, j)
    counterpart_a = np.full(n, -1, dtype=np.int32)
    counterpart_b = np.full(m, -1, dtype=np.int32)
    i, j = best_position
    while i > 0 and j > 0 and h[i, j] > 0:
        state = int(trace[i, j])
        if state == 1:
            counterpart_a[i - 1], counterpart_b[j - 1] = j - 1, i - 1
            i, j = i - 1, j - 1
        elif state == 2:
            i -= 1
        elif state == 3:
            j -= 1
        else:
            break
    anomaly_a = np.ones(n, dtype=np.float32)
    anomaly_b = np.ones(m, dtype=np.float32)
    matched_a = np.flatnonzero(counterpart_a >= 0)
    matched_b = np.flatnonzero(counterpart_b >= 0)
    anomaly_a[matched_a] = 1 - similarity[matched_a, counterpart_a[matched_a]]
    anomaly_b[matched_b] = 1 - similarity[counterpart_b[matched_b], matched_b]
    return anomaly_a, anomaly_b, counterpart_a, counterpart_b


MATCHERS = {"M0": match_m0, "M1": match_m1, "M2": match_m2, "M3": match_m3}


def _project(values, word_ids, token_count: int) -> list[float]:
    grouped = [[] for _ in range(token_count)]
    for value, word_id in zip(values, word_ids):
        if int(word_id) >= 0:
            grouped[int(word_id)].append(float(value))
    if any(not group for group in grouped):
        raise ValueError("subword map does not cover every official token")
    result = [sum(group) / len(group) for group in grouped]
    if any(not math.isfinite(value) for value in result):
        raise ValueError("projection produced a non-finite score")
    return result


def _official_counterparts(counterpart, source_word_ids, target_word_ids, token_count: int) -> list[int]:
    votes = [[] for _ in range(token_count)]
    for source_subword, target_subword in enumerate(counterpart):
        source_word = int(source_word_ids[source_subword])
        if source_word < 0:
            continue
        target_word = -1 if int(target_subword) < 0 else int(target_word_ids[int(target_subword)])
        votes[source_word].append(target_word)
    result = []
    for values in votes:
        non_null = [value for value in values if value >= 0]
        result.append(Counter(non_null).most_common(1)[0][0] if non_null else -1)
    return result


def _numeric_diagnostics(tokens: Sequence[str], target_tokens: Sequence[str], counterparts: Sequence[int]) -> dict:
    numeric = [index for index, token in enumerate(tokens) if any(character.isdigit() for character in token)]
    exact = mismatch = null = 0
    for index in numeric:
        counterpart = counterparts[index]
        if counterpart < 0:
            null += 1
        elif tokens[index].casefold() == target_tokens[counterpart].casefold():
            exact += 1
        else:
            mismatch += 1
    return {"numeric_tokens": len(numeric), "exact_numeric_counterpart": exact,
            "different_or_nonnumeric_counterpart": mismatch, "null_counterpart": null}


def _bootstrap(records, reference: Mapping[str, Mapping], method: Mapping[str, Mapping], *, iterations: int = 500) -> dict:
    import numpy as np
    from scipy.stats import rankdata
    from .evaluation import assemble

    parts: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for item, gold in records:
        ref, gold_values, _ = assemble([(gold, reference[item.id]["prediction_a"], reference[item.id]["prediction_b"])])
        candidate, candidate_gold, _ = assemble([(gold, method[item.id]["prediction_a"], method[item.id]["prediction_b"])])
        if gold_values != candidate_gold:
            raise ValueError("bootstrap denominator changed")
        parts[item.id.rsplit("_", 1)[1]][item.language].append((ref, candidate, gold_values))
    keys = sorted(parts)
    rng = random.Random(20261013)
    macros, deltas = [], []

    def macro(sample, field):
        correlations = []
        for language in ("de", "fr", "it"):
            rows = [row for key in sample for row in parts[key].get(language, [])]
            if not rows:
                return None
            prediction = np.concatenate([np.asarray(row[field], dtype=float) for row in rows])
            gold = np.concatenate([np.asarray(row[2], dtype=float) for row in rows])
            value = float(np.corrcoef(rankdata(prediction), rankdata(gold))[0, 1])
            if not math.isfinite(value):
                return None
            correlations.append(value)
        return statistics.fmean(correlations)

    for _ in range(iterations):
        sample = [rng.choice(keys) for _key in keys]
        ref_macro, method_macro = macro(sample, 0), macro(sample, 1)
        if ref_macro is not None and method_macro is not None:
            macros.append(method_macro)
            deltas.append(method_macro - ref_macro)
    def percentile(values, quantile):
        ordered = sorted(values)
        point = (len(ordered) - 1) * quantile
        lower, upper = math.floor(point), math.ceil(point)
        return ordered[lower] if lower == upper else ordered[lower] * (upper - point) + ordered[upper] * (point - lower)
    return {"unit": "shared English document index", "clusters": len(keys), "seed": 20261013,
            "iterations_requested": iterations, "iterations_valid": len(deltas),
            "macro_ci95": [percentile(macros, 0.025), percentile(macros, 0.975)],
            "delta_ci95": [percentile(deltas, 0.025), percentile(deltas, 0.975)]}


def score_b(cache_dir: Path, cache_provenance_path: Path, evidence_path: Path, baseline_path: Path,
            a_interventions_path: Path,
            frozen_manifest_path: Path, out_dir: Path, *, split: str = "dev") -> dict:
    assert_development_split(split)
    if out_dir.exists():
        raise FileExistsError("B5 B artifact directory never overwrites")
    import numpy as np
    cache_provenance = json.loads(cache_provenance_path.read_text(encoding="utf-8"))
    if cache_provenance.get("coverage") != "30/30" or cache_provenance.get("model", {}).get("revision") != MODEL_REVISION:
        raise ValueError("embedding cache provenance is incomplete or not pinned")
    evidence_rows = _jsonl(evidence_path)
    token_lookup = {(row["id"], row["side"]): row["tokens"] for row in evidence_rows}
    _manifest, records = load_frozen_records(frozen_manifest_path, split=split)
    baseline = {row["id"]: row for row in _jsonl(baseline_path)}
    selected_a = {row["id"]: row for row in _jsonl(a_interventions_path)
                  if row.get("policy") == "suspicious_v1" and row.get("budget_groups_per_document") == 5}
    if set(selected_a) != set(baseline):
        raise ValueError("selected A baseline does not exactly cover the frozen 30 documents")
    predictions_by_method: dict[str, dict] = {method: {} for method in METHODS}
    diagnostics_by_method: dict[str, list] = {method: [] for method in METHODS}
    alignment_rows, runtime = [], {}
    usage_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    for method in METHODS:
        started = time.monotonic()
        for item, _gold in records:
            cache_path = cache_dir / f"{item.id}.npz"
            with np.load(cache_path) as cached:
                similarity = cached["similarity"]
                word_ids_a, word_ids_b = cached["word_ids_a"], cached["word_ids_b"]
            anomaly_a, anomaly_b, counterpart_a, counterpart_b = MATCHERS[method](similarity)
            official_a = _project(anomaly_a, word_ids_a, len(item.text_a.tokens))
            official_b = _project(anomaly_b, word_ids_b, len(item.text_b.tokens))
            links_a = _official_counterparts(counterpart_a, word_ids_a, word_ids_b, len(item.text_a.tokens))
            links_b = _official_counterparts(counterpart_b, word_ids_b, word_ids_a, len(item.text_b.tokens))
            predictions_by_method[method][item.id] = {"prediction_a": official_a, "prediction_b": official_b}
            used = [value for value in counterpart_a if value >= 0]
            duplicate_reuse = len(used) - len(set(map(int, used)))
            diag = {"id": item.id, "null_subwords_a": int(np.sum(counterpart_a < 0)),
                    "null_subwords_b": int(np.sum(counterpart_b < 0)), "duplicate_target_reuse_subwords": duplicate_reuse,
                    "numeric_a": _numeric_diagnostics(item.text_a.tokens, item.text_b.tokens, links_a),
                    "numeric_b": _numeric_diagnostics(item.text_b.tokens, item.text_a.tokens, links_b)}
            diagnostics_by_method[method].append(diag)
            alignment_rows.append({"schema": B5_ALIGNMENT_SCHEMA, "method": method, "id": item.id,
                                   "counterpart_a": links_a, "counterpart_b": links_b,
                                   "prediction_a": official_a, "prediction_b": official_b})
        runtime[method] = time.monotonic() - started
    results = []
    gold_lookup = {item.id: gold for item, gold in records}
    for method in METHODS:
        grouped: dict[str, list] = defaultdict(list)
        positives_detected = positives = 0
        for item, gold in records:
            prediction = predictions_by_method[method][item.id]
            grouped[item.language].append((gold, prediction["prediction_a"], prediction["prediction_b"]))
            for labels, values in ((gold.labels_a, prediction["prediction_a"]), (gold.labels_b, prediction["prediction_b"])):
                for label, value in zip(labels, values):
                    if label > 0:
                        positives += 1
                        positives_detected += value >= 0.5
        metrics = _metrics(grouped)
        nulls = sum(row["null_subwords_a"] + row["null_subwords_b"] for row in diagnostics_by_method[method])
        duplicates = sum(row["duplicate_target_reuse_subwords"] for row in diagnostics_by_method[method])
        results.append({"method": method, "coverage": "30/30", "metrics": metrics,
                        "runtime_s": runtime[method], "null_subwords": nulls,
                        "duplicate_target_reuse_subwords": duplicates,
                        "gold_positive_detection_at_0.5": positives_detected / positives,
                        "diagnostics": diagnostics_by_method[method]})
    m0 = predictions_by_method["M0"]
    differences = [abs(value - published)
                   for item, _gold in records
                   for side in ("a", "b")
                   for value, published in zip(m0[item.id][f"prediction_{side}"], baseline[item.id][f"prediction_{side}"])]
    m0_agreement = {"maximum_absolute_difference": max(differences),
                    "mean_absolute_difference": sum(differences) / len(differences),
                    "within_published_5_decimal_rounding": max(differences) <= 0.0000051}
    b4_macro = 0.1871166580894296
    a_macro = 0.20927113161193936
    competitive = [row for row in results if row["method"] != "M0"]
    best = max(competitive, key=lambda row: row["metrics"]["macro_spearman"])
    uncertainty_vs_b4 = _bootstrap(records, baseline, predictions_by_method[best["method"]])
    uncertainty_vs_a = _bootstrap(records, selected_a, predictions_by_method[best["method"]])
    passes = (best["metrics"]["macro_spearman"] >= b4_macro + 0.005 and
              best["metrics"]["macro_spearman"] >= a_macro + 0.005 and best["coverage"] == "30/30")
    output = {
        "schema": B5_ALIGNMENT_SCHEMA, "experiment": "B", "split": split, "coverage": "30/30",
        "inputs": {"cache_provenance": {"path": str(cache_provenance_path), "sha256": _sha256(cache_provenance_path.read_bytes())},
                   "same_regenerated_similarity_matrices": True},
        "methods": results, "m0_published_b4_agreement": m0_agreement,
        "resources": {"matcher_wall_s": sum(runtime.values()), "max_rss_kib": max(usage_before, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)},
        "gate_b": {"useful_delta": 0.005, "best_method": best["method"],
                   "best_macro": best["metrics"]["macro_spearman"],
                   "delta_over_unmodified_b4": best["metrics"]["macro_spearman"] - b4_macro,
                   "delta_over_selected_a_baseline": best["metrics"]["macro_spearman"] - a_macro,
                   "uncertainty_vs_unmodified_b4": uncertainty_vs_b4,
                   "uncertainty_vs_selected_a": uncertainty_vs_a,
                   "passes": passes},
        "scientific_comparability": "direct to published B4 only if M0 agrees within its five-decimal publication rounding; M0-M3 always share this regenerated cache",
    }
    out_dir.mkdir(parents=True)
    _write_jsonl(out_dir / "alignments-and-predictions.jsonl", alignment_rows)
    _write_json(out_dir / "results.json", output)
    _write_json(out_dir / "checksums.json", {
        "alignments-and-predictions.jsonl": _sha256((out_dir / "alignments-and-predictions.jsonl").read_bytes()),
        "results.json": _sha256((out_dir / "results.json").read_bytes()),
        "cache_provenance": _sha256(cache_provenance_path.read_bytes()),
    })
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    encode = commands.add_parser("encode-b")
    encode.add_argument("--evidence", type=Path, required=True)
    encode.add_argument("--model", type=Path, required=True)
    encode.add_argument("--cache", type=Path, required=True)
    encode.add_argument("--provenance", type=Path, required=True)
    encode.add_argument("--split", default="dev")
    score = commands.add_parser("score-b")
    score.add_argument("--cache", type=Path, required=True)
    score.add_argument("--cache-provenance", type=Path, required=True)
    score.add_argument("--evidence", type=Path, required=True)
    score.add_argument("--baseline", type=Path, required=True)
    score.add_argument("--a-interventions", type=Path, required=True)
    score.add_argument("--manifest", type=Path, required=True)
    score.add_argument("--out", type=Path, required=True)
    score.add_argument("--split", default="dev")
    args = parser.parse_args(argv)
    if args.command == "encode-b":
        result = encode_b(args.evidence, args.model, args.cache, args.provenance, split=args.split)
    else:
        result = score_b(args.cache, args.cache_provenance, args.evidence, args.baseline,
                         args.a_interventions, args.manifest, args.out, split=args.split)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
