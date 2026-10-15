"""B7 structural control, frozen routing, local verifier, and evaluation.

The generation APIs in this module deliberately accept no gold labels.  Gold is
loaded only by ``evaluate`` after the protocol, candidates, and model evidence
have been frozen on disk.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import time
import urllib.request
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path

from .b4 import _metrics, load_frozen_records
from .b5_alignment import _bootstrap, _official_counterparts, _project
from .splits import assert_development_split

SCHEMA = "uzh-rsd.b7/v1"
SEED = "b7-routing-20261013-v1"
CTF_WIDTH = 8
UPDATE_SCORE = 0.85
RELATIONS = ("equivalent", "commitment", "missing", "incorrect", "unresolved")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Sequence[Mapping]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in rows), encoding="utf-8")


def token_offsets(tokens: Sequence[str]) -> list[list[int]]:
    result, cursor = [], 0
    for token in tokens:
        result.append([cursor, cursor + len(token)])
        cursor += len(token) + 1
    return result


def _argmax_pairs(matrix) -> list[tuple[int, int]]:
    import numpy as np
    fwd, back = np.argmax(matrix, axis=1), np.argmax(matrix, axis=0)
    return [(i, int(j)) for i, j in enumerate(fwd) if int(back[int(j)]) == i and float(matrix[i, int(j)]) > 0]


def ctf_restrict(similarity, width: int = CTF_WIDTH):
    """Pinned NumPy translation of CTFAlign 30f4f89, argmax mode."""
    import numpy as np
    sim = np.asarray(similarity, dtype=np.float32).copy()
    m, n = sim.shape
    block_h, block_w = max(m // 2, 1), max(n // 2, 1)
    allowed = np.ones_like(sim, dtype=bool)
    while block_h >= 1 and block_w >= 1:
        bh, bw = math.ceil(m / block_h), math.ceil(n / block_w)
        final = block_h == 1 and block_w == 1
        if not final and width >= max(bh, bw) - 1:
            block_h, block_w = max(block_h // 2, 1), max(block_w // 2, 1)
            continue
        if final:
            return sim, allowed, _argmax_pairs(sim)
        coarse = np.zeros((bh, bw), dtype=np.float32)
        for i in range(bh):
            for j in range(bw):
                cell = np.maximum(sim[i * block_h:min((i + 1) * block_h, m),
                                      j * block_w:min((j + 1) * block_w, n)], 0)
                coarse[i, j] = float(cell.mean())
        pairs = _argmax_pairs(coarse)
        mask = np.zeros((bh, bw), dtype=bool)
        for i, j in pairs:
            mask[max(i-width, 0):min(i+width+1, bh), max(j-width, 0):min(j+width+1, bw)] = True
        empty_r, empty_c = ~mask.any(1), ~mask.any(0)
        for i, j in zip(*np.where(empty_r[:, None] & empty_c[None, :])):
            mask[max(i-width, 0):min(i+width+1, bh), max(j-width, 0):min(j+width+1, bw)] = True
        expanded = np.repeat(np.repeat(mask, block_h, axis=0), block_w, axis=1)[:m, :n]
        allowed &= expanded
        sim *= expanded
        block_h, block_w = max(block_h // 2, 1), max(block_w // 2, 1)
    raise AssertionError("CTF pyramid did not terminate")


def structural_scores(similarity, word_ids_a, word_ids_b, count_a: int, count_b: int):
    import numpy as np
    restricted, allowed, pairs = ctf_restrict(similarity)
    best_a, best_b = np.max(restricted, axis=1), np.max(restricted, axis=0)
    score_a, score_b = 1 - best_a, 1 - best_b
    cp_a, cp_b = np.full(len(score_a), -1, dtype=np.int32), np.full(len(score_b), -1, dtype=np.int32)
    for i, j in pairs:
        cp_a[i], cp_b[j] = j, i
    return {
        "prediction_a": _project(score_a, word_ids_a, count_a),
        "prediction_b": _project(score_b, word_ids_b, count_b),
        "counterpart_a": _official_counterparts(cp_a, word_ids_a, word_ids_b, count_a),
        "counterpart_b": _official_counterparts(cp_b, word_ids_b, word_ids_a, count_b),
        "allowed_fraction": float(allowed.mean()),
    }


def _lex(token: str) -> str:
    return token.casefold().strip(".,;:!?()[]{}<>\"'«»“”/\\|_-–—")


LEXICAL = {
    "de": {"nicht", "kein", "muss", "darf", "kann", "sofern", "ausser", "bis", "mindestens", "höchstens"},
    "fr": {"ne", "pas", "aucun", "doit", "peut", "si", "sauf", "jusqu", "minimum", "maximum"},
    "it": {"non", "nessun", "deve", "può", "se", "salvo", "fino", "minimo", "massimo"},
    "en": {"not", "no", "must", "shall", "may", "if", "unless", "until", "minimum", "maximum"},
}


def _risk(token: str) -> tuple[float, list[str]]:
    lexical = _lex(token)
    tags = []
    if any(c.isdigit() for c in token): tags.append("quantity_or_date")
    if any(lexical in values for values in LEXICAL.values()): tags.append("constraint_lexeme")
    return (2.0 if "quantity_or_date" in tags else 0.0) + (1.0 if "constraint_lexeme" in tags else 0.0), tags


def _candidate(record_id: str, language: str, side: str, positions: Sequence[int], tokens: Sequence[str],
               target_tokens: Sequence[str], counterparts: Sequence[int], policy: str, rank: int,
               features: Mapping | None = None) -> dict:
    positions = sorted(set(map(int, positions)))
    offsets, target_offsets = token_offsets(tokens), token_offsets(target_tokens)
    anchors = sorted({int(counterparts[i]) for i in positions if 0 <= int(counterparts[i]) < len(target_tokens)})
    target_start, target_end = (min(anchors), max(anchors) + 1) if anchors else (None, None)
    source_start, source_end = min(positions), max(positions) + 1
    identity = f"{record_id}|{side}|{source_start}:{source_end}|{','.join(map(str, positions))}"
    return {
        "candidate_id": hashlib.sha256(identity.encode()).hexdigest()[:20], "document_id": record_id,
        "source_family_id": record_id.rsplit("_", 1)[1], "language_pair": f"en-{language}",
        "source_side": side, "source_token_ids": positions,
        "source_evidence_offsets": [offsets[i] for i in positions],
        "source_text": " ".join(tokens[source_start:source_end]),
        "target_anchor_token_ids": anchors,
        "target_anchor_offsets": [] if target_start is None else [target_offsets[i] for i in range(target_start, target_end)],
        "target_text": "" if target_start is None else " ".join(target_tokens[target_start:target_end]),
        "anchor_method": "CTFAlign-width8-argmax-v1", "anchor_ambiguity": "unavailable" if not anchors else ("valid" if len(anchors) <= len(positions) + 2 else "ambiguous"),
        "risk_features": dict(features or {}), "provenance": [policy], "estimated_model_calls": 1,
        "estimated_score_tokens": len(positions), "policy_rank": rank,
    }


def freeze_candidates(evidence_path: Path, b5_selector_path: Path, cache_dir: Path,
                      cache_provenance_path: Path, out_path: Path, *, split="dev") -> dict:
    assert_development_split(split)
    if out_path.exists(): raise FileExistsError(out_path)
    import numpy as np
    evidence = _jsonl(evidence_path)
    lookup = {(r["id"], r["side"]): r for r in evidence}
    b5 = json.loads(b5_selector_path.read_text(encoding="utf-8"))
    b5_groups = {(r["id"], r["policy"]): r["groups"][:5] for r in b5["selections"]}
    provenance = json.loads(cache_provenance_path.read_text(encoding="utf-8"))
    candidates, routes = {}, []
    for entry in provenance["records"]:
        record_id = entry["id"]
        language = record_id.split("_")[1]
        with np.load(cache_dir / entry["path"]) as z:
            similarity, wa, wb = z["similarity"], z["word_ids_a"], z["word_ids_b"]
        a, b = lookup[(record_id, "a")], lookup[(record_id, "b")]
        structural = structural_scores(similarity, wa, wb, len(a["tokens"]), len(b["tokens"]))
        side_data = {"a": (a["tokens"], b["tokens"], structural["counterpart_a"]),
                     "b": (b["tokens"], a["tokens"], structural["counterpart_b"])}
        r1_positions = defaultdict(set)
        for group in b5_groups[(record_id, "suspicious_v1")]:
            r1_positions[group["side"]].update(range(group["start"], group["end"]))
        required = sum(map(len, r1_positions.values()))
        route_ids = {}
        for policy in ("R1", "R2", "R3"):
            groups = []
            if policy == "R1":
                for group in b5_groups[(record_id, "suspicious_v1")]:
                    groups.append((group["side"], list(range(group["start"], group["end"])), group["features"]))
            else:
                universe = []
                for side, (tokens, target, counterparts) in side_data.items():
                    for i, token in enumerate(tokens):
                        risk, tags = _risk(token)
                        cp = counterparts[i]
                        mismatch = 0.0 if cp < 0 else float(_lex(token) != _lex(target[cp]))
                        key = hashlib.sha256(f"{SEED}|{record_id}|{side}|{i}".encode()).hexdigest()
                        priority = int(key, 16) / (2**256-1) if policy == "R2" else risk + mismatch + 0.05 * float(a["anomaly_scores"][i] if side == "a" else b["anomaly_scores"][i])
                        universe.append((priority, key, side, i, {"risk_tags": tags, "anchor_lexical_mismatch": mismatch}))
                universe.sort(key=lambda x: (-x[0], x[1]))
                chosen = universe[:required]
                for rank, (_, _, side, i, feat) in enumerate(chosen, 1): groups.append((side, [i], feat))
            ids = []
            for rank, (side, positions, feat) in enumerate(groups, 1):
                tokens, target, counterparts = side_data[side]
                row = _candidate(record_id, language, side, positions, tokens, target, counterparts, policy, rank, feat)
                if row["candidate_id"] in candidates:
                    candidates[row["candidate_id"]]["provenance"] = sorted(set(candidates[row["candidate_id"]]["provenance"] + [policy]))
                else: candidates[row["candidate_id"]] = row
                ids.append(row["candidate_id"])
            coverage = sorted({(side, i) for side, positions, _ in groups for i in positions})
            if len(coverage) != required: raise ValueError(f"{record_id} {policy}: unmatched unique-token budget")
            route_ids[policy] = ids
        routes.append({"document_id": record_id, "unique_official_source_token_budget": required, "policies": route_ids})
    result = {
        "schema": SCHEMA, "stage": "gold_blind_candidate_freeze", "split": split,
        "seed": SEED, "ctf_width": CTF_WIDTH, "documents": 30, "candidates": sorted(candidates.values(), key=lambda x: x["candidate_id"]),
        "routes": routes, "sources": {"evidence_sha256": sha256(evidence_path), "b5_selector_sha256": sha256(b5_selector_path),
        "cache_provenance_sha256": sha256(cache_provenance_path)}, "gold_fields_accepted": False,
    }
    _write_json(out_path, result)
    return result


def score_structural(cache_dir: Path, cache_provenance_path: Path, evidence_path: Path, out_path: Path, *, split="dev") -> dict:
    assert_development_split(split)
    if out_path.exists(): raise FileExistsError(out_path)
    import numpy as np
    evidence = _jsonl(evidence_path); lookup = {(r["id"], r["side"]): r for r in evidence}
    provenance = json.loads(cache_provenance_path.read_text(encoding="utf-8")); rows=[]
    started=time.monotonic()
    for entry in provenance["records"]:
        path=cache_dir/entry["path"]
        if sha256(path) != entry["sha256"]: raise ValueError(f"cache hash mismatch: {entry['id']}")
        with np.load(path) as z: result=structural_scores(z["similarity"],z["word_ids_a"],z["word_ids_b"],len(lookup[(entry["id"],"a")]["tokens"]),len(lookup[(entry["id"],"b")]["tokens"]))
        rows.append({"schema":SCHEMA,"arm":"S2","id":entry["id"],**result})
    _write_jsonl(out_path, rows)
    return {"documents":len(rows),"wall_s":time.monotonic()-started}


def _prompt(candidate: Mapping, labels: Mapping[str,str]) -> tuple[str,str]:
    system=("Classify the cross-language relationship. Return exactly one label token. " +
            "; ".join(f"{value}={key}" for key,value in labels.items()) + ".")
    user=f"SOURCE: {candidate['source_text']}\nCOUNTERPART: {candidate['target_text']}"
    return system,user


def _call(base_url: str, model: str, system: str, user: str, max_tokens=4) -> dict:
    payload={"model":model,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"temperature":0,"seed":20261013,"max_tokens":max_tokens}
    req=urllib.request.Request(base_url.rstrip("/")+"/v1/chat/completions",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    started=time.monotonic()
    try:
        with urllib.request.urlopen(req,timeout=60) as response: raw=json.loads(response.read())
        text=raw["choices"][0]["message"]["content"].strip(); error=None
    except Exception as exc:
        raw={}; text=""; error=f"{type(exc).__name__}: {exc}"
    return {"raw_output":text,"response":raw,"latency_s":time.monotonic()-started,"error":error}


def run_candidates(candidate_path: Path, out_path: Path, base_url: str, model: str, *, split="dev") -> dict:
    assert_development_split(split)
    if out_path.exists(): raise FileExistsError(out_path)
    if base_url.rstrip("/") != "http://127.0.0.1:11436": raise ValueError("B7 inference is restricted to 127.0.0.1:11436")
    manifest=json.loads(candidate_path.read_text(encoding="utf-8")); labels=dict(zip(RELATIONS,"01234")); inverse={v:k for k,v in labels.items()}
    rows=[]
    for i,candidate in enumerate(manifest["candidates"],1):
        system,user=_prompt(candidate,labels); call=_call(base_url,model,system,user)
        output=call["raw_output"]; valid=output in inverse
        rows.append({"schema":SCHEMA,"kind":"benchmark_candidate","candidate_id":candidate["candidate_id"],"prompt":{"system":system,"user":user},
                     "configuration":{"temperature":0,"seed":20261013,"max_tokens":4},"label":inverse.get(output),"valid":valid,**call})
        print(f"candidate {i}/{len(manifest['candidates'])}",flush=True)
    _write_jsonl(out_path,rows); return {"calls":len(rows),"valid":sum(r["valid"] for r in rows)}


def run_synthetic(cases_path: Path, out_path: Path, base_url: str, model: str) -> dict:
    if out_path.exists(): raise FileExistsError(out_path)
    if base_url.rstrip("/") != "http://127.0.0.1:11436": raise ValueError("B7 inference is restricted to 127.0.0.1:11436")
    cases=json.loads(cases_path.read_text(encoding="utf-8"))["cases"]; rows=[]
    maps=[dict(zip(RELATIONS,"01234")),dict(zip(RELATIONS,"23401"))]
    for case in cases:
        conditions=[("base",False,0,case["target"]),("passage_reversed",True,0,case["target"]),("labels_permuted",False,1,case["target"]),
                    ("both_reversed",True,1,case["target"]),("unrelated",False,0,case["unrelated"]),("meaning_control",False,0,case["meaning_control"])]
        for condition,reverse,map_id,target in conditions:
            c={"source_text":target if reverse else case["source"],"target_text":case["source"] if reverse else target}
            system,user=_prompt(c,maps[map_id]); call=_call(base_url,model,system,user); inverse={v:k for k,v in maps[map_id].items()}
            rows.append({"schema":SCHEMA,"kind":"synthetic_direct","case_id":case["case_id"],"language_pair":case["language_pair"],"category":case["category"],
                         "condition":condition,"expected":"incorrect" if condition=="unrelated" else case["label"],"prompt":{"system":system,"user":user},
                         "configuration":{"temperature":0,"seed":20261013,"max_tokens":4},"label":inverse.get(call["raw_output"]),"valid":call["raw_output"] in inverse,**call})
        if case.get("alternative"):
            for order in ("AB","BA"):
                a,b=(case["target"],case["alternative"]) if order=="AB" else (case["alternative"],case["target"])
                system="Choose the faithful counterpart to SOURCE. Return exactly A or B."
                user=f"SOURCE: {case['source']}\nA: {a}\nB: {b}"; call=_call(base_url,model,system,user,2)
                expected="A" if order=="AB" else "B"
                rows.append({"schema":SCHEMA,"kind":"synthetic_contrastive","case_id":case["case_id"],"language_pair":case["language_pair"],"category":case["category"],
                             "condition":f"contrastive_{order}","expected":expected,"prompt":{"system":system,"user":user},"configuration":{"temperature":0,"seed":20261013,"max_tokens":2},
                             "label":call["raw_output"] if call["raw_output"] in {"A","B"} else None,"valid":call["raw_output"] in {"A","B"},**call})
    _write_jsonl(out_path,rows); return {"calls":len(rows),"valid":sum(r["valid"] for r in rows)}


def _apply(baseline: Mapping[str,Mapping], manifest: Mapping, decisions: Mapping[str,str], policy: str, *, shuffled=False) -> dict:
    result={k:{"prediction_a":list(v["prediction_a"]),"prediction_b":list(v["prediction_b"])} for k,v in baseline.items()}
    routes={r["document_id"]:r for r in manifest["routes"]}; candidates={c["candidate_id"]:c for c in manifest["candidates"]}
    chosen=[cid for route in manifest["routes"] for cid in route["policies"][policy]]
    decision_values=[decisions.get(cid) for cid in chosen]
    if shuffled:
        rng=random.Random(20261013); rng.shuffle(decision_values)
    for cid,decision in zip(chosen,decision_values):
        if decision not in {"commitment","missing","incorrect"}: continue
        c=candidates[cid]; key=f"prediction_{c['source_side']}"
        for index in c["source_token_ids"]: result[c["document_id"]][key][index]=max(result[c["document_id"]][key][index],UPDATE_SCORE)
    return result


def _route_quality(records, manifest: Mapping, baseline: Mapping, policy: str) -> dict:
    candidates={c["candidate_id"]:c for c in manifest["candidates"]}
    selected=defaultdict(lambda:defaultdict(set))
    for route in manifest["routes"]:
        for cid in route["policies"][policy]:
            c=candidates[cid]; selected[c["document_id"]][c["source_side"]].update(c["source_token_ids"])
    totals=Counter(); per_language=defaultdict(Counter)
    for item,gold in records:
        for side,labels in (("a",gold.labels_a),("b",gold.labels_b)):
            for index,label in enumerate(labels):
                if label == -1: continue
                chosen=index in selected[item.id][side]; positive=label>0
                missed=positive and baseline[item.id][f"prediction_{side}"][index] < .5
                totals.update(all=1, selected=int(chosen), positives=int(positive), selected_positive=int(chosen and positive),
                              missed_positive=int(missed), selected_missed_positive=int(chosen and missed), selected_negative=int(chosen and not positive))
                per_language[item.language].update(all=1,selected=int(chosen),positives=int(positive),selected_positive=int(chosen and positive),
                                                   missed_positive=int(missed),selected_missed_positive=int(chosen and missed),selected_negative=int(chosen and not positive))
    def finish(c):
        return {**c,"unique_token_coverage":c["selected"]/c["all"],"total_positive_recall":c["selected_positive"]/c["positives"],
                "b4_missed_positive_recall":c["selected_missed_positive"]/c["missed_positive"],"selected_negative_burden":c["selected_negative"]/c["selected"]}
    return {"overall":finish(totals),"per_language":{k:finish(v) for k,v in sorted(per_language.items())}}


def _leave_one_family(records, reference, method) -> dict:
    families=sorted({item.id.rsplit("_",1)[1] for item,_ in records}); full=[]
    def macro(rows,pred):
        grouped=defaultdict(list)
        for item,gold in rows: grouped[item.language].append((gold,pred[item.id]["prediction_a"],pred[item.id]["prediction_b"]))
        return _metrics(grouped)["macro_spearman"]
    delta=macro(records,method)-macro(records,reference)
    for family in families:
        subset=[row for row in records if row[0].id.rsplit("_",1)[1]!=family]
        d=macro(subset,method)-macro(subset,reference)
        full.append({"family":family,"delta_without":d,"influence":delta-d})
    full.sort(key=lambda x:abs(x["influence"]),reverse=True)
    return {"full_delta":delta,"families":len(families),"top_absolute_influence":full[:10],"range_without":[min(x["delta_without"] for x in full),max(x["delta_without"] for x in full)]}


def _usage(rows):
    latencies=[r["latency_s"] for r in rows]
    return {"calls":len(rows),"valid":sum(r["valid"] for r in rows),"invalid":sum(not r["valid"] for r in rows),
            "errors":sum(r["error"] is not None for r in rows),"prompt_tokens":sum(r.get("response",{}).get("usage",{}).get("prompt_tokens",0) for r in rows),
            "completion_tokens":sum(r.get("response",{}).get("usage",{}).get("completion_tokens",0) for r in rows),
            "latency_total_s":sum(latencies),"latency_median_s":statistics.median(latencies),"monetary_cost":0}


def evaluate(manifest_path: Path, baseline_path: Path, s1_path: Path, s2_path: Path, evidence_path: Path,
             synthetic_path: Path, frozen_data_path: Path, out_path: Path, *, split="dev") -> dict:
    assert_development_split(split)
    if out_path.exists(): raise FileExistsError(out_path)
    manifest=json.loads(manifest_path.read_text(encoding="utf-8")); baseline={r["id"]:r for r in _jsonl(baseline_path)}
    s1={r["id"]:r for r in _jsonl(s1_path) if r["method"]=="M0"}; s2={r["id"]:r for r in _jsonl(s2_path)}
    evidence_rows=_jsonl(evidence_path); synthetic_rows=_jsonl(synthetic_path)
    decisions={r["candidate_id"]:r.get("label") for r in evidence_rows}
    candidates={c["candidate_id"]:c for c in manifest["candidates"]}
    deterministic={cid:("incorrect" if (c["risk_features"].get("risk_tags") and c["risk_features"].get("anchor_lexical_mismatch")) else "equivalent") for cid,c in candidates.items()}
    arms={"E0":baseline,"E1":s1,"E2":s2,"E3":_apply(baseline,manifest,deterministic,"R3"),"E6_non_apertus":baseline,
          "E5":_apply(baseline,manifest,decisions,"R1",shuffled=True),"E6":_apply(baseline,manifest,decisions,"R1"),
          "E7_random":_apply(baseline,manifest,decisions,"R2"),"E7_routed":_apply(baseline,manifest,decisions,"R3")}
    _m,records=load_frozen_records(frozen_data_path,split=split); grouped_results={}; gold_lookup={i.id:g for i,g in records}
    for name,pred in arms.items():
        grouped=defaultdict(list)
        for item,gold in records: grouped[item.language].append((gold,pred[item.id]["prediction_a"],pred[item.id]["prediction_b"]))
        metrics=_metrics(grouped); metrics["ties"]={side:sum(len(values)-len(set(values)) for values in ([p[item.id][f"prediction_{side}"] for item,_ in records] if False else [])) for side in ()}
        reference = s1 if name=="E2" else baseline
        grouped_results[name]={"metrics":metrics,"bootstrap_vs_comparator":None if name in {"E0","E6_non_apertus"} else _bootstrap(records,reference,pred),
                               "comparator":"E1" if name=="E2" else "E0",
                               "leave_one_family_out":None if name in {"E0","E6_non_apertus"} else _leave_one_family(records,reference,pred),
                               "complete_finite_coverage":all(len(pred[i.id]["prediction_a"])==len(g.labels_a) and len(pred[i.id]["prediction_b"])==len(g.labels_b) and all(math.isfinite(x) for x in pred[i.id]["prediction_a"]+pred[i.id]["prediction_b"]) for i,g in records)}
    syn=synthetic_rows; direct=[r for r in syn if r["kind"]=="synthetic_direct"]
    primary=[r for r in direct if r["condition"]=="base"]; equivalent_fp=[r for r in primary if r["expected"]=="equivalent" and r["label"]!="equivalent"]
    base_by={r["case_id"]:r for r in primary}
    stability={cond:statistics.fmean([base_by[r["case_id"]]["label"]==r["label"] for r in direct if r["condition"]==cond]) for cond in ("passage_reversed","labels_permuted","both_reversed")}
    contrastive=[r for r in syn if r["kind"]=="synthetic_contrastive"]
    syn_summary={"calls":len(syn),"primary_accuracy":statistics.fmean([r["label"]==r["expected"] for r in primary]),
                 "valid_rate":statistics.fmean([r["valid"] for r in syn]),"equivalent_false_positive_rate":len(equivalent_fp)/max(1,sum(r["expected"]=="equivalent" for r in primary)),
                 "stability":stability,"counterpart_sensitivity":statistics.fmean([r["label"]!=base_by[r["case_id"]]["label"] for r in direct if r["condition"]=="unrelated"]),
                 "contrastive_accuracy":statistics.fmean([r["label"]==r["expected"] for r in contrastive]),
                 "per_language_primary_accuracy":{language:statistics.fmean([r["label"]==r["expected"] for r in primary if r["language_pair"]==language]) for language in ("en-de","en-fr","en-it")}}
    thresholds={"primary_accuracy":syn_summary["primary_accuracy"]>=.8,"valid_rate":syn_summary["valid_rate"]>=.98,
                "equivalent_false_positive_rate":syn_summary["equivalent_false_positive_rate"]<=.2,"counterpart_sensitivity":syn_summary["counterpart_sensitivity"]>=.75,
                "stability_each":all(x>=.85 for x in stability.values())}
    syn_summary["thresholds"]=thresholds; syn_summary["gate_passes"]=all(thresholds.values())
    result={"schema":SCHEMA,"stage":"gold_aware_evaluation","arms":grouped_results,"synthetic":syn_summary,
            "decisive_apertus_comparisons":{"actual_vs_shuffled":_bootstrap(records,arms["E5"],arms["E6"]),
                                            "actual_vs_identical_non_apertus":_bootstrap(records,arms["E6_non_apertus"],arms["E6"])},
            "routing_quality":{p:_route_quality(records,manifest,baseline,p) for p in ("R1","R2","R3")},
            "missing_arms":{"E4":"not measured: optional compact comparator was inapplicable within the dependency ceiling"},
            "resource_cost":{"benchmark":_usage(evidence_rows),"synthetic":_usage(synthetic_rows)},
            "model_calls":{"benchmark":len(decisions),"synthetic":len(syn),"total":len(decisions)+len(syn)}}
    _write_json(out_path,result); return result


def make_blind_audit(manifest_path: Path, evidence_path: Path, baseline_path: Path, s2_path: Path,
                     frozen_data_path: Path, out_dir: Path, *, split="dev") -> dict:
    """Freeze a method-blind 5/5/5 audit packet after predictions are fixed."""
    assert_development_split(split)
    if out_dir.exists(): raise FileExistsError(out_dir)
    manifest=json.loads(manifest_path.read_text(encoding="utf-8")); candidates={c["candidate_id"]:c for c in manifest["candidates"]}
    decisions={r["candidate_id"]:r.get("label") for r in _jsonl(evidence_path)}
    baseline={r["id"]:r for r in _jsonl(baseline_path)}; s2={r["id"]:r for r in _jsonl(s2_path)}
    _m,records=load_frozen_records(frozen_data_path,split=split); gold={i.id:g for i,g in records}
    discrepancy=[]
    for cid,c in candidates.items():
        labels=getattr(gold[c["document_id"]],f"labels_{c['source_side']}")
        if decisions.get(cid) in {"commitment","missing","incorrect"} and all(labels[i]<=0 for i in c["source_token_ids"]): discrepancy.append(cid)
    missed=[]
    evidence_lookup={(r["id"],r["side"]):r for r in _jsonl(Path("track_2a/experiments/b4-alignment-first-sdm/alignment-20261013/evidence.jsonl"))}
    for item,g in records:
        for side,labels in (("a",g.labels_a),("b",g.labels_b)):
            for i,label in enumerate(labels):
                if label>0 and baseline[item.id][f"prediction_{side}"][i]<.5 and s2[item.id][f"prediction_{side}"][i]<.5:
                    row=evidence_lookup[(item.id,side)]; other=evidence_lookup[(item.id,"b" if side=="a" else "a")]
                    missed.append({"document_id":item.id,"language_pair":f"en-{item.language}","source_side":side,"source_text":row["tokens"][i],"target_text":" ".join(other["tokens"][:8]),"token_id":i})
    rng=random.Random(20261013); rng.shuffle(discrepancy); rng.shuffle(missed)
    controls=[cid for cid in candidates if decisions.get(cid)=="equivalent"]; rng.shuffle(controls)
    blind=[]; key=[]
    def add(category, payload, metadata):
        aid=f"audit-{len(blind)+1:02d}"; blind.append({"audit_id":aid,"language_pair":payload["language_pair"],"source_passage":payload["source_text"],
            "counterpart_passage":payload["target_text"],"review_fields":{"semantic_difference":"supported|unsupported|unresolved","correspondence":"valid|invalid|unresolved",
            "context_dependency":"low|medium|high","localization_difficulty":"low|medium|high","minimal_original_source_evidence":"text","practical_materiality":"material|immaterial|unresolved"}})
        key.append({"audit_id":aid,"sample_category":category,**metadata})
    for cid in discrepancy[:5]: add("model_discrepancy_absent_official_positive",candidates[cid],{"candidate_id":cid})
    for row in missed[:5]: add("gold_positive_missed_by_all",row,{"document_id":row["document_id"],"side":row["source_side"],"token_id":row["token_id"]})
    for cid in controls[:5]: add("random_control",candidates[cid],{"candidate_id":cid})
    out_dir.mkdir(parents=True); _write_json(out_dir/"blind-review.json",{"schema":"uzh-rsd.b7-audit/v1","method_identity_hidden":True,"items":blind})
    _write_json(out_dir/"audit-key.json",{"schema":"uzh-rsd.b7-audit-key/v1","not_for_blinded_reviewer":True,"items":key})
    return {"items":len(blind),"categories":dict(Counter(x["sample_category"] for x in key))}


def main(argv=None):
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd",required=True)
    f=sub.add_parser("freeze");
    for name in ("evidence","b5-selector","cache","cache-provenance","out"): f.add_argument("--"+name,type=Path,required=True)
    s=sub.add_parser("structural")
    for name in ("cache","cache-provenance","evidence","out"): s.add_argument("--"+name,type=Path,required=True)
    for command in ("run-candidates","run-synthetic"):
        q=sub.add_parser(command); q.add_argument("--input",type=Path,required=True); q.add_argument("--out",type=Path,required=True); q.add_argument("--base-url",required=True); q.add_argument("--model",required=True)
    e=sub.add_parser("evaluate")
    for name in ("manifest","baseline","s1","s2","evidence","synthetic","frozen-data","out"): e.add_argument("--"+name,type=Path,required=True)
    a=sub.add_parser("audit")
    for name in ("manifest","evidence","baseline","s2","frozen-data","out-dir"): a.add_argument("--"+name,type=Path,required=True)
    args=p.parse_args()
    if args.cmd=="freeze": result=freeze_candidates(args.evidence,args.b5_selector,args.cache,args.cache_provenance,args.out)
    elif args.cmd=="structural": result=score_structural(args.cache,args.cache_provenance,args.evidence,args.out)
    elif args.cmd=="run-candidates": result=run_candidates(args.input,args.out,args.base_url,args.model)
    elif args.cmd=="run-synthetic": result=run_synthetic(args.input,args.out,args.base_url,args.model)
    elif args.cmd=="evaluate": result=evaluate(args.manifest,args.baseline,args.s1,args.s2,args.evidence,args.synthetic,args.frozen_data,args.out)
    else: result=make_blind_audit(args.manifest,args.evidence,args.baseline,args.s2,args.frozen_data,args.out_dir)
    print(json.dumps(result,ensure_ascii=False,indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
