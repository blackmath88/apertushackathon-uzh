"""Bounded Experiment C capability probe for the local Apertus llama.cpp server.

This is not a benchmark run.  It makes exactly 16 single-token calls (four
frozen dev passage pairs x order/label controls), once each, without rationale,
retry, grammar, test data, or prompt search.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .splits import assert_development_split

SCHEMA = "uzh-rsd.b4-apertus-probe/v1"
MODEL = "apertus-v1.5-8b-text-q8_0"
MODEL_SHA256 = "dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d"
LLAMA_COMMIT = "7ab4ee7"
MAX_CALLS = 24

CASES = (
    {"id": "admin_fr_53:07", "pair": "en-fr", "expected": "equivalent",
     "a": "Last modification 17 . 09 . 2024",
     "b": "Dernière modification 17 . 09 . 2024"},
    {"id": "admin_it_37:01", "pair": "en-it", "expected": "equivalent",
     "a": "OFCOM Central : Tel .",
     "b": "UFCOM Centrale : Tel ."},
    {"id": "admin_de_140:07", "pair": "en-de", "expected": "different",
     "a": "Specialist staff Last modification 03 . 01 . 2024",
     "b": "Fachkontakt Letzte Änderung 10 . 11 . 2023 Zum Seitenanfang Bestellformular"},
    {"id": "admin_fr_58:07", "pair": "en-fr", "expected": "different",
     "a": "He is a Swiss - Italian dual citizen . Specialist staff",
     "b": "Il est membre du Parti vert’libéral . Contact spécialisé"},
)

CONDITIONS = (
    {"name": "base", "reverse": False,
     "labels": {"equivalent": "0", "different": "1", "insufficient": "2"}},
    {"name": "order_reversed", "reverse": True,
     "labels": {"equivalent": "0", "different": "1", "insufficient": "2"}},
    {"name": "labels_rotated", "reverse": False,
     "labels": {"equivalent": "2", "different": "0", "insufficient": "1"}},
    {"name": "order_reversed_labels_rotated", "reverse": True,
     "labels": {"equivalent": "2", "different": "0", "insufficient": "1"}},
)


def _request(url: str, *, body: dict | None = None, timeout: float = 120) -> dict:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def _endpoint(base_url: str, path: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port != 11436:
        raise ValueError("Experiment C is restricted to loopback port 11436")
    return base_url.rstrip("/") + path


def inspect_capabilities(base_url: str) -> dict:
    """Read native metadata and tokenize labels before any inference call."""
    health = _request(_endpoint(base_url, "/health"))
    models = _request(_endpoint(base_url, "/v1/models"))
    props = _request(_endpoint(base_url, "/props"))
    tokenization = {}
    for label in ("0", "1", "2"):
        tokenization[label] = _request(_endpoint(base_url, "/tokenize"), body={
            "content": label, "add_special": False, "with_pieces": True,
        })["tokens"]
    if health.get("status") != "ok":
        raise RuntimeError("Apertus endpoint is not healthy")
    ids = {entry.get("id") for entry in models.get("data", [])}
    if MODEL not in ids:
        raise RuntimeError(f"expected model {MODEL!r} not served")
    if any(len(tokens) != 1 or tokens[0].get("piece") != label for label, tokens in tokenization.items()):
        raise RuntimeError("candidate labels are not one token each")
    return {
        "health": health,
        "model": next(entry for entry in models["data"] if entry["id"] == MODEL),
        "tokenization": tokenization,
        "chat_template_caps": props.get("chat_template_caps"),
        "default_n_probs": props.get("default_generation_settings", {}).get("params", {}).get("n_probs"),
        "native_observations": {
            "chat_completions": True,
            "tokenize_endpoint": True,
            "schema_or_grammar_constraints": True,
            "top_token_logprobs": True,
            "constraint_probability_warning": "grammar filters the candidate set, so constrained probabilities are conditional and not an unbiased original-label distribution",
        },
    }


def build_prompt(case: dict, condition: dict) -> tuple[str, str]:
    labels = condition["labels"]
    system = (
        "Classify whether two passages are materially equivalent. Return exactly one token. "
        f"{labels['equivalent']} = materially equivalent; "
        f"{labels['different']} = materially different; "
        f"{labels['insufficient']} = insufficient context."
    )
    a, b = (case["b"], case["a"]) if condition["reverse"] else (case["a"], case["b"])
    return system, f"A: {a}\nB: {b}"


def _candidate_logprobs(choice: dict) -> dict[str, float | None]:
    content = choice.get("logprobs", {}).get("content") or []
    if not content:
        return {label: None for label in ("0", "1", "2")}
    values = {entry.get("token"): entry.get("logprob") for entry in content[0].get("top_logprobs", [])}
    return {label: values.get(label) for label in ("0", "1", "2")}


def run_probe(base_url: str, out_dir: Path, *, split: str = "dev") -> dict:
    assert_development_split(split)
    if split != "dev":
        raise ValueError("Experiment C is frozen to the permitted dev smoke set")
    if out_dir.exists():
        raise FileExistsError(f"refusing to overwrite immutable artifact directory {out_dir}")
    call_budget = len(CASES) * len(CONDITIONS)
    if call_budget > MAX_CALLS:
        raise ValueError(f"probe needs {call_budget} calls, above ceiling {MAX_CALLS}")
    inspected = inspect_capabilities(base_url)
    started = time.monotonic()
    records = []
    for condition in CONDITIONS:
        inverse = {label: semantic for semantic, label in condition["labels"].items()}
        for case in CASES:
            system, user = build_prompt(case, condition)
            payload = {
                "model": MODEL,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0, "top_p": 1, "max_tokens": 1, "seed": 20261013,
                "logprobs": True, "top_logprobs": 20, "stream": False,
            }
            call_started = time.monotonic()
            error = response = None
            try:
                response = _request(_endpoint(base_url, "/v1/chat/completions"), body=payload)
            except (OSError, ValueError, urllib.error.URLError) as caught:
                error = f"{type(caught).__name__}: {caught}"
            choice = (response or {}).get("choices", [{}])[0]
            raw = choice.get("message", {}).get("content")
            label = raw if raw in {"0", "1", "2"} else None
            semantic = inverse.get(label) if label else None
            records.append({
                "schema": SCHEMA, "case_id": case["id"], "pair": case["pair"],
                "expected_semantic": case["expected"], "condition": condition["name"],
                "reverse": condition["reverse"], "label_mapping": condition["labels"],
                "prompt": {"system": system, "user": user},
                "prompt_sha256": hashlib.sha256((system + "\n" + user).encode()).hexdigest(),
                "attempt": 1, "max_tokens": 1, "raw_output": raw, "label": label,
                "semantic": semantic, "correct": semantic == case["expected"],
                "candidate_logprobs": _candidate_logprobs(choice),
                "finish_reason": choice.get("finish_reason"), "usage": (response or {}).get("usage"),
                "timings": (response or {}).get("timings"),
                "latency_s": round(time.monotonic() - call_started, 6), "error": error,
            })
    by_key = {(record["case_id"], record["condition"]): record for record in records}
    condition_accuracy = {}
    for condition in CONDITIONS:
        group = [record for record in records if record["condition"] == condition["name"]]
        condition_accuracy[condition["name"]] = sum(record["correct"] for record in group) / len(group)
    order_pairs = (("base", "order_reversed"), ("labels_rotated", "order_reversed_labels_rotated"))
    label_pairs = (("base", "labels_rotated"), ("order_reversed", "order_reversed_labels_rotated"))
    order_stable = [by_key[(case["id"], a)]["semantic"] == by_key[(case["id"], b)]["semantic"]
                    for case in CASES for a, b in order_pairs]
    label_stable = [by_key[(case["id"], a)]["semantic"] == by_key[(case["id"], b)]["semantic"]
                    for case in CASES for a, b in label_pairs]
    candidate_complete = sum(all(value is not None for value in record["candidate_logprobs"].values()) for record in records)
    valid = sum(record["label"] is not None and record["error"] is None for record in records)
    result = {
        "schema": SCHEMA, "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "split": split, "scope": "capability probe only", "model": MODEL,
        "model_sha256": MODEL_SHA256, "llama_cpp_commit": LLAMA_COMMIT,
        "budget": {"ceiling": MAX_CALLS, "planned": call_budget, "actual": len(records), "attempts_per_condition": 1},
        "capabilities": inspected, "counts": {"valid_one_token": valid, "calls": len(records),
                                                 "candidate_distributions_complete": candidate_complete},
        "condition_accuracy": condition_accuracy,
        "order_semantic_stability": sum(order_stable) / len(order_stable),
        "label_permutation_semantic_stability": sum(label_stable) / len(label_stable),
        "latency": {"wall_s": round(time.monotonic() - started, 6),
                    "sum_call_s": round(sum(record["latency_s"] for record in records), 6),
                    "median_call_s": sorted(record["latency_s"] for record in records)[len(records) // 2]},
        "verdict": "operational_but_not_benchmark_ready" if
                   valid == len(records) and candidate_complete == len(records) else
                   "not_operational",
        "interpretation": (
            "Native unconstrained one-token scoring is operational, but this tiny probe does not "
            "validate a benchmark method: semantic decisions changed under both order reversal and "
            "label permutation. Unconstrained first-token logprobs are comparable across labels only "
            "when all candidates are returned; grammar-constrained probabilities would be conditional "
            "on the grammar."
        ),
    }
    out_dir.mkdir(parents=True)
    raw_path = out_dir / "raw.jsonl"
    raw_path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
    result_path = out_dir / "results.json"
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    checksums = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (raw_path, result_path)}
    (out_dir / "checksums.json").write_text(json.dumps(checksums, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:11436")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--split", default="dev")
    args = parser.parse_args()
    result = run_probe(args.base_url, args.out, split=args.split)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
