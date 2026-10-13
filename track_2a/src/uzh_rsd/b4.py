"""B4 Alignment-First SDM: frozen oracle and alignment-only experiments.

Experiment A is explicitly gold-derived and diagnostic-only.  Experiment B
replays the MIT-licensed DiffAlign continuous predictions published by
ZurichNLP at a pinned commit, filters them to the frozen B2/B3 30-document
development sample, and scores them with the local official-parity evaluator.

No entry point in this module accepts the test split.  B prediction records are
constructed from :class:`InferenceInput` plus pinned upstream scores; gold is
joined only inside the scoring function.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import resource
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from .data_adapter import DEFAULT_DATA_DIR, LANGUAGES, GoldLabels, InferenceInput
from .evaluation import OFFICIAL_COMMIT, OFFICIAL_FILES, assemble, evaluate_language, macro_average
from .runner import manifest_records
from .sdm.pipeline import segment as passage_segment
from .splits import assert_development_split
from .tokens import check_vector

B4_SCHEMA = "uzh-rsd.b4/v1"
FROZEN_MANIFEST_SHA256 = "523306bece722e61436b93760d10820fa541eab10c1858215d0c4c6873eca4c5"
UPSTREAM_REPO = "ZurichNLP/document-level-word-alignment"
UPSTREAM_COMMIT = "60ad0a32bbceb5570ed8440f6bc7a2f470a04c25"
UPSTREAM_LICENSE = "MIT"
UPSTREAM_FILES = {
    "de": ("DiffAlign(model=Qwen_Qwen3-Embedding-4B, layer=20_admin_de.jsonl.jsonl",
           "749d556ff7baa240085320bdffdbea04b2596348362a53dc4b82741df454c6c8"),
    "fr": ("DiffAlign(model=Qwen_Qwen3-Embedding-4B, layer=20_admin_fr.jsonl.jsonl",
           "7e3a39735c956c2ebd178e861873c5e3ffb244cb25ca9b56f8483b619939309e"),
    "it": ("DiffAlign(model=Qwen_Qwen3-Embedding-4B, layer=20_admin_it.jsonl.jsonl",
           "c4212b840e018c22eb1f4c45a3ca41fab03b04a7726fab2a4cc015ad19765503"),
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, values: Sequence[Mapping]) -> None:
    path.write_text("".join(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n" for value in values), encoding="utf-8")


def load_frozen_records(manifest_path: Path, *, split: str = "dev", data_dir: Path = DEFAULT_DATA_DIR) -> tuple[dict, list[tuple[InferenceInput, GoldLabels]]]:
    """Load exactly the frozen 30 IDs and verify text and gold fingerprints."""
    assert_development_split(split)
    raw = Path(manifest_path).read_bytes()
    if _sha256(raw) != FROZEN_MANIFEST_SHA256:
        raise ValueError("B4 requires the byte-identical frozen B2 manifest")
    manifest = json.loads(raw)
    if manifest.get("split") != split or manifest.get("counts") != {"en-de": 10, "en-fr": 10, "en-it": 10}:
        raise ValueError("B4 requires the frozen 30-ID development sample")
    records = manifest_records(manifest, data_dir=data_dir)
    if len(records) != 30 or len({item.id for item, _ in records}) != 30:
        raise ValueError("frozen sample must contain 30 unique documents")
    entries = {entry["id"]: entry for entry in manifest["entries"]}
    for item, gold in records:
        digest = _sha256(json.dumps([gold.labels_a, gold.labels_b]).encode())
        if digest != entries[item.id]["gold_sha256"]:
            raise ValueError(f"{item.id}: gold differs from frozen manifest")
    return manifest, records


def sentence_segments(tokens: Sequence[str]) -> list[tuple[int, int]]:
    """Deterministic sentence boundaries without splitting URL/decimal tokens."""
    if not tokens:
        return []
    result: list[tuple[int, int]] = []
    start = 0
    closers = "\"'»”)]}"
    for index, token in enumerate(tokens, 1):
        core = token.rstrip(closers)
        lower = core.casefold()
        is_url = lower.startswith(("http://", "https://", "www."))
        boundary = (core in {".", "!", "?", "…", ";"} or
                    (len(core) > 1 and core[-1:] in {"!", "?", "…"}))
        if boundary and not is_url:
            result.append((start, index))
            start = index
    if start < len(tokens):
        result.append((start, len(tokens)))
    return result


def diffalign_scores(similarities: Sequence[Sequence[float]]) -> tuple[list[float], list[float]]:
    """Reference DiffAlign reduction from a cross-lingual similarity matrix.

    This dependency-free form makes the alignment contract testable.  Rows and
    columns may be permuted without changing the corresponding token scores;
    an empty counterpart is explicitly maximally anomalous rather than silently
    equivalent.
    """
    rows = [list(row) for row in similarities]
    if not rows:
        return [], []
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("similarity matrix must be rectangular")
    if width == 0:
        return [1.0] * len(rows), []
    checked = []
    for row in rows:
        values = []
        for value in row:
            number = float(value)
            if not math.isfinite(number):
                raise ValueError("similarity matrix contains a non-finite value")
            values.append(min(1.0, max(0.0, number)))
        checked.append(values)
    left = [1.0 - max(row) for row in checked]
    right = [1.0 - max(checked[row][column] for row in range(len(checked))) for column in range(width)]
    return left, right


def _positive_spans(labels: Sequence[float]) -> list[tuple[int, int, float]]:
    spans: list[tuple[int, int, float]] = []
    start: int | None = None
    for index in range(len(labels) + 1):
        positive = index < len(labels) and labels[index] > 0
        if positive and start is None:
            start = index
        elif not positive and start is not None:
            spans.append((start, index, max(labels[start:index])))
            start = None
    return spans


def _clean_gold(labels: Sequence[float]) -> list[float]:
    return [0.0 if value == -1 else float(value) for value in labels]


def oracle_vector(name: str, tokens: Sequence[str], labels: Sequence[float]) -> list[float]:
    """Create one predeclared oracle representation; never used by B."""
    gold = _clean_gold(labels)
    if name == "A0_exact_gold":
        return gold
    if name == "A1_binary_locations":
        return [float(value > 0) for value in gold]
    if name == "A2_three_severity_buckets":
        return [0.0 if value == 0 else (1 / 3 if value <= 0.4 else 2 / 3 if value <= 0.6 else 1.0) for value in gold]
    if name in {"A3_sentence_max", "A4_passage_max"}:
        groups = (sentence_segments(tokens) if name.startswith("A3") else
                  [(part.start_token, part.end_token) for part in passage_segment(tokens)])
        result = [0.0] * len(gold)
        for start, end in groups:
            value = max(gold[start:end], default=0.0)
            result[start:end] = [value] * (end - start)
        return result
    if name.startswith("A5_expand_"):
        width = int(name.rsplit("_", 1)[1])
        result = list(gold)
        for start, end, severity in _positive_spans(gold):
            for index in range(max(0, start - width), min(len(gold), end + width)):
                result[index] = max(result[index], severity)
        return result
    if name.startswith("A6_contract_"):
        width = int(name.rsplit("_", 1)[1])
        result = [0.0] * len(gold)
        for start, end, _severity in _positive_spans(gold):
            inner_start, inner_end = start + width, end - width
            if inner_start < inner_end:
                result[inner_start:inner_end] = gold[inner_start:inner_end]
        return result
    if name == "A7_soft_boundary_decay":
        result = list(gold)
        for start, end, severity in _positive_spans(gold):
            for distance in range(1, 6):
                value = severity * math.exp(-distance / 2)
                for index in (start - distance, end - 1 + distance):
                    if 0 <= index < len(result):
                        result[index] = max(result[index], value)
        return result
    if name == "A8_continuous_token_attribution":
        result = []
        for token, severity in zip(tokens, gold, strict=True):
            if severity == 0:
                result.append(0.0)
                continue
            lowered = token.casefold()
            numeric = any(character.isdigit() for character in token)
            url = lowered.startswith(("http://", "https://", "www."))
            lexical = min(1.0, 0.55 + len(token.strip(".,;:!?()[]{}\"'")) / 20)
            salience = 1.0 if numeric or url else 0.9 if token[:1].isupper() else lexical
            result.append(severity * salience)
        return result
    raise ValueError(f"unknown oracle variant {name!r}")


ORACLE_VARIANTS = (
    ("A0_exact_gold", "token", "exact permitted dev gold; evaluator sanity check"),
    ("A1_binary_locations", "token", "exact positive locations; binary severity"),
    ("A2_three_severity_buckets", "token", "exact locations; low/mid/high buckets"),
    ("A3_sentence_max", "sentence", "maximum severity broadcast within deterministic sentence"),
    ("A4_passage_max", "passage<=8", "maximum severity broadcast within frozen B3 passages"),
    ("A5_expand_1", "span+1", "positive spans expanded one token per boundary"),
    ("A5_expand_3", "span+3", "positive spans expanded three tokens per boundary"),
    ("A5_expand_5", "span+5", "positive spans expanded five tokens per boundary"),
    ("A6_contract_1", "span-1", "positive spans contracted one token per boundary"),
    ("A6_contract_3", "span-3", "positive spans contracted three tokens per boundary"),
    ("A7_soft_boundary_decay", "soft span", "five-token exponential boundary decay"),
    ("A8_continuous_token_attribution", "token", "gold severity modulated by deterministic token salience"),
)


def average_precision(predictions: Sequence[float], gold: Sequence[float]) -> float | None:
    positives = sum(value > 0 for value in gold)
    if not positives:
        return None
    pairs = sorted(zip(predictions, gold), key=lambda pair: pair[0], reverse=True)
    true_positive = false_positive = 0
    previous_recall = score = 0.0
    index = 0
    while index < len(pairs):
        end = index
        while end < len(pairs) and pairs[end][0] == pairs[index][0]:
            if pairs[end][1] > 0:
                true_positive += 1
            else:
                false_positive += 1
            end += 1
        recall = true_positive / positives
        precision = true_positive / (true_positive + false_positive)
        score += (recall - previous_recall) * precision
        previous_recall, index = recall, end
    return score


def _metrics(grouped: Mapping[str, list[tuple[GoldLabels, Sequence[float], Sequence[float]]]]) -> dict:
    results = {language: evaluate_language(language, grouped[language]) for language in LANGUAGES}
    macro, reason = macro_average(results)
    by_language, all_predictions, all_gold = {}, [], []
    for language in LANGUAGES:
        predictions, gold, masked = assemble(grouped[language])
        all_predictions.extend(predictions)
        all_gold.extend(gold)
        by_language[language] = {
            "documents": results[language].documents,
            "positions": results[language].positions,
            "masked_punctuation": masked,
            "spearman": results[language].spearman,
            "ties": len(predictions) - len(set(predictions)),
            "average_precision": average_precision(predictions, gold),
        }
    return {
        "per_language": by_language,
        "macro_spearman": macro,
        "macro_undefined_reason": reason,
        "ties": len(all_predictions) - len(set(all_predictions)),
        "average_precision": average_precision(all_predictions, all_gold),
    }


def _artifact_manifest(out_dir: Path, names: Sequence[str]) -> dict:
    return {name: _sha256((out_dir / name).read_bytes()) for name in names}


def run_oracle(manifest_path: Path, out_dir: Path, *, split: str = "dev") -> dict:
    assert_development_split(split)
    if out_dir.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact directory {out_dir}")
    _manifest, records = load_frozen_records(manifest_path, split=split)
    out_dir.mkdir(parents=True)
    rows, prediction_records = [], []
    for name, granularity, description in ORACLE_VARIANTS:
        grouped: dict[str, list] = defaultdict(list)
        for item, gold in records:
            prediction_a = oracle_vector(name, item.text_a.tokens, gold.labels_a)
            prediction_b = oracle_vector(name, item.text_b.tokens, gold.labels_b)
            check_vector(item.text_a, prediction_a, name=f"{name}.{item.id}.a")
            check_vector(item.text_b, prediction_b, name=f"{name}.{item.id}.b")
            grouped[item.language].append((gold, prediction_a, prediction_b))
            prediction_records.append({"schema": B4_SCHEMA, "experiment": "A", "diagnostic_only": True,
                                       "variant": name, "id": item.id, "pair": item.pair,
                                       "prediction_a": prediction_a, "prediction_b": prediction_b})
        metrics = _metrics(grouped)
        rows.append({"variant": name, "granularity": granularity, "description": description,
                     "coverage": "30/30", **metrics})
    result = {
        "schema": B4_SCHEMA, "experiment": "A", "name": "B4 — Alignment-First SDM",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "split": split, "frozen_manifest_sha256": FROZEN_MANIFEST_SHA256,
        "official_evaluator": {"commit": OFFICIAL_COMMIT, "files": OFFICIAL_FILES,
                               "punctuation": "gold label -1 positions masked exactly as official evaluator"},
        "safety": "gold-derived diagnostics only; forbidden from prompts, prediction features, routing, and submissions",
        "rows": rows,
    }
    _write_jsonl(out_dir / "predictions.jsonl", prediction_records)
    _write_json(out_dir / "results.json", result)
    checksums = _artifact_manifest(out_dir, ("predictions.jsonl", "results.json"))
    _write_json(out_dir / "checksums.json", checksums)
    return result


def upstream_url(language: str, *, split: str = "dev") -> str:
    assert_development_split(split)
    filename = UPSTREAM_FILES[language][0]
    path = f"swissgov_rsd/data/evaluation/encoder_predictions/dev/{filename}"
    return f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_COMMIT}/{urllib.parse.quote(path, safe='/')}"


def fetch_upstream(language: str, cache_dir: Path, *, split: str = "dev", opener: Callable[..., object] = urllib.request.urlopen) -> Path:
    assert_development_split(split)
    filename, expected = UPSTREAM_FILES[language]
    target = Path(cache_dir) / UPSTREAM_COMMIT / filename
    if target.exists() and _sha256(target.read_bytes()) == expected:
        return target
    with opener(upstream_url(language, split=split), timeout=120) as response:  # type: ignore[operator]
        data = response.read()
    if _sha256(data) != expected:
        raise ValueError(f"pinned DiffAlign {language} prediction hash mismatch")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def load_alignment_predictions(items: Sequence[InferenceInput], cache_dir: Path, *, split: str = "dev") -> tuple[dict[str, dict], dict]:
    """Gold-blind loader: input texts and pinned prediction scores only."""
    assert_development_split(split)
    wanted = {item.id: item for item in items}
    output: dict[str, dict] = {}
    sources = {}
    for language in LANGUAGES:
        path = fetch_upstream(language, cache_dir, split=split)
        sources[language] = {"path": str(path), "sha256": _sha256(path.read_bytes()), "url": upstream_url(language)}
        for record in _jsonl(path):
            item = wanted.get(record.get("id"))
            if item is None:
                continue
            if record["text_a"] != " ".join(item.text_a.tokens) or record["text_b"] != " ".join(item.text_b.tokens):
                raise ValueError(f"{item.id}: upstream prediction text differs from frozen input")
            a = check_vector(item.text_a, record["labels_a"], name=f"{item.id}.diffalign_a")
            b = check_vector(item.text_b, record["labels_b"], name=f"{item.id}.diffalign_b")
            output[item.id] = {"prediction_a": a, "prediction_b": b}
    missing = sorted(set(wanted) - set(output))
    if missing:
        raise ValueError(f"pinned DiffAlign predictions missing frozen IDs: {missing}")
    return output, sources


def _document_spearman(item: InferenceInput, gold: GoldLabels, prediction: Mapping[str, Sequence[float]]) -> float | None:
    return evaluate_language(item.language, [(gold, prediction["prediction_a"], prediction["prediction_b"])]).spearman


def run_alignment(manifest_path: Path, out_dir: Path, cache_dir: Path, *, split: str = "dev") -> dict:
    assert_development_split(split)
    if out_dir.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact directory {out_dir}")
    _manifest, records = load_frozen_records(manifest_path, split=split)
    started, cpu_started = time.monotonic(), time.process_time()
    usage_before = resource.getrusage(resource.RUSAGE_SELF)
    items = [item for item, _gold in records]
    predictions, sources = load_alignment_predictions(items, cache_dir, split=split)
    # Gold is joined only here, after all prediction-time work is complete.
    grouped: dict[str, list] = defaultdict(list)
    per_document = []
    prediction_records, evidence_records = [], []
    for item, gold in records:
        prediction = predictions[item.id]
        grouped[item.language].append((gold, prediction["prediction_a"], prediction["prediction_b"]))
        per_document.append({"id": item.id, "pair": item.pair,
                             "spearman": _document_spearman(item, gold, prediction)})
        prediction_records.append({"schema": B4_SCHEMA, "experiment": "B", "id": item.id, "pair": item.pair,
                                   "prediction_a": list(prediction["prediction_a"]),
                                   "prediction_b": list(prediction["prediction_b"])})
        for side, tokens, values in (("a", item.text_a.tokens, prediction["prediction_a"]),
                                     ("b", item.text_b.tokens, prediction["prediction_b"])):
            evidence_records.append({"schema": B4_SCHEMA, "experiment": "B", "id": item.id, "side": side,
                                     "tokens": list(tokens), "anomaly_scores": list(values),
                                     "alignment_confidence": [1.0 - value for value in values],
                                     "counterpart_indices": None,
                                     "limitation": "published DiffAlign vectors retain max similarity, not argmax counterpart index"})
    metrics = _metrics(grouped)
    usage_after = resource.getrusage(resource.RUSAGE_SELF)
    failures = sorted(per_document, key=lambda value: (value["spearman"] is not None,
                                                       value["spearman"] if value["spearman"] is not None else -2))[:5]
    result = {
        "schema": B4_SCHEMA, "experiment": "B", "name": "B4 — Alignment-First SDM",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "split": split,
        "method": {
            "name": "DiffAlign continuous alignment-only baseline",
            "formula": "per official token: 1 - maximum non-negative cross-lingual subword cosine similarity; subwords averaged to whitespace token",
            "upstream_repo": UPSTREAM_REPO, "upstream_commit": UPSTREAM_COMMIT, "license": UPSTREAM_LICENSE,
            "upstream_model": "Qwen/Qwen3-Embedding-4B layer 20",
            "properties": ["full-document all-to-all correspondence", "continuous scores", "order-reversal tolerant",
                           "unmatched material receives high anomaly score", "no gold prediction features"],
        },
        "sources": sources, "frozen_manifest_sha256": FROZEN_MANIFEST_SHA256,
        "coverage": "30/30", "calls": {"apertus": 0, "network_prediction_calls": 0},
        "metrics": metrics, "per_document": per_document, "failure_cases": failures,
        "resources": {"wall_s": round(time.monotonic() - started, 6),
                      "cpu_s": round(time.process_time() - cpu_started, 6),
                      "max_rss_kib": max(usage_before.ru_maxrss, usage_after.ru_maxrss),
                      "local_model_inference": False,
                      "upstream_generation_resources": "not reported in published prediction artifacts"},
        "limitations": [
            "Pinned published predictions make local evaluation small and reproducible but do not measure upstream encoder latency.",
            "Published vectors retain max-alignment confidence but not counterpart indices, so evidence cannot reconstruct individual links.",
            "All-to-all matching supports reordering but can spuriously match repeated boilerplate and cognates.",
        ],
        "official_evaluator": {"commit": OFFICIAL_COMMIT, "files": OFFICIAL_FILES,
                               "punctuation": "gold label -1 positions masked exactly as official evaluator"},
    }
    out_dir.mkdir(parents=True)
    _write_jsonl(out_dir / "predictions.jsonl", prediction_records)
    _write_jsonl(out_dir / "evidence.jsonl", evidence_records)
    _write_json(out_dir / "results.json", result)
    checksums = _artifact_manifest(out_dir, ("predictions.jsonl", "evidence.jsonl", "results.json"))
    _write_json(out_dir / "checksums.json", checksums)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("oracle", "alignment"):
        command = sub.add_parser(name)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--out", type=Path, required=True)
        command.add_argument("--split", default="dev")
        if name == "alignment":
            command.add_argument("--cache", type=Path, default=Path("data/upstream/diffalign"))
    args = parser.parse_args(argv)
    if args.command == "oracle":
        result = run_oracle(args.manifest, args.out, split=args.split)
    else:
        result = run_alignment(args.manifest, args.out, args.cache, split=args.split)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
