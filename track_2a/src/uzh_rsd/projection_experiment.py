"""Predeclared B2 projection-cap experiment on the development split only.

Inference, parsing/projection, and scoring are deliberately separate.  P0 is
the frozen 40-token projector; P1 changes only that cap to 160.  P2 requires
model-supplied, validated offsets, which the frozen B2 response schema does not
contain, so it is reported as infeasible rather than simulated.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Mapping, Sequence

from .data_adapter import DATASET_REPO, DATASET_REVISION, LANGUAGES, GoldLabels, load_split, manifest_digest
from .evaluation import evaluate_language, macro_average, official_excluded_ids, LanguageResult
from .methods import MethodOutput, load_json_object, parse_b2
from .runner import manifest_records, read_raw

SEED = "b2-projection-evidence-v1"
P0_CAP = 40
P1_CAP = 160
SAMPLE_PER_LANGUAGE = 10


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _gold_type(gold: GoldLabels) -> str:
    a = any(value > 0 for value in gold.labels_a if value != -1)
    b = any(value > 0 for value in gold.labels_b if value != -1)
    return "both" if a and b else "a_only" if a else "b_only" if b else "none"


def build_experiment_manifest() -> dict:
    excluded, excluded_sha = official_excluded_ids()
    entries = []
    for language in LANGUAGES:
        records = [(item, gold) for item, gold in load_split("dev", language) if item.id not in excluded]
        ordered = sorted(records, key=lambda pair: len(pair[0].text_a) + len(pair[0].text_b))
        buckets: dict[str, list] = defaultdict(list)
        for rank, pair in enumerate(ordered):
            length_bucket = ("short", "medium", "long")[min(2, rank * 3 // len(ordered))]
            buckets[length_bucket].append(pair)
        chosen = []
        for length_bucket, quota in (("short", 4), ("medium", 3), ("long", 3)):
            candidates = sorted(
                buckets[length_bucket],
                key=lambda pair: (_gold_type(pair[1]), _hash(f"{SEED}|{pair[0].id}")),
            )
            # Round-robin label-derived burden/type groups, with deterministic ordering.
            groups: dict[str, list] = defaultdict(list)
            for pair in candidates:
                groups[_gold_type(pair[1])].append(pair)
            labels = sorted(groups, key=lambda name: _hash(f"{SEED}|{language}|{length_bucket}|{name}"))
            while len([x for x in chosen if x[2] == length_bucket]) < quota:
                progressed = False
                for label in labels:
                    if groups[label] and len([x for x in chosen if x[2] == length_bucket]) < quota:
                        item, gold = groups[label].pop(0)
                        chosen.append((item, gold, length_bucket, label))
                        progressed = True
                if not progressed:
                    raise ValueError(f"insufficient {language}/{length_bucket} candidates")
        for item, gold, length_bucket, burden_type in chosen:
            entries.append({
                "id": item.id,
                "pair": item.pair,
                "doc_index": item.doc_index,
                "tokens_a": len(item.text_a),
                "tokens_b": len(item.text_b),
                "text_a_sha256": item.text_a.sha256,
                "text_b_sha256": item.text_b.sha256,
                "gold_sha256": hashlib.sha256(json.dumps([gold.labels_a, gold.labels_b]).encode()).hexdigest(),
                "stratum": {"source_length": length_bucket, "gold_burden_type": burden_type},
            })
    body = {
        "schema": "uzh-rsd.projection-experiment-manifest/v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "split": "dev",
        "dataset": {"repo": DATASET_REPO, "revision": DATASET_REVISION},
        "selection": {
            "method": "within each language: source-length terciles; quotas 4/3/3 short/medium/long; deterministic round-robin over gold-derived burden/type",
            "seed": SEED,
            "sample_per_language": SAMPLE_PER_LANGUAGE,
            "gold_use": "selection stratum and post-inference scoring only; never prompt input",
            "excluded_ids_source": "SwissGov-RSD list_to_drop.txt",
            "excluded_ids_sha256": excluded_sha,
        },
        "projection_variants": {
            "P0": {"method": "frozen strict exact/normalised excerpt matching", "max_excerpt_tokens": P0_CAP},
            "P1": {"method": "same strict matching; cap-only change predeclared before scoring", "max_excerpt_tokens": P1_CAP},
            "P2": {"status": "infeasible", "reason": "B2 response schema contains excerpts but no offsets; offsets will not be manufactured"},
        },
        "counts": {f"en-{language}": sum(e["pair"] == f"en-{language}" for e in entries) for language in LANGUAGES},
        "entries": entries,
    }
    body["manifest_sha256"] = manifest_digest(body)
    return body


def write_manifest(path: Path) -> dict:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    manifest = build_experiment_manifest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest


def _score(outputs: Mapping[str, MethodOutput], records: Sequence[tuple]) -> dict:
    by_language = defaultdict(list)
    for item, gold in records:
        output = outputs[item.id]
        if output.diff_a is not None:
            by_language[item.language].append((gold, output.diff_a, output.diff_b))
    results = {language: evaluate_language(language, by_language[language]) for language in LANGUAGES if by_language[language]}
    macro, reason = macro_average(results)
    return {
        "per_language": {language: {"documents": r.documents, "positions": r.positions, "spearman": r.spearman} for language, r in results.items()},
        "macro": macro,
        "macro_undefined_reason": reason,
    }


def _doc_score(output: MethodOutput, gold: GoldLabels, language: str) -> float | None:
    if output.diff_a is None:
        return None
    return evaluate_language(language, [(gold, output.diff_a, output.diff_b)]).spearman


def _aggregate(outputs: Mapping[str, MethodOutput]) -> dict:
    valid = [output for output in outputs.values() if output.diff_a is not None]
    keys = ("items", "projected", "invalid_item", "invalid_severity", "unknown_kind", "spans_exact", "spans_normalised",
            "spans_not_found", "spans_too_long", "spans_ambiguous", "marked_tokens_a", "marked_tokens_b")
    sums = {key: sum(o.diagnostics.get(key, 0) for o in valid) for key in keys}
    sums.update({
        "documents": len(outputs),
        "parseable_documents": len(valid),
        "matched_excerpts": sums["spans_exact"] + sums["spans_normalised"],
        "unmatched_excerpts": sums["spans_not_found"] + sums["spans_too_long"],
        "coverage": len(valid) / len(outputs) if outputs else 0,
    })
    return sums


def analyse(raw_path: Path, manifest_path: Path, out_dir: Path, *, label: str) -> dict:
    manifest = json.loads(manifest_path.read_text())
    records = manifest_records(manifest)
    raw = [record for record in read_raw(raw_path) if record["method"] == "b2"]
    by_id = {record["id"]: record for record in raw}
    variants: dict[str, dict[str, MethodOutput]] = {"P0": {}, "P1": {}}
    decisions = {}
    for item, _gold in records:
        record = by_id.get(item.id)
        text = record.get("generation", {}).get("text") if record and record.get("status") == "returned" else None
        variants["P0"][item.id] = parse_b2(item, text, max_excerpt_tokens=P0_CAP)
        variants["P1"][item.id] = parse_b2(item, text, max_excerpt_tokens=P1_CAP)
        parsed, _mode = load_json_object(text or "")
        decisions[item.id] = parsed if parsed is not None else {"unparseable": True}
    result = {
        "schema": "uzh-rsd.projection-experiment-results/v1",
        "label": label,
        "raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "manifest_sha256": manifest["manifest_sha256"],
        "P2": manifest.get("projection_variants", {}).get("P2", {
            "status": "infeasible",
            "reason": "B2 response schema contains excerpts but no offsets; offsets will not be manufactured",
        }),
        "variants": {},
    }
    generations = [record.get("generation") for record in raw if record.get("generation")]
    latencies = [generation["latency_s"] for generation in generations if generation.get("latency_s") is not None]
    completion = [generation["completion_tokens"] for generation in generations if generation.get("completion_tokens") is not None]
    result["inference"] = {
        "calls": len(raw),
        "returned": sum(record.get("status") == "returned" for record in raw),
        "call_failed": sum(record.get("status") == "call_failed" for record in raw),
        "finish_length": sum(generation.get("finish_reason") == "length" for generation in generations),
        "prompt_tokens": sum(generation.get("prompt_tokens") or 0 for generation in generations),
        "completion_tokens": sum(completion),
        "latency_total_s": round(sum(latencies), 3),
        "latency_median_s": round(statistics.median(latencies), 3) if latencies else None,
        "completion_tokens_per_s": round(sum(completion) / sum(latencies), 3) if latencies and sum(latencies) else None,
        "monetary_cost_usd": 0,
    }
    for name in ("P0", "P1"):
        result["variants"][name] = {"score": _score(variants[name], records), "projection": _aggregate(variants[name])}
    p0_projection = result["variants"]["P0"]["projection"]
    p1_projection = result["variants"]["P1"]["projection"]
    result["recovered_spans"] = p1_projection["matched_excerpts"] - p0_projection["matched_excerpts"]
    result["over_cap_but_still_unmatched"] = p1_projection["spans_not_found"] - p0_projection["spans_not_found"]
    cases = []
    for item, gold in records:
        p0, p1 = variants["P0"][item.id], variants["P1"][item.id]
        s0, s1 = _doc_score(p0, gold, item.language), _doc_score(p1, gold, item.language)
        delta = None if s0 is None or s1 is None else s1 - s0
        cases.append({"id": item.id, "pair": item.pair, "p0_spearman": s0, "p1_spearman": s1, "delta": delta,
                      "decision": decisions[item.id], "source_a": " ".join(item.text_a.tokens[:80]), "source_b": " ".join(item.text_b.tokens[:80]),
                      "p0_projection": p0.diagnostics, "p1_projection": p1.diagnostics})
    improved = sorted((c for c in cases if c["delta"] is not None and c["delta"] > 0), key=lambda c: -c["delta"])
    regressed = sorted((c for c in cases if c["delta"] is not None and c["delta"] < 0), key=lambda c: c["delta"])
    unchanged = sorted((c for c in cases if c["delta"] == 0), key=lambda c: (c["p1_spearman"] is not None, c["p1_spearman"] or -2))
    result["case_analysis"] = {
        "improvement": improved[0] if improved else None,
        "regression": regressed[0] if regressed else None,
        "unchanged_failure": unchanged[0] if unchanged else None,
        "category_notes": {
            "improvement": None if improved else "No per-document P1 improvement exists.",
            "regression": None if regressed else "No per-document P1 regression exists.",
            "unchanged_failure": None if unchanged else "No unchanged per-document case exists.",
        },
    }
    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "analysis.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    (out_dir / "report.md").write_text(render_report(result))
    return result


def render_report(result: Mapping) -> str:
    lines = [f"# B2 projection-cap experiment — {result['label']}", "", "P0 is the frozen 40-token strict projector. P1 changes only the predeclared cap to 160. P2 is infeasible because responses carry no offsets; none were invented.", "",
             "| Variant | DE | FR | IT | Macro | matched | unmatched | too long | ambiguous | coverage |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for name in ("P0", "P1"):
        v = result["variants"][name]; p = v["projection"]; s = v["score"]
        vals = [s["per_language"].get(lang, {}).get("spearman") for lang in LANGUAGES]
        fmt = lambda x: "undefined" if x is None else f"{x:.6f}"
        lines.append(f"| {name} | {fmt(vals[0])} | {fmt(vals[1])} | {fmt(vals[2])} | {fmt(s['macro'])} | {p['matched_excerpts']} | {p['unmatched_excerpts']} | {p['spans_too_long']} | {p['spans_ambiguous']} | {p['parseable_documents']}/{p['documents']} |")
    usage = result["inference"]
    lines += ["", f"Recovered over-cap excerpts under P1: **{result['recovered_spans']}**; over-cap excerpts still unmatched after validation: **{result['over_cap_but_still_unmatched']}**.", "",
              f"Inference: {usage['returned']}/{usage['calls']} returned; {usage['finish_length']} hit the completion limit; {usage['prompt_tokens']} prompt and {usage['completion_tokens']} completion tokens; {usage['latency_total_s']} s total, {usage['latency_median_s']} s median, {usage['completion_tokens_per_s']} completion tokens/s; monetary cost $0.", "",
              "Projection changes do not establish improved semantic reasoning: both variants replay identical model decisions.", "", "## Cases", ""]
    for key in ("improvement", "regression", "unchanged_failure"):
        case = result["case_analysis"][key]
        if case is None:
            lines.append(f"- **{key}:** {result['case_analysis']['category_notes'][key]}")
        else:
            lines.append(f"- **{key}:** `{case['id']}` P0={case['p0_spearman']} P1={case['p1_spearman']} delta={case['delta']}; failure attribution: projection if diagnostics differ, otherwise semantic decision/scoring. Full bounded passages, decision, and diagnostics are in `analysis.json`.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    manifest = sub.add_parser("manifest")
    manifest.add_argument("--out", type=Path, required=True)
    replay = sub.add_parser("analyse")
    replay.add_argument("--raw", type=Path, required=True)
    replay.add_argument("--manifest", type=Path, required=True)
    replay.add_argument("--out", type=Path, required=True)
    replay.add_argument("--label", required=True)
    args = parser.parse_args(argv)
    if args.command == "manifest":
        result = write_manifest(args.out)
        print(json.dumps({"path": str(args.out), "counts": result["counts"], "manifest_sha256": result["manifest_sha256"]}, indent=2))
    else:
        result = analyse(args.raw, args.manifest, args.out, label=args.label)
        print(json.dumps({"out": str(args.out), "P0": result["variants"]["P0"]["score"], "P1": result["variants"]["P1"]["score"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
