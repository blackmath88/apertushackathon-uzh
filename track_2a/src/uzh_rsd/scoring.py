"""Offline scoring of a saved run: parse, export predictions, evaluate.

Gold labels are loaded here, after inference, and never reach a prompt.

Three explicitly labelled views (none silently drops or fills documents):

* ``matched``        documents where *every* method produced valid vectors —
                     the like-for-like B0/B2 comparison;
* ``available``      per method, every document that method produced;
* ``paper_protocol`` every manifest document; a method's missing document is
                     scored as all-zero difference, which is what the upstream
                     parser yields for an empty response. Shown only as a
                     sensitivity check, with the number of filled documents.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

from .data_adapter import DEFAULT_DATA_DIR, LANGUAGES
from .evaluation import (
    DEFAULT_OFFICIAL_DIR,
    OfficialEvaluatorUnavailable,
    assemble,
    evaluate_language,
    load_official_compute_correlations,
    load_official_function,
    macro_average,
)
from .methods import MethodOutput, parse_b0, parse_b2
from .runner import manifest_records, read_raw
from .tokens import check_vector

RESULTS_SCHEMA = "uzh-rsd.results/v1"


def parse_run(raw: Sequence[dict], records, official_dir: Path = DEFAULT_OFFICIAL_DIR) -> tuple[dict[tuple[str, str], MethodOutput], dict[tuple[str, str], dict]]:
    parse_token_labels = load_official_function("parse_token_labels", official_dir)
    by_key: dict[tuple[str, str], dict] = {}
    for record in raw:
        key = (record["id"], record["method"])
        if key in by_key:
            raise ValueError(f"duplicate raw record for {key}")
        by_key[key] = record
    methods = sorted({record["method"] for record in raw})
    outputs: dict[tuple[str, str], MethodOutput] = {}
    for inference, _gold in records:
        for method in methods:
            record = by_key.get((inference.id, method))
            if record is None or record["status"] == "skipped_deadline":
                outputs[(inference.id, method)] = MethodOutput(method, inference.id, "not_run")
                continue
            text = record["generation"]["text"] if record["status"] == "returned" else None
            if method == "b0":
                output = parse_b0(inference, text, parse_token_labels)
            else:
                output = parse_b2(inference, text)
            if output.diff_a is not None:
                check_vector(inference.text_a, output.diff_a, name=f"{inference.id}.{method}.a")
                check_vector(inference.text_b, output.diff_b, name=f"{inference.id}.{method}.b")
            output.diagnostics["finish_reason"] = (record.get("generation") or {}).get("finish_reason")
            outputs[(inference.id, method)] = output
    return outputs, by_key


def _score(items_by_language: Mapping[str, list], official=None) -> dict:
    per_language = {}
    for language in LANGUAGES:
        items = items_by_language.get(language, [])
        if not items:
            continue
        result = evaluate_language(language, items)
        entry = {"documents": result.documents, "positions": result.positions, "spearman": result.spearman}
        if result.undefined_reason:
            entry["undefined_reason"] = result.undefined_reason
        if official is not None and result.spearman is not None:
            predictions, gold, _ = assemble(items)
            try:
                (rho, _interval), _kendall = official(list(predictions), list(gold), False)
                entry["official_spearman"] = float(rho)
            except Exception as error:  # official code raises on constant vectors
                entry["official_spearman"] = f"error: {type(error).__name__}"
        per_language[language] = entry
    from .evaluation import LanguageResult

    macro, reason = macro_average({
        language: LanguageResult(language, value["documents"], value["positions"], 0, value["spearman"])
        for language, value in per_language.items()
    })
    return {"per_language": per_language, "macro": macro, "macro_undefined_reason": reason}


def _usage(raw_by_key: Mapping, method: str) -> dict:
    generations = [record["generation"] for (_, m), record in raw_by_key.items() if m == method and record.get("generation")]
    latencies = [g["latency_s"] for g in generations if g.get("latency_s") is not None]
    prompt = [g["prompt_tokens"] for g in generations if g.get("prompt_tokens") is not None]
    completion = [g["completion_tokens"] for g in generations if g.get("completion_tokens") is not None]
    return {
        "calls": len(generations),
        "latency_s_total": round(sum(latencies), 1),
        "latency_s_median": round(statistics.median(latencies), 1) if latencies else None,
        "prompt_tokens_total": sum(prompt) if prompt else None,
        "completion_tokens_total": sum(completion) if completion else None,
        "token_count_source": sorted({g.get("token_count_source") for g in generations}),
        "finish_length": sum(1 for g in generations if g.get("finish_reason") == "length"),
    }


def evaluate_run(run_dir: Path, manifest: Mapping, data_dir: Path = DEFAULT_DATA_DIR, official_dir: Path = DEFAULT_OFFICIAL_DIR) -> dict:
    run_dir = Path(run_dir)
    raw = read_raw(run_dir / "raw.jsonl")
    records = manifest_records(manifest, data_dir)
    outputs, raw_by_key = parse_run(raw, records, official_dir)
    methods = sorted({method for _, method in outputs})
    try:
        official = load_official_compute_correlations(official_dir)
    except OfficialEvaluatorUnavailable:
        official = None

    # Predictions export (official encoder-style records) for every valid document.
    for method in methods:
        target = run_dir / "predictions" / method
        target.mkdir(parents=True, exist_ok=True)
        for language in LANGUAGES:
            lines = []
            for inference, _gold in records:
                output = outputs[(inference.id, method)]
                if inference.language == language and output.diff_a is not None:
                    lines.append(json.dumps({"id": inference.id, "text_a": inference.text_a.text, "text_b": inference.text_b.text,
                                             "labels_a": output.diff_a, "labels_b": output.diff_b}, ensure_ascii=False))
            (target / f"predictions_{language}.jsonl").write_text("".join(line + "\n" for line in lines), encoding="utf-8")

    views: dict[str, dict] = {"matched": {}, "available": {}, "paper_protocol": {}}
    matched_ids = [inference.id for inference, _ in records if all(outputs[(inference.id, m)].diff_a is not None for m in methods)]
    for method in methods:
        matched, available, paper = {}, {}, {}
        filled = 0
        for inference, gold in records:
            output = outputs[(inference.id, method)]
            language = inference.language
            if output.diff_a is not None:
                entry = (gold, output.diff_a, output.diff_b)
                available.setdefault(language, []).append(entry)
                if inference.id in matched_ids:
                    matched.setdefault(language, []).append(entry)
                paper.setdefault(language, []).append(entry)
            else:
                filled += 1
                paper.setdefault(language, []).append((gold, [0.0] * len(inference.text_a), [0.0] * len(inference.text_b)))
        views["matched"][method] = _score(matched, official)
        views["available"][method] = _score(available, official)
        views["paper_protocol"][method] = {**_score(paper, official), "documents_scored_as_zero": filled}

    coverage = {}
    for method in methods:
        method_outputs = [outputs[(inference.id, method)] for inference, _ in records]
        status = Counter(output.status for output in method_outputs)
        entry = {"documents": len(method_outputs), "status": dict(status), "usage": _usage(raw_by_key, method)}
        valid = [o for o in method_outputs if o.diff_a is not None]
        if method == "b0":
            entry["strict_valid_documents"] = sum(1 for o in valid if o.diagnostics.get("strict_valid"))
            tokens = sum(o.diagnostics[s]["tokens"] for o in valid for s in ("a", "b"))
            fallback = sum(o.diagnostics[s]["fallback"] + o.diagnostics[s]["out_of_range"] for o in valid for s in ("a", "b"))
            entry["tokens_in_parsed_documents"] = tokens
            entry["tokens_fallback_to_no_difference"] = fallback
            entry["model_punctuation_labels"] = sum(o.diagnostics[s]["model_punctuation_label"] for o in valid for s in ("a", "b"))
        else:
            keys = ("items", "projected", "invalid_item", "invalid_severity", "unknown_kind", "spans_exact", "spans_normalised",
                    "spans_not_found", "spans_too_long", "spans_ambiguous", "marked_tokens_a", "marked_tokens_b")
            entry["spans"] = {key: sum(o.diagnostics.get(key, 0) for o in valid) for key in keys}
        coverage[method] = entry

    results = {
        "schema": RESULTS_SCHEMA,
        "run_dir": run_dir.name,
        "manifest_sha256": manifest["manifest_sha256"],
        "documents": len(records),
        "matched_documents": len(matched_ids),
        "official_cross_check": official is not None,
        "views": views,
        "coverage": coverage,
        "per_document": [
            {"id": inference.id, "pair": inference.pair,
             **{method: {"status": outputs[(inference.id, method)].status, **_doc_diag(outputs[(inference.id, method)])} for method in methods}}
            for inference, _ in records
        ],
    }
    (run_dir / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    (run_dir / "results.md").write_text(render_markdown(results))
    return results


def _doc_diag(output: MethodOutput) -> dict:
    keep = {k: v for k, v in output.diagnostics.items() if k in ("parse", "strict_valid", "finish_reason", "items", "projected", "spans_not_found")}
    if output.method == "b0" and "a" in output.diagnostics:
        keep["fallback_tokens"] = sum(output.diagnostics[s]["fallback"] + output.diagnostics[s]["out_of_range"] for s in ("a", "b"))
    return keep


def _fmt(value) -> str:
    if value is None:
        return "undefined"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def render_markdown(results: Mapping) -> str:
    methods = sorted(results["coverage"])
    lines = [
        f"# Results — {results['run_dir']}",
        "",
        f"Dev manifest `{results['manifest_sha256'][:12]}…`: {results['documents']} documents; "
        f"{results['matched_documents']} have valid output from every method. "
        "Small pilot sample: differences between methods are **not** statistically established.",
        "",
    ]
    titles = {
        "matched": "Matched documents (like-for-like comparison)",
        "available": "All valid documents per method",
        "paper_protocol": "Paper protocol (missing documents scored as zero difference)",
    }
    for view, title in titles.items():
        lines += [f"## {title}", "", "| Method | EN–DE | EN–FR | EN–IT | Macro | Docs |", "|---|---|---|---|---|---|"]
        for method in methods:
            score = results["views"][view][method]
            cells = [_fmt(score["per_language"].get(language, {}).get("spearman")) for language in LANGUAGES]
            docs = sum(v["documents"] for v in score["per_language"].values())
            extra = f" ({score['documents_scored_as_zero']} zero-filled)" if view == "paper_protocol" else ""
            lines.append(f"| {method.upper()} | {' | '.join(cells)} | {_fmt(score['macro'])} | {docs}{extra} |")
        lines.append("")
    lines += ["## Coverage and usage", "", "| Method | Status | Calls | Prompt tok | Completion tok | Latency total / median (s) | Truncated |", "|---|---|---|---|---|---|---|"]
    for method in methods:
        entry = results["coverage"][method]
        usage = entry["usage"]
        status = ", ".join(f"{k} {v}" for k, v in sorted(entry["status"].items()))
        lines.append(f"| {method.upper()} | {status} | {usage['calls']} | {_fmt(usage['prompt_tokens_total'])} | {_fmt(usage['completion_tokens_total'])} | "
                     f"{_fmt(usage['latency_s_total'])} / {_fmt(usage['latency_s_median'])} | {usage['finish_length']} |")
    lines.append("")
    if "b0" in results["coverage"]:
        b0 = results["coverage"]["b0"]
        lines.append(f"B0 parsing: {b0['strict_valid_documents']} strictly valid documents; "
                     f"{b0['tokens_fallback_to_no_difference']} of {b0['tokens_in_parsed_documents']} tokens in parsed documents fell back to "
                     "'no difference' (upstream fallback similarity 5).")
    if "b2" in results["coverage"]:
        spans = results["coverage"]["b2"]["spans"]
        lines.append(f"B2 spans: {spans['items']} items, {spans['projected']} projected; excerpts located exactly {spans['spans_exact']}, "
                     f"normalised {spans['spans_normalised']}, not found {spans['spans_not_found']}, ambiguous {spans['spans_ambiguous']}; "
                     f"invalid items {spans['invalid_item']}, invalid severity {spans['invalid_severity']}, unknown kind {spans['unknown_kind']}.")
    lines.append("")
    cross = "official evaluator cross-check included (`official_spearman` in results.json)" if results["official_cross_check"] else "official evaluator not available for cross-check"
    lines.append(f"Spearman: global token-level per language, gold punctuation masked; {cross}.")
    return "\n".join(lines) + "\n"
