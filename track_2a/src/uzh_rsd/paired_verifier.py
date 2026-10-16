"""Frozen paired-evidence keep/drop diagnostic for PR #44.

Generation and verification are gold-blind. Development gold is opened only by
``score`` after the immutable request ledger has exactly one result per intent.
The module rejects test before any input access and never overwrites artifacts.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import random
import statistics
import time
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path

from .backends import OpenAICompatibleBackend
from .methods import load_json_object, parse_b2
from .staged_comparison import (
    BOOTSTRAP_REPLICATES,
    BOOTSTRAP_SEED,
    FALLBACK,
    SCHEMA as PARENT_SCHEMA,
    _load_gold,
    _private_inference,
    _score_rows,
    digest,
    file_sha256,
    read_json,
    render_candidate,
    runtime_identity,
    write_json,
)

SCHEMA = "uzh-rsd.paired-verifier/v1"
GENERATOR_MAX_TOKENS = 1024
VERIFIER_MAX_TOKENS = 128
REQUEST_TIMEOUT_S = 600.0
TOTAL_LIMIT_S = 3600.0
CALL_CEILING = 36
AUDIT_IDS = (
    "admin_de_199", "admin_fr_199", "admin_it_199",
    "admin_de_215", "admin_fr_215", "admin_it_215",
    "admin_de_185", "admin_fr_185", "admin_it_185",
)
VERIFIER_INSTRUCTION = """You verify proposed factual differences between two versions of one government page.
Return exactly one JSON object: {"keep":[INDICES]} using zero-based indices from PROPOSED.
Keep an item only when its quoted A/B evidence supports a factual mismatch. Reject faithful translation,
paraphrase, reordering, navigation boilerplate, and claims not supported by both quoted passages.
Do not rewrite evidence, add findings, or change severity. An empty keep list is valid."""


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _append(handle, value: Mapping) -> None:
    handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    handle.flush()


def _selected_rows(package_dir: Path) -> list[dict]:
    subset = read_json(package_dir / "subset-manifest.json")
    executed = {row["id"] for row in subset["validation_execution"]}
    rows = [row for row in subset["validation_pool"] if row["id"] not in executed]
    if len(rows) != 18 or Counter(row["language"] for row in rows) != Counter({"de": 6, "fr": 6, "it": 6}):
        raise ValueError("frozen confirmation sample is not the expected balanced 18")
    return rows


def freeze(package_dir: Path, out_dir: Path, *, base_commit: str, split: str = "dev") -> dict:
    if split != "dev":
        raise ValueError("paired verifier is development-only")
    if out_dir.exists():
        raise FileExistsError(out_dir)
    rows = _selected_rows(package_dir)
    protocol = {
        "schema": SCHEMA, "parent_schema": PARENT_SCHEMA, "status": "frozen_before_inference",
        "split": split, "base_commit": base_commit,
        "sample": rows, "sample_count": len(rows), "audit_ids": list(AUDIT_IDS),
        "generator": {"candidate": "C1", "render": "uzh_rsd.staged_comparison.render_candidate",
                      "max_tokens": GENERATOR_MAX_TOKENS, "temperature": 0.0, "attempts": 1},
        "verifier": {"instruction": VERIFIER_INSTRUCTION,
                     "instruction_sha256": hashlib.sha256(VERIFIER_INSTRUCTION.encode()).hexdigest(),
                     "max_tokens": VERIFIER_MAX_TOKENS, "temperature": 0.0, "attempts": 1,
                     "output_schema": {"keep": "unique zero-based integer indices"}},
        "projection": "unchanged parse_b2 locator/severity/max-overlap projection; treatment filters items by index",
        "failure_policy": "unparseable generator => explicit zero in both arms and no verifier call; invalid verifier => treatment equals control",
        "metrics": ["official macro/per-language Spearman", "paired source-group bootstrap delta", "usable coverage",
                    "kept/dropped items", "verifier validity", "latency", "audit precision/recall"],
        "acceptance": "treatment macro > control macro; usable coverage unchanged; fixed audit precision improves without recall decreasing; otherwise reject",
        "budget": {"call_ceiling": CALL_CEILING, "generator_calls": 18, "verifier_calls_max": 18,
                   "concurrency": 1, "automatic_retries": 0, "total_limit_s": TOTAL_LIMIT_S},
        "exposure": "all 18 cases become exposed to this verifier experiment",
    }
    protocol["protocol_digest"] = digest(protocol)
    out_dir.mkdir(parents=True)
    write_json(out_dir / "protocol.json", protocol)
    write_json(out_dir / "ledger-state.json", {"schema": SCHEMA, "status": "frozen", "protocol_digest": protocol["protocol_digest"]})
    return protocol


def _items(protocol: Mapping, private_source: Path, baseline_manifest: Path):
    manifest = read_json(baseline_manifest)
    items, raw = _private_inference(private_source, manifest)
    lookup = {item.id: item for item in items}
    wanted = [row["id"] for row in protocol["sample"]]
    if set(wanted) - set(lookup):
        raise ValueError("frozen sample missing from private inference data")
    return [lookup[x] for x in wanted], {x: raw[x] for x in wanted}


def _difference_items(text: str | None) -> list[dict] | None:
    if text is None:
        return None
    data, _ = load_json_object(text)
    if data is None or not isinstance(data.get("differences"), list):
        return None
    return data["differences"]


def _verifier_prompt(raw: Mapping, differences: Sequence[Mapping]) -> str:
    proposed = [{"index": i, "a": row.get("a"), "b": row.get("b"), "kind": row.get("kind"),
                 "severity": row.get("severity")} for i, row in enumerate(differences)]
    return (VERIFIER_INSTRUCTION + "\n\nPASSAGE A:\n" + raw["text_a"] + "\n\nPASSAGE B:\n" + raw["text_b"]
            + "\n\nPROPOSED:\n" + json.dumps(proposed, ensure_ascii=False, separators=(",", ":")))


def _parse_keep(text: str | None, size: int) -> tuple[list[int] | None, str]:
    if text is None:
        return None, "call_failed"
    data, mode = load_json_object(text)
    values = None if data is None else data.get("keep")
    if not isinstance(values, list) or any(isinstance(x, bool) or not isinstance(x, int) for x in values):
        return None, "invalid_schema"
    if len(values) != len(set(values)) or any(x < 0 or x >= size for x in values):
        return None, "invalid_indices"
    return sorted(values), mode


def _read_state(path: Path) -> tuple[set[str], dict[str, dict]]:
    intents, results = set(), {}
    if not path.exists():
        return intents, results
    for row in _jsonl(path):
        key = row["task_key"]
        if row["event"] == "intent":
            if key in intents: raise ValueError(f"duplicate intent {key}")
            intents.add(key)
        elif row["event"] == "result":
            if key not in intents or key in results: raise ValueError(f"invalid result {key}")
            results[key] = row
    return intents, results


def run(protocol_dir: Path, private_source: Path, baseline_manifest: Path, run_dir: Path,
        *, base_url: str, model: str, api_key: str, model_path: Path, server_binary: Path) -> dict:
    if run_dir.exists():
        raise FileExistsError(run_dir)
    protocol = read_json(protocol_dir / "protocol.json")
    if protocol.get("protocol_digest") != digest({k: v for k, v in protocol.items() if k != "protocol_digest"}):
        raise ValueError("protocol digest mismatch")
    items, raw = _items(protocol, private_source, baseline_manifest)
    runtime = runtime_identity(model_path, server_binary, base_url)
    run_dir.mkdir(parents=True)
    write_json(run_dir / "runtime-identity.json", runtime)
    backend = OpenAICompatibleBackend(base_url, model, api_key, timeout_s=REQUEST_TIMEOUT_S)
    ledger_path = run_dir / "ledger.jsonl"
    started = time.monotonic(); calls = 0
    with ledger_path.open("x", encoding="utf-8") as ledger:
        for item in items:
            if time.monotonic() - started >= TOTAL_LIMIT_S: raise TimeoutError("experiment time ceiling reached")
            prompt = render_candidate("C1", item); key = f"generate:{item.id}"
            _append(ledger, {"schema": SCHEMA, "event": "intent", "task_key": key, "id": item.id,
                             "kind": "generator", "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                             "created_utc": dt.datetime.now(dt.timezone.utc).isoformat()})
            generation = backend.generate(prompt, GENERATOR_MAX_TOKENS); calls += 1
            _append(ledger, {"schema": SCHEMA, "event": "result", "task_key": key, "id": item.id,
                             "kind": "generator", "generation": generation.as_dict(),
                             "response_sha256": hashlib.sha256((generation.text or "").encode()).hexdigest()})
            differences = _difference_items(generation.text)
            if differences is None:
                continue
            verifier_prompt = _verifier_prompt(raw[item.id], differences); key = f"verify:{item.id}"
            _append(ledger, {"schema": SCHEMA, "event": "intent", "task_key": key, "id": item.id,
                             "kind": "verifier", "items": len(differences),
                             "prompt_sha256": hashlib.sha256(verifier_prompt.encode()).hexdigest(),
                             "created_utc": dt.datetime.now(dt.timezone.utc).isoformat()})
            verification = backend.generate(verifier_prompt, VERIFIER_MAX_TOKENS); calls += 1
            _append(ledger, {"schema": SCHEMA, "event": "result", "task_key": key, "id": item.id,
                             "kind": "verifier", "generation": verification.as_dict(),
                             "response_sha256": hashlib.sha256((verification.text or "").encode()).hexdigest()})
            if calls > CALL_CEILING: raise RuntimeError("call ceiling exceeded")
    intents, results = _read_state(ledger_path)
    if intents != set(results): raise RuntimeError("unsettled intents")
    summary = {"schema": SCHEMA, "status": "settled", "calls": calls, "scheduled_max": CALL_CEILING,
               "wall_s": round(time.monotonic() - started, 3), "ledger_sha256": file_sha256(ledger_path)}
    write_json(run_dir / "run-summary.json", summary)
    return summary


def _bootstrap(groups: Mapping[str, Mapping[str, list]]) -> dict:
    keys = sorted(groups); rng = random.Random(BOOTSTRAP_SEED); deltas=[]; undefined=0
    for _ in range(BOOTSTRAP_REPLICATES):
        picked = [rng.choice(keys) for _ in keys]; control=[]; treatment=[]
        for key in picked:
            control += groups[key]["control"]; treatment += groups[key]["treatment"]
        a, b = _score_rows(treatment)["macro"], _score_rows(control)["macro"]
        if a is None or b is None: undefined += 1
        else: deltas.append(a-b)
    deltas.sort()
    ci = None if not deltas else [deltas[int(.025*(len(deltas)-1))], deltas[int(.975*(len(deltas)-1))]]
    return {"replicates": BOOTSTRAP_REPLICATES, "seed": BOOTSTRAP_SEED, "defined": len(deltas), "undefined": undefined, "ci95": ci}


def score(protocol_dir: Path, private_source: Path, baseline_manifest: Path, run_dir: Path,
          out_dir: Path, audit_path: Path | None = None) -> dict:
    if out_dir.exists(): raise FileExistsError(out_dir)
    if read_json(run_dir / "run-summary.json").get("status") != "settled": raise RuntimeError("run not settled")
    protocol = read_json(protocol_dir / "protocol.json"); items, _ = _items(protocol, private_source, baseline_manifest)
    manifest = read_json(baseline_manifest); gold = _load_gold(private_source, manifest)
    intents, results = _read_state(run_dir / "ledger.jsonl")
    if intents != set(results): raise RuntimeError("ledger not settled")
    rows={"control":[],"treatment":[]}; groups=defaultdict(lambda:{"control":[],"treatment":[]})
    counts=Counter(); predictions=[]; sample={x["id"]:x for x in protocol["sample"]}
    for item in items:
        text=results[f"generate:{item.id}"]["generation"].get("text"); differences=_difference_items(text)
        control=parse_b2(item,text)
        if differences is None:
            keep=None; verify_status="not_run_generator_unparseable"; treatment=control
        else:
            verification=results[f"verify:{item.id}"]["generation"].get("text")
            keep,verify_status=_parse_keep(verification,len(differences))
            filtered=differences if keep is None else [differences[i] for i in keep]
            treatment=parse_b2(item,json.dumps({"differences":filtered},ensure_ascii=False))
            counts["proposed_items"] += len(differences); counts["kept_items"] += len(filtered)
        usable=control.diff_a is not None
        ca=control.diff_a if usable else [FALLBACK]*len(item.text_a); cb=control.diff_b if usable else [FALLBACK]*len(item.text_b)
        ta=treatment.diff_a if usable else [FALLBACK]*len(item.text_a); tb=treatment.diff_b if usable else [FALLBACK]*len(item.text_b)
        for name,a,b in (("control",ca,cb),("treatment",ta,tb)):
            row=(item.language,gold[item.id],a,b); rows[name].append(row); groups[sample[item.id]["group_key"]][name].append(row)
        counts["usable_documents"] += usable; counts["generator_unparseable"] += differences is None
        counts["verifier_valid"] += keep is not None; counts["verifier_invalid"] += differences is not None and keep is None
        predictions.append({"id":item.id,"control_status":control.status,"verifier_status":verify_status,
                            "items":0 if differences is None else len(differences),"keep":keep,
                            "control_a":ca,"control_b":cb,"treatment_a":ta,"treatment_b":tb})
    latencies=[]; prompt_tokens=completion_tokens=0
    for result in results.values():
        generation=result["generation"]
        if generation.get("latency_s") is not None: latencies.append(generation["latency_s"])
        prompt_tokens += generation.get("prompt_tokens") or 0; completion_tokens += generation.get("completion_tokens") or 0
    audit=None
    if audit_path:
        annotations=read_json(audit_path)["annotations"]; tp=fp=fn=tn=uncertain=0
        pred_by_id={row["id"]:row for row in predictions}
        for row in annotations:
            if row["label"] == "uncertain": uncertain += 1; continue
            kept=row["index"] in (pred_by_id[row["id"]]["keep"] or list(range(pred_by_id[row["id"]]["items"])))
            supported=row["label"] == "supported"
            tp += kept and supported; fp += kept and not supported; fn += (not kept) and supported; tn += (not kept) and not supported
        audit={"tp":tp,"fp":fp,"fn":fn,"tn":tn,"uncertain":uncertain,
               "precision":None if tp+fp==0 else tp/(tp+fp),"recall":None if tp+fn==0 else tp/(tp+fn),
               "control_precision":None if tp+fp+fn+tn==0 else (tp+fn)/(tp+fp+fn+tn),"control_recall":1.0}
    out_dir.mkdir(parents=True)
    pred_path=out_dir/"predictions.jsonl"; pred_path.write_text("".join(json.dumps(x,separators=(",",":"))+"\n" for x in predictions))
    cscore,tscore=_score_rows(rows["control"]),_score_rows(rows["treatment"])
    delta=None if cscore["macro"] is None or tscore["macro"] is None else tscore["macro"]-cscore["macro"]
    accepted=bool(delta is not None and delta>0 and counts["usable_documents"]==18 and audit and
                  audit["precision"] is not None and audit["control_precision"] is not None and
                  audit["precision"]>audit["control_precision"] and audit["recall"]>=audit["control_recall"])
    summary={"schema":SCHEMA,"control":cscore,"treatment":tscore,"macro_delta":delta,"bootstrap":_bootstrap(groups),
             "coverage":dict(counts),"audit":audit,"accepted":accepted,"decision":"advance" if accepted else "reject",
             "cost":{"calls":len(results),"prompt_tokens":prompt_tokens,"completion_tokens":completion_tokens,
                     "latency_sum_s":round(sum(latencies),3),"latency_median_s":statistics.median(latencies) if latencies else None,
                     "latency_p95_s":sorted(latencies)[math.ceil(.95*len(latencies))-1] if latencies else None},
             "predictions_sha256":file_sha256(pred_path),"ledger_sha256":file_sha256(run_dir/"ledger.jsonl")}
    write_json(out_dir/"summary.json",summary); return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser=argparse.ArgumentParser(); sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("freeze"); p.add_argument("--package",type=Path,required=True); p.add_argument("--out",type=Path,required=True); p.add_argument("--base-commit",required=True); p.add_argument("--split",default="dev")
    p=sub.add_parser("run"); p.add_argument("--protocol",type=Path,required=True); p.add_argument("--private-source",type=Path,required=True); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--run-dir",type=Path,required=True); p.add_argument("--base-url",required=True); p.add_argument("--model",required=True); p.add_argument("--api-key",default="local-only"); p.add_argument("--model-path",type=Path,required=True); p.add_argument("--server-binary",type=Path,required=True)
    p=sub.add_parser("score"); p.add_argument("--protocol",type=Path,required=True); p.add_argument("--private-source",type=Path,required=True); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--run-dir",type=Path,required=True); p.add_argument("--out-dir",type=Path,required=True); p.add_argument("--audit",type=Path)
    a=parser.parse_args(argv)
    if a.command=="freeze": result=freeze(a.package,a.out,base_commit=a.base_commit,split=a.split)
    elif a.command=="run": result=run(a.protocol,a.private_source,a.manifest,a.run_dir,base_url=a.base_url,model=a.model,api_key=a.api_key,model_path=a.model_path,server_binary=a.server_binary)
    else: result=score(a.protocol,a.private_source,a.manifest,a.run_dir,a.out_dir,a.audit)
    print(json.dumps(result,indent=2,sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
