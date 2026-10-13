"""B6 Semantic Risk Atlas: gold-blind selection and isolated evaluation.

``freeze`` accepts only B4 gold-free evidence, a sanitized identity manifest,
the independently authored atlas, and the already-frozen B5 selector.  Gold is
not part of its API.  ``score`` is a separate command that joins permitted dev
gold only after verifying the frozen selection-manifest checksum.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path

from .b4 import load_frozen_records
from .b5 import _bootstrap, _metric_bundle
from .evaluation import _average_ranks
from .splits import assert_development_split

B6_SCHEMA = "uzh-rsd.b6/v1"
BUDGET = 5
RADIUS = 2
SEED = "b6-risk-atlas-random-v1"
STRATEGIES = ("A0_b5", "A1_risk", "A2_family", "uniform_random", "cue_first")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def sanitize_identities(source_path: Path, out_path: Path, *, split: str = "dev") -> dict:
    """Make the only manifest shape accepted by ``freeze``; copy no gold fields."""
    assert_development_split(split)
    if out_path.exists():
        raise FileExistsError(out_path)
    source = json.loads(source_path.read_bytes())
    if source.get("split") != split or len(source.get("entries", [])) != 30:
        raise ValueError("requires the frozen 30-document dev manifest")
    result = {"schema": B6_SCHEMA, "stage": "gold_free_identity_sanitization", "split": split,
              "source_sha256": _sha(source_path.read_bytes()),
              "entries": [{key: row[key] for key in ("id", "pair", "doc_index", "text_a_sha256", "text_b_sha256", "tokens_a", "tokens_b")}
                          for row in source["entries"]]}
    _write_json(out_path, result)
    return result


def _lex(token: str) -> str:
    return token.casefold().strip(".,;:!?()[]{}<>\"'«»“”/\\|_-–—")


def _match_categories(tokens: Sequence[str], atlas: Mapping) -> list[set[str]]:
    """Return independently-authored lexical/structural risk categories per token."""
    result = [set() for _ in tokens]
    lowered = [_lex(token) for token in tokens]
    for entry in atlas["entries"]:
        category = str(entry["category"])
        lexical = {str(value).casefold() for value in entry["pattern"].get("tokens", [])}
        for index, token in enumerate(lowered):
            if token and token in lexical:
                result[index].add(category)
        structural = entry["pattern"].get("structural")
        if structural == "numeric":
            for index, token in enumerate(tokens):
                if any(character.isdigit() for character in token):
                    result[index].add(category)
        elif structural == "conditional_pair":
            anchors = [i for i, token in enumerate(lowered) if token in lexical]
            for anchor in anchors:
                for index in range(max(0, anchor - 2), min(len(tokens), anchor + 6)):
                    result[index].add(category)
        elif structural == "scope_punctuation":
            for index, token in enumerate(tokens):
                if token in {";", ":", "(", ")"}:
                    result[index].add(category)
    return result


def _candidate_rows(record: Mapping, categories: Sequence[set[str]], family_categories: set[str]) -> list[dict]:
    tokens = [str(value) for value in record["tokens"]]
    anomaly = [float(value) for value in record["anomaly_scores"]]
    if len(tokens) != len(anomaly) or len(tokens) != len(categories):
        raise ValueError(f"{record.get('id')}.{record.get('side')}: incompatible evidence")
    counts = Counter(filter(None, map(_lex, tokens)))
    rows = []
    for center in range(len(tokens)):
        start, end = max(0, center - RADIUS), min(len(tokens), center + RADIUS + 1)
        cats = sorted(set().union(*categories[start:end]))
        numeric = any(any(character.isdigit() for character in tokens[i]) for i in range(start, end))
        repeated = any(counts[_lex(tokens[i])] > 1 and len(_lex(tokens[i])) >= 3 for i in range(start, end))
        url = any(_lex(tokens[i]).startswith(("http", "www")) or "@" in tokens[i] for i in range(start, end))
        cue = float(numeric or repeated or url)
        risk = min(1.0, len(cats) / 2)
        confidence = 1.0 - anomaly[center]
        shared = float(bool(set(cats) & family_categories) and record["side"] == "a")
        rows.append({
            "side": record["side"], "start": start, "end": end, "center": center,
            "group_id": f"{record['id']}:{record['side']}:{start}:{end}:{center}",
            "token_sha256": _sha("\u241f".join(tokens[start:end]).encode()),
            "categories": cats,
            "features": {"risk": risk, "confidence": confidence, "anomaly": anomaly[center],
                         "cue": cue, "family_agreement": shared},
        })
    return rows


def _priority(row: Mapping, strategy: str) -> tuple[float, str]:
    f = row["features"]
    if strategy == "A1_risk":
        value = .60 * f["risk"] + .25 * f["confidence"] + .10 * f["cue"] + .05 * f["anomaly"]
    elif strategy == "A2_family":
        value = .50 * f["risk"] + .20 * f["confidence"] + .10 * f["cue"] + .05 * f["anomaly"] + .15 * f["family_agreement"]
    elif strategy == "uniform_random":
        value = int(_sha(f"{SEED}|{row['group_id']}".encode()), 16) / (2**256 - 1)
    elif strategy == "cue_first":
        value = f["cue"] + .01 * f["anomaly"]
    else:
        raise ValueError(strategy)
    return value, str(row["group_id"])


def _select(rows: Sequence[Mapping], strategy: str) -> list[dict]:
    ordered = sorted(rows, key=lambda row: (-_priority(row, strategy)[0], _priority(row, strategy)[1]))
    selected: list[dict] = []
    occupied: dict[str, set[int]] = defaultdict(set)
    for candidate in ordered:
        positions = set(range(int(candidate["start"]), int(candidate["end"])))
        if positions & occupied[str(candidate["side"])]:
            continue
        row = dict(candidate)
        row["priority"] = _priority(candidate, strategy)[0]
        row["rank"] = len(selected) + 1
        selected.append(row)
        occupied[str(candidate["side"])].update(positions)
        if len(selected) == BUDGET:
            return selected
    raise ValueError("fewer than five non-overlapping regions")


def freeze(evidence_path: Path, identity_path: Path, atlas_path: Path, b5_path: Path,
           out_path: Path, *, split: str = "dev") -> dict:
    assert_development_split(split)
    if out_path.exists():
        raise FileExistsError(out_path)
    evidence_bytes, identity_bytes, atlas_bytes, b5_bytes = (path.read_bytes() for path in (evidence_path, identity_path, atlas_path, b5_path))
    evidence, identities, atlas, b5 = _read_jsonl(evidence_path), json.loads(identity_bytes), json.loads(atlas_bytes), json.loads(b5_bytes)
    if len(evidence) != 60 or any(row.get("counterpart_indices") is not None for row in evidence):
        raise ValueError("requires 60 gold-free B4 side records without counterpart links")
    forbidden = {"gold", "labels_a", "labels_b", "gold_sha256", "stratum"}
    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value)) if value else set()
        return set()
    if forbidden & keys(identities):
        raise ValueError("identity manifest contains gold-related fields")
    identity_by_id = {row["id"]: row for row in identities["entries"]}
    by_id = defaultdict(dict)
    for row in evidence:
        by_id[row["id"]][row["side"]] = row
    if set(by_id) != set(identity_by_id) or any(set(sides) != {"a", "b"} for sides in by_id.values()):
        raise ValueError("identity/evidence coverage mismatch")

    # A four-language family is accepted only when DE/FR/IT all exist and the
    # English official tokens and frozen source-text hashes are identical.
    families: dict[int, list[str]] = defaultdict(list)
    for record_id, identity in identity_by_id.items():
        families[int(identity["doc_index"])].append(record_id)
    verified = {}
    category_map = {}
    for record_id, sides in by_id.items():
        category_map[record_id] = {side: _match_categories(row["tokens"], atlas) for side, row in sides.items()}
    for index, ids in families.items():
        languages = {identity_by_id[record_id]["pair"].split("-")[1] for record_id in ids}
        hashes = {identity_by_id[record_id]["text_a_sha256"] for record_id in ids}
        tokens = {_sha(_canonical(by_id[record_id]["a"]["tokens"])) for record_id in ids}
        if languages == {"de", "fr", "it"} and len(ids) == 3 and len(hashes) == len(tokens) == 1:
            target_sets = []
            for record_id in ids:
                target_sets.append(set().union(*category_map[record_id]["b"]))
            english = set().union(*category_map[ids[0]]["a"])
            verified[index] = {"ids": sorted(ids), "shared_categories": sorted(english.intersection(*target_sets)),
                               "text_a_sha256": next(iter(hashes)), "official_tokens_sha256": next(iter(tokens))}

    b5_groups = {(row["id"], row["policy"]): row["groups"][:BUDGET] for row in b5["selections"]}
    selections = []
    for record_id in sorted(by_id):
        family = verified.get(int(identity_by_id[record_id]["doc_index"]), {})
        family_categories = set(family.get("shared_categories", []))
        candidates = []
        for side in ("a", "b"):
            candidates.extend(_candidate_rows(by_id[record_id][side], category_map[record_id][side], family_categories))
        strategies = {
            "A0_b5": b5_groups[(record_id, "suspicious_v1")],
            "cue_first": b5_groups[(record_id, "cue_first_v1")],
            "A1_risk": _select(candidates, "A1_risk"),
            "A2_family": _select(candidates, "A2_family"),
            "uniform_random": _select(candidates, "uniform_random"),
        }
        for strategy in STRATEGIES:
            selections.append({"id": record_id, "strategy": strategy, "groups": strategies[strategy]})
    manifest = {
        "schema": B6_SCHEMA, "stage": "gold_blind_selection_freeze", "split": split,
        "budget": {"groups_per_document": BUDGET, "window_radius": RADIUS, "max_selected_tokens_nominal": BUDGET * (2 * RADIUS + 1)},
        "strategies": list(STRATEGIES), "primary": "A2_family", "verified_four_language_families": verified,
        "failure_behavior": "fail closed on coverage, identity, finite-score, budget, or split mismatch; never backfill from gold",
        "inputs": {"evidence_sha256": _sha(evidence_bytes), "identity_sha256": _sha(identity_bytes),
                   "atlas_sha256": _sha(atlas_bytes), "b5_selector_sha256": _sha(b5_bytes)},
        "selections": selections,
    }
    _write_json(out_path, manifest)
    return manifest


def _positions(groups: Sequence[Mapping]) -> dict[str, set[int]]:
    result: dict[str, set[int]] = defaultdict(set)
    for group in groups:
        result[str(group["side"])].update(range(int(group["start"]), int(group["end"])))
    return result


def _under_ranked(labels: Sequence[float], predictions: Sequence[float]) -> set[int]:
    eligible = [i for i, label in enumerate(labels) if label != -1]
    gold, pred = [labels[i] for i in eligible], [predictions[i] for i in eligible]
    gold_ranks, pred_ranks = _average_ranks(gold), _average_ranks(pred)
    return {index for index, gr, pr, label in zip(eligible, gold_ranks, pred_ranks, gold) if label > 0 and gr > pr}


def score(selector_path: Path, expected_sha256: str, baseline_path: Path, frozen_manifest_path: Path,
          out_dir: Path, *, split: str = "dev") -> dict:
    assert_development_split(split)
    if out_dir.exists():
        raise FileExistsError(out_dir)
    selector_bytes = selector_path.read_bytes()
    actual = _sha(selector_bytes)
    if actual != expected_sha256:
        raise ValueError(f"selection checksum mismatch: {actual}")
    selector = json.loads(selector_bytes)
    if selector.get("stage") != "gold_blind_selection_freeze":
        raise ValueError("selector not frozen")
    _manifest, records = load_frozen_records(frozen_manifest_path, split=split)
    baseline_rows = _read_jsonl(baseline_path)
    baseline = {row["id"]: row for row in baseline_rows}
    record_by_id = {item.id: item for item, _gold in records}
    offset_rows = []
    for row in selector["selections"]:
        item = record_by_id[row["id"]]
        for group in row["groups"]:
            side = str(group["side"])
            document = item.text_a if side == "a" else item.text_b
            start, end = int(group["start"]), int(group["end"])
            if not (0 <= start < end <= len(document.tokens)):
                raise ValueError(f"{item.id}.{side}: selected token offsets out of range")
            token_hash = _sha("\u241f".join(document.tokens[start:end]).encode())
            if token_hash != group["token_sha256"]:
                raise ValueError(f"{item.id}.{side}: selected official tokens changed")
            offset_rows.append({"id": item.id, "strategy": row["strategy"], "side": side,
                                "token_start": start, "token_end": end,
                                "source_char_start": document.offsets[start][0],
                                "source_char_end": document.offsets[end - 1][1],
                                "token_sha256": token_hash})
    chosen = {(row["id"], row["strategy"]): _positions(row["groups"]) for row in selector["selections"]}
    baseline_metrics = _metric_bundle(records, baseline)
    results = []
    for strategy in STRATEGIES:
        predictions, totals = {}, Counter()
        language = defaultdict(Counter)
        selected_sets = {}
        for item, gold in records:
            pos = chosen[(item.id, strategy)]
            selected_sets[item.id] = pos
            pa, pb = list(baseline[item.id]["prediction_a"]), list(baseline[item.id]["prediction_b"])
            for side, labels, values in (("a", gold.labels_a, pa), ("b", gold.labels_b, pb)):
                under = _under_ranked(labels, values)
                selected = {i for i in pos.get(side, set()) if labels[i] != -1}
                positive = {i for i, value in enumerate(labels) if value > 0}
                totals.update(selected=len(selected), positive=len(positive), selected_positive=len(selected & positive),
                              under_ranked=len(under), selected_under_ranked=len(selected & under), eligible=sum(v != -1 for v in labels))
                language[item.language].update(selected=len(selected), positive=len(positive), selected_positive=len(selected & positive),
                                                under_ranked=len(under), selected_under_ranked=len(selected & under), eligible=sum(v != -1 for v in labels))
                for index in selected:
                    values[index] = float(labels[index])
            predictions[item.id] = {"prediction_a": pa, "prediction_b": pb}
        metrics = _metric_bundle(records, predictions)
        def summarize(counts: Counter) -> dict:
            prevalence = counts["positive"] / counts["eligible"]
            precision = counts["selected_positive"] / counts["selected"]
            return {**counts, "token_coverage": counts["selected"] / counts["eligible"],
                    "gold_positive_recall": counts["selected_positive"] / counts["positive"],
                    "under_ranked_positive_recall": counts["selected_under_ranked"] / counts["under_ranked"] if counts["under_ranked"] else None,
                    "gold_positive_enrichment": precision / prevalence if prevalence else None}
        results.append({"strategy": strategy, "selection": summarize(totals),
                        "per_language_selection": {key: summarize(value) for key, value in language.items()},
                        "oracle_reachable_metrics": metrics,
                        "oracle_delta": metrics["macro_spearman"] - baseline_metrics["macro_spearman"],
                        "source_family_clustered_uncertainty": _bootstrap(records, baseline, predictions, iterations=500)})
    by_name = {row["strategy"]: row for row in results}
    primary, a0, random_control = by_name["A2_family"], by_name["A0_b5"], by_name["uniform_random"]
    threshold = {"under_ranked_recall_margin": .02, "oracle_delta_margin": .005,
                 "minimum_enrichment": 1.25, "languages_beating_a0_under_ranked_recall": 2}
    language_wins = sum(primary["per_language_selection"][lang]["under_ranked_positive_recall"] >
                        a0["per_language_selection"][lang]["under_ranked_positive_recall"] for lang in ("de", "fr", "it"))
    gate_checks = {
        "under_ranked_recall_over_a0": primary["selection"]["under_ranked_positive_recall"] >= a0["selection"]["under_ranked_positive_recall"] + .02,
        "under_ranked_recall_over_random": primary["selection"]["under_ranked_positive_recall"] >= random_control["selection"]["under_ranked_positive_recall"] + .02,
        "oracle_delta_over_a0": primary["oracle_delta"] >= a0["oracle_delta"] + .005,
        "oracle_delta_over_random": primary["oracle_delta"] >= random_control["oracle_delta"] + .005,
        "enrichment": primary["selection"]["gold_positive_enrichment"] >= 1.25,
        "per_language": language_wins >= 2,
    }
    result = {"schema": B6_SCHEMA, "split": split, "coverage": "30/30", "selector_sha256": actual,
              "baseline": baseline_metrics, "methods": results,
              "complementarity_with_b5": {
                  "a1_extra_selected_under_ranked": by_name["A1_risk"]["selection"]["selected_under_ranked"] - a0["selection"]["selected_under_ranked"],
                  "a2_extra_selected_under_ranked": primary["selection"]["selected_under_ranked"] - a0["selection"]["selected_under_ranked"],
              },
              "gate_a": {"primary": "A2_family", "thresholds": threshold, "checks": gate_checks,
                         "passes": all(gate_checks.values()),
                         "failure_verdict": "NOT SUPPORTED"},
              "official_offset_contract": "verified official str.split tokens and exact source [start,end) character offsets for every selected region",
              "pairing": {"verified_four_language_families": len(selector["verified_four_language_families"]),
                          "failure": "no complete DE/FR/IT sibling family in the frozen 30 documents" if not selector["verified_four_language_families"] else None},
              "failures": [], "apertus_calls": 0}
    out_dir.mkdir(parents=True)
    _write_json(out_dir / "results.json", result)
    (out_dir / "selected-offsets.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in offset_rows), encoding="utf-8"
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sanitize_parser = sub.add_parser("sanitize-identities")
    sanitize_parser.add_argument("--source", type=Path, required=True)
    sanitize_parser.add_argument("--out", type=Path, required=True)
    sanitize_parser.add_argument("--split", default="dev")
    freeze_parser = sub.add_parser("freeze")
    for name in ("evidence", "identity", "atlas", "b5-selector", "out"):
        freeze_parser.add_argument(f"--{name}", type=Path, required=True)
    freeze_parser.add_argument("--split", default="dev")
    score_parser = sub.add_parser("score")
    for name in ("selector", "baseline", "manifest", "out"):
        score_parser.add_argument(f"--{name}", type=Path, required=True)
    score_parser.add_argument("--selector-sha256", required=True)
    score_parser.add_argument("--split", default="dev")
    args = parser.parse_args(argv)
    if args.command == "sanitize-identities":
        sanitize_identities(args.source, args.out, split=args.split)
    elif args.command == "freeze":
        freeze(args.evidence, args.identity, args.atlas, args.b5_selector, args.out, split=args.split)
    else:
        score(args.selector, args.selector_sha256, args.baseline, args.manifest, args.out, split=args.split)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
