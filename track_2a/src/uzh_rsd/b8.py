"""B8 pre-inference validation, scheduling, bounded execution, and evaluation.

This module intentionally contains no HTTP/provider client.  Execution requires
an explicitly injected callable plus a separately approved authorization record.
The committed B8 package is therefore useful for dry runs without making model
calls possible by accident.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

SCHEMA = "uzh-rsd.b8/v1"
RELATIONS = ("equivalent", "commitment", "missing", "incorrect", "unresolved")
REPRESENTATIONS = ("R0", "R1", "R2", "R3")
CONTROLS = ("passage_reversed", "labels_permuted", "source_ablated", "counterpart_shuffled")
BASE_LABEL_MAP = dict(zip(RELATIONS, "ABCDE"))
PERMUTED_LABEL_MAP = dict(zip(RELATIONS, "CDEAB"))
REQUIRED_STUDENT = {
    "gguf_sha256": "dea904ad80cd725ec89962abae464477f5d8114d1f4377514f381f7dc2ed202d",
    "llama_cpp_commit": "7ab4ee7",
    "endpoint": "http://127.0.0.1:11436",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def attest_student(model_path: Path, *, llama_cpp_commit: str, endpoint: str) -> dict:
    """Create a local, fail-closed identity attestation without starting a server."""
    identity = {
        "gguf_sha256": sha256(model_path),
        "llama_cpp_commit": llama_cpp_commit,
        "endpoint": endpoint.rstrip("/"),
    }
    for key, expected in REQUIRED_STUDENT.items():
        if identity[key] != expected:
            raise ValueError(f"student identity mismatch: {key}")
    return {**identity, "model_path": str(model_path.resolve()), "model_bytes": model_path.stat().st_size, "attested": True}


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Sequence[Mapping]) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_freeze(package: Path) -> dict:
    manifest = _read_json(package / "freeze-manifest.json")
    failures = []
    for relative, expected in manifest["files"].items():
        path = package / relative
        actual = sha256(path) if path.is_file() else None
        if actual != expected:
            failures.append({"path": relative, "expected": expected, "actual": actual})
    if manifest.get("case_sha256") != manifest["files"].get("synthetic-cases.json"):
        failures.append({"path": "case_sha256", "error": "does not match file map"})
    if manifest.get("family_sha256") != manifest["files"].get("families.json"):
        failures.append({"path": "family_sha256", "error": "does not match file map"})
    if failures:
        raise ValueError(f"B8 freeze mismatch: {failures}")
    return manifest


def _validate_offsets(case: Mapping) -> None:
    for side, offset_name in (("source", "source_focus"), ("counterpart", "counterpart_focus")):
        sentence = case[side]["sentence"]
        focus = case[side]["focus"]
        span = case["offsets"][offset_name]
        if span.get("unit") != "unicode_codepoints":
            raise ValueError(f"{case['case_id']}: unsupported offset unit")
        if not (isinstance(span.get("start"), int) and isinstance(span.get("end"), int)):
            raise ValueError(f"{case['case_id']}: offsets must be integers")
        if sentence[span["start"] : span["end"]] != focus or span.get("exact") != focus:
            raise ValueError(f"{case['case_id']}: {offset_name} does not round trip")


def _validate_commitment(value: Mapping, case_id: str) -> None:
    fields = {"actor", "action", "modality", "polarity", "condition", "quantity", "deadline", "exception"}
    if set(value) != fields:
        raise ValueError(f"{case_id}: commitment fields differ from frozen R3 contract")
    if not all(item is None or isinstance(item, str) for item in value.values()):
        raise ValueError(f"{case_id}: invalid commitment value")


def load_package(package: Path) -> tuple[dict, dict, list[dict]]:
    verify_freeze(package)
    protocol = _read_json(package / "protocol.json")
    families_doc = _read_json(package / "families.json")
    cases_doc = _read_json(package / "synthetic-cases.json")
    families = {row["source_family_id"]: row for row in families_doc["families"]}
    cases = cases_doc["cases"]

    if protocol["data"]["case_count"] != len(cases) or len(cases) != 27:
        raise ValueError("B8 requires exactly 27 frozen cases")
    if protocol["data"]["family_count"] != len(families) or len(families) != 9:
        raise ValueError("B8 requires exactly nine source families")
    if tuple(protocol["representations"]) != REPRESENTATIONS:
        raise ValueError("representation contract changed")
    for key, expected in REQUIRED_STUDENT.items():
        if protocol["student"].get(key) != expected:
            raise ValueError(f"student {key} mismatch")

    seen = set()
    family_languages: dict[str, set[str]] = defaultdict(set)
    split_families: dict[str, set[str]] = defaultdict(set)
    for case in cases:
        case_id = case.get("case_id")
        if not case_id or case_id in seen:
            raise ValueError(f"duplicate or missing case id: {case_id}")
        seen.add(case_id)
        family_id = case.get("source_family_id")
        if family_id not in families:
            raise ValueError(f"{case_id}: unknown family")
        family = families[family_id]
        if case.get("split") != family["split"] or case.get("category") != family["category"]:
            raise ValueError(f"{case_id}: family metadata mismatch")
        if case.get("review_status") != "provisionally_reviewed":
            raise ValueError(f"{case_id}: cases must be provisionally reviewed, never human-verified")
        provenance = case.get("provenance", {})
        if provenance.get("protected_test_data_used") is not False:
            raise ValueError(f"{case_id}: protected test provenance is forbidden")
        if provenance.get("origin") != "independently_authored_synthetic":
            raise ValueError(f"{case_id}: unsupported provenance")
        language_pair = case.get("language_pair")
        family_languages[family_id].add(language_pair)
        split_families[case["split"]].add(family_id)
        _validate_offsets(case)
        commitments = case.get("commitments", {})
        if commitments.get("authorship") != "independently_authored_pre_inference":
            raise ValueError(f"{case_id}: R3 may not be model-authored")
        _validate_commitment(commitments.get("source", {}), case_id)
        _validate_commitment(commitments.get("counterpart", {}), case_id)
        if case.get("expected_relation") not in RELATIONS:
            raise ValueError(f"{case_id}: invalid expected relation")

    expected_languages = {"en-de", "en-fr", "en-it"}
    if any(values != expected_languages for values in family_languages.values()):
        raise ValueError("every family must contain one DE, FR, and IT pair")
    if split_families["optimization"] & split_families["evaluation"]:
        raise ValueError("source-family leakage across splits")
    if len(split_families["optimization"]) != 3 or len(split_families["evaluation"]) != 6:
        raise ValueError("unexpected family split")
    return protocol, families_doc, cases


def representation(case: Mapping, name: str) -> dict:
    if name not in REPRESENTATIONS:
        raise ValueError(f"unknown representation: {name}")
    base = {"schema": "uzh-rsd.b8-representation/v1", "case_id": case["case_id"], "representation": name}
    if name == "R0":
        for side, offset_name in (("source", "source_focus"), ("counterpart", "counterpart_focus")):
            span = case["offsets"][offset_name]
            base[side] = {key: span[key] for key in ("start", "end", "unit")}
            base[side]["text"] = span["exact"]
    elif name == "R1":
        base["source_sentence"] = case["source"]["sentence"]
        base["counterpart_sentence"] = case["counterpart"]["sentence"]
    elif name == "R2":
        for side in ("source", "counterpart"):
            base[side] = {
                "heading": case[side]["heading"],
                "governing_condition": case[side]["governing_condition"],
                "sentence": case[side]["sentence"],
            }
    else:
        base["source"] = case["commitments"]["source"]
        base["counterpart"] = case["commitments"]["counterpart"]
        base["authorship"] = case["commitments"]["authorship"]
    return base


def validate_representation(value: Mapping) -> None:
    common = {"schema", "case_id", "representation"}
    name = value.get("representation")
    if value.get("schema") != "uzh-rsd.b8-representation/v1" or name not in REPRESENTATIONS:
        raise ValueError("invalid representation identity")
    expected = {
        "R0": common | {"source", "counterpart"},
        "R1": common | {"source_sentence", "counterpart_sentence"},
        "R2": common | {"source", "counterpart"},
        "R3": common | {"source", "counterpart", "authorship"},
    }[name]
    if set(value) != expected:
        raise ValueError(f"{name}: fields do not match schema")
    if name == "R0":
        for side in ("source", "counterpart"):
            if set(value[side]) != {"text", "start", "end", "unit"} or value[side]["unit"] != "unicode_codepoints":
                raise ValueError("invalid R0 span")
    elif name == "R2":
        for side in ("source", "counterpart"):
            if set(value[side]) != {"heading", "governing_condition", "sentence"}:
                raise ValueError("invalid R2 context")
    elif name == "R3":
        if value["authorship"] != "independently_authored_pre_inference":
            raise ValueError("R3 authorship mismatch")
        _validate_commitment(value["source"], value["case_id"])
        _validate_commitment(value["counterpart"], value["case_id"])


def _render_evidence(value: Mapping, *, reversed_passages: bool = False, source_ablated: bool = False,
                     shuffled_counterpart: Mapping | None = None) -> tuple[str, str]:
    name = value["representation"]
    if name == "R0":
        source = value["source"]["text"]
        counterpart = value["counterpart"]["text"]
    elif name == "R1":
        source, counterpart = value["source_sentence"], value["counterpart_sentence"]
    elif name == "R2":
        def context(side):
            condition = side["governing_condition"] or "<none>"
            return f"HEADING: {side['heading']}\nCONDITION: {condition}\nTEXT: {side['sentence']}"
        source, counterpart = context(value["source"]), context(value["counterpart"])
    else:
        source = json.dumps(value["source"], ensure_ascii=False, sort_keys=True)
        counterpart = json.dumps(value["counterpart"], ensure_ascii=False, sort_keys=True)
    if shuffled_counterpart is not None:
        counterpart = _render_evidence(shuffled_counterpart)[1]
    if source_ablated:
        source = "<SOURCE_ABLATED>"
    if reversed_passages:
        source, counterpart = counterpart, source
    return source, counterpart


def _prompt(value: Mapping, label_map: Mapping[str, str], *, condition: str = "direct",
            shuffled_counterpart: Mapping | None = None, transfer_contract: str | None = None) -> tuple[str, str]:
    source, counterpart = _render_evidence(
        value,
        reversed_passages=condition == "passage_reversed",
        source_ablated=condition == "source_ablated",
        shuffled_counterpart=shuffled_counterpart,
    )
    legend = "; ".join(f"{token}={relation}" for relation, token in label_map.items())
    contract = ""
    if transfer_contract == "deterministic_no_teacher":
        contract = " Compare actor, action, modality, polarity, condition, quantity, deadline, and exception in that order."
    elif transfer_contract == "teacher_generic":
        contract = " Apply only the separately frozen generic teacher contract; do not use case-specific teacher analysis."
    system = f"Classify the semantic relationship. Return exactly one opaque label token. {legend}.{contract}"
    user = f"SOURCE:\n{source}\n\nCOUNTERPART:\n{counterpart}"
    return system, user


def _expected(case: Mapping, condition: str) -> str:
    relation = case["expected_relation"]
    if condition == "source_ablated":
        return "unresolved"
    if condition == "counterpart_shuffled":
        return "incorrect"
    if condition == "passage_reversed" and relation == "missing":
        return "commitment"
    if condition == "passage_reversed" and relation == "commitment":
        return "missing"
    return relation


def _shuffle_map(cases: Sequence[Mapping]) -> dict[str, Mapping]:
    result = {}
    by_language: dict[str, list[Mapping]] = defaultdict(list)
    for case in cases:
        if case["split"] == "evaluation":
            by_language[case["language_pair"]].append(case)
    for language_cases in by_language.values():
        ordered = sorted(language_cases, key=lambda row: row["case_id"])
        for index, case in enumerate(ordered):
            candidate = ordered[(index + 1) % len(ordered)]
            if candidate["source_family_id"] == case["source_family_id"]:
                raise AssertionError("shuffled counterpart stayed in source family")
            result[case["case_id"]] = candidate
    return result


def _plan_row(protocol: Mapping, case: Mapping, model_role: str, rep_name: str, arm: str,
              condition: str = "direct", transfer_contract: str | None = None,
              shuffled_case: Mapping | None = None) -> dict:
    value = representation(case, rep_name)
    shuffled_value = representation(shuffled_case, rep_name) if shuffled_case else None
    label_map = PERMUTED_LABEL_MAP if condition == "labels_permuted" else BASE_LABEL_MAP
    system, user = _prompt(value, label_map, condition=condition, shuffled_counterpart=shuffled_value,
                           transfer_contract=transfer_contract)
    estimated_tokens = math.ceil((len(system) + len(user)) / 3) + 24
    identity = "|".join((arm, model_role, case["case_id"], rep_name, condition, transfer_contract or "none"))
    return {
        "schema": "uzh-rsd.b8-call-plan/v1",
        "call_id": hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24],
        "arm": arm,
        "model_role": model_role,
        "case_id": case["case_id"],
        "source_family_id": case["source_family_id"],
        "split": case["split"],
        "language_pair": case["language_pair"],
        "representation": rep_name,
        "condition": condition,
        "transfer_contract": transfer_contract,
        "expected_relation": _expected(case, condition),
        "label_map": label_map,
        "prompt": {"system": system, "user": user},
        "prompt_sha256": canonical_sha256({"system": system, "user": user}),
        "configuration": {"temperature": 0, "seed": protocol["student"]["seed"], "max_output_tokens": 2},
        "estimated_prompt_tokens": estimated_tokens,
        "projected_wall_seconds": protocol["estimation"]["wall_seconds_per_call"],
        "attempt_limit": 1,
    }


def build_schedule(protocol: Mapping, cases: Sequence[Mapping]) -> list[dict]:
    optimization = [case for case in cases if case["split"] == "optimization"]
    evaluation = [case for case in cases if case["split"] == "evaluation"]
    shuffled = _shuffle_map(cases)
    rows = []
    for case in optimization:
        for rep_name in REPRESENTATIONS:
            rows.append(_plan_row(protocol, case, "teacher", rep_name, "teacher_discovery"))
    for case in evaluation:
        for model_role in ("teacher", "student"):
            for rep_name in REPRESENTATIONS:
                rows.append(_plan_row(protocol, case, model_role, rep_name, "matched_direct"))
    for case in evaluation:
        for model_role in ("teacher", "student"):
            for rep_name in protocol["schedule"]["control_representations"]:
                for condition in CONTROLS:
                    rows.append(_plan_row(protocol, case, model_role, rep_name, "control", condition,
                                          shuffled_case=shuffled[case["case_id"]] if condition == "counterpart_shuffled" else None))
    for case in evaluation:
        for contract in ("deterministic_no_teacher", "teacher_generic"):
            rows.append(_plan_row(protocol, case, "student", "R2", "transfer", transfer_contract=contract))
    validate_schedule(protocol, rows)
    return rows


def schedule_summary(protocol: Mapping, rows: Sequence[Mapping]) -> dict:
    return {
        "schema": "uzh-rsd.b8-schedule-summary/v1",
        "stage": "dry_run_no_model_calls",
        "calls": len(rows),
        "estimated_prompt_tokens": sum(row["estimated_prompt_tokens"] for row in rows),
        "projected_wall_seconds": sum(row["projected_wall_seconds"] for row in rows),
        "ceilings": protocol["ceilings"],
        "by_arm": dict(sorted(Counter(row["arm"] for row in rows).items())),
        "by_model_role": dict(sorted(Counter(row["model_role"] for row in rows).items())),
        "by_representation": dict(sorted(Counter(row["representation"] for row in rows).items())),
        "optimization_families": sorted({row["source_family_id"] for row in rows if row["split"] == "optimization"}),
        "evaluation_families": sorted({row["source_family_id"] for row in rows if row["split"] == "evaluation"}),
        "schedule_sha256": canonical_sha256(list(rows)),
        "first_call_id": rows[0]["call_id"],
        "last_call_id": rows[-1]["call_id"],
        "model_calls_performed": 0,
    }


def validate_schedule(protocol: Mapping, rows: Sequence[Mapping]) -> None:
    if len({row["call_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate call ids")
    expected = protocol["schedule"]["expected_total_calls"]
    if len(rows) != expected:
        raise ValueError(f"schedule has {len(rows)} calls, expected {expected}")
    totals = {
        "total_calls": len(rows),
        "prompt_tokens": sum(row["estimated_prompt_tokens"] for row in rows),
        "wall_seconds": sum(row["projected_wall_seconds"] for row in rows),
    }
    for key, actual in totals.items():
        if actual > protocol["ceilings"][key]:
            raise ValueError(f"schedule exceeds {key}: {actual}")
    if any(row.get("attempt_limit") != 1 for row in rows):
        raise ValueError("B8 permits exactly one attempt per planned call")


def _preflight_authority(protocol: Mapping, rows: Sequence[Mapping], authorization: Mapping,
                         student_identity: Mapping | None, teacher_identity: Mapping | None) -> None:
    if not authorization.get("approved") or not authorization.get("amends_execution_authorized"):
        raise PermissionError("B8 execution requires a separate approved protocol amendment")
    if authorization.get("protocol_sha256") != canonical_sha256(protocol):
        raise PermissionError("authorization is not bound to this protocol")
    roles = {row["model_role"] for row in rows}
    if "student" in roles:
        if student_identity is None:
            raise PermissionError("student identity proof is required")
        for key, expected in REQUIRED_STUDENT.items():
            if student_identity.get(key) != expected:
                raise PermissionError(f"student identity mismatch: {key}")
        if student_identity.get("attested") is not True:
            raise PermissionError("student identity must come from a local attestation")
    if "teacher" in roles:
        if teacher_identity is None or not teacher_identity.get("provider") or not teacher_identity.get("model_revision"):
            raise PermissionError("approved teacher provider and immutable model revision are required")
        if teacher_identity.get("authorization_id") != authorization.get("authorization_id"):
            raise PermissionError("teacher identity is not bound to the authorization")


def run_bounded(protocol: Mapping, rows: Sequence[Mapping], ledger_path: Path,
                call_fn: Callable[[Mapping], Mapping], *, authorization: Mapping,
                student_identity: Mapping | None = None, teacher_identity: Mapping | None = None,
                clock: Callable[[], float] = time.monotonic) -> dict:
    """Execute a frozen plan through an injected callable; no provider client exists here."""
    validate_schedule(protocol, rows)
    _preflight_authority(protocol, rows, authorization, student_identity, teacher_identity)
    if ledger_path.exists():
        raise FileExistsError(ledger_path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    started = clock()
    calls = 0
    prompt_tokens = 0
    with ledger_path.open("x", encoding="utf-8") as stream:
        for row in rows:
            projected_calls = calls + 1
            projected_tokens = prompt_tokens + row["estimated_prompt_tokens"]
            elapsed = clock() - started
            if projected_calls > protocol["ceilings"]["total_calls"]:
                raise RuntimeError("call ceiling reached")
            if projected_tokens > protocol["ceilings"]["prompt_tokens"]:
                raise RuntimeError("prompt-token ceiling reached")
            if elapsed + row["projected_wall_seconds"] > protocol["ceilings"]["wall_seconds"]:
                raise RuntimeError("wall-time ceiling reached")
            call_started = clock()
            error = None
            request = {
                "schema": "uzh-rsd.b8-call-request/v1",
                "call_id": row["call_id"],
                "model_role": row["model_role"],
                "prompt": row["prompt"],
                "configuration": row["configuration"],
            }
            try:
                response = dict(call_fn(request))
            except Exception as exc:  # preserve the single failed attempt, then stop
                response = {}
                error = f"{type(exc).__name__}: {exc}"
            latency = clock() - call_started
            raw_output = response.get("raw_output", "")
            inverse = {token: relation for relation, token in row["label_map"].items()}
            label = inverse.get(raw_output)
            record = {
                "schema": "uzh-rsd.b8-call-ledger/v1",
                "sequence": calls + 1,
                "call_id": row["call_id"],
                "plan_sha256": canonical_sha256(row),
                "request_sha256": canonical_sha256(request),
                "prompt_sha256": row["prompt_sha256"],
                "model_role": row["model_role"],
                "case_id": row["case_id"],
                "source_family_id": row["source_family_id"],
                "split": row["split"],
                "language_pair": row["language_pair"],
                "arm": row["arm"],
                "representation": row["representation"],
                "condition": row["condition"],
                "transfer_contract": row["transfer_contract"],
                "expected_relation": row["expected_relation"],
                "raw_output": raw_output,
                "raw_output_sha256": hashlib.sha256(raw_output.encode("utf-8")).hexdigest(),
                "label": label,
                "valid": label is not None,
                "usage": response.get("usage", {}),
                "latency_seconds": latency,
                "error": error,
                "attempt": 1,
            }
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
            stream.flush()
            calls, prompt_tokens = projected_calls, projected_tokens
            if error is not None:
                raise RuntimeError(f"model call failed after ledger capture: {error}")
    return {
        "calls": calls,
        "estimated_prompt_tokens": prompt_tokens,
        "wall_seconds": clock() - started,
        "ledger_sha256": sha256(ledger_path),
    }


def _accuracy(rows: Sequence[Mapping]) -> float | None:
    return sum(row.get("label") == row.get("expected_relation") for row in rows) / len(rows) if rows else None


def _rate(rows: Sequence[Mapping], predicate: Callable[[Mapping], bool]) -> float | None:
    return sum(bool(predicate(row)) for row in rows) / len(rows) if rows else None


def evaluate_rows(protocol: Mapping, rows: Sequence[Mapping]) -> dict:
    if len({row["call_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate ledger call ids")
    evaluation = [row for row in rows if row.get("split") == "evaluation"]
    groups: dict[tuple, list[Mapping]] = defaultdict(list)
    for row in evaluation:
        groups[(row["model_role"], row["arm"], row["representation"], row.get("condition"), row.get("transfer_contract"))].append(row)
    metrics = []
    for key, values in sorted(groups.items(), key=lambda item: str(item[0])):
        metrics.append({
            "model_role": key[0], "arm": key[1], "representation": key[2], "condition": key[3],
            "transfer_contract": key[4], "count": len(values), "accuracy": _accuracy(values),
            "valid_rate": _rate(values, lambda row: row.get("valid") is True),
            "abstention_rate": _rate(values, lambda row: row.get("label") == "unresolved"),
        })

    index = {(row["model_role"], row["case_id"], row["representation"], row["arm"],
              row.get("condition"), row.get("transfer_contract")): row for row in evaluation}
    baseline = [row for row in evaluation if row["model_role"] == "student" and row["arm"] == "matched_direct" and row["representation"] == "R2"]
    deterministic = [row for row in evaluation if row["arm"] == "transfer" and row.get("transfer_contract") == "deterministic_no_teacher"]
    teacher_transfer = [row for row in evaluation if row["arm"] == "transfer" and row.get("transfer_contract") == "teacher_generic"]

    def stability(condition: str) -> float | None:
        pairs = []
        for direct in baseline:
            control = index.get(("student", direct["case_id"], "R2", "control", condition, None))
            if control:
                pairs.append((direct, control))
        return sum(a.get("label") == b.get("label") for a, b in pairs) / len(pairs) if pairs else None

    label_stability = stability("labels_permuted")
    passage_order_stability = stability("passage_reversed")
    source_controls = [row for row in evaluation if row["model_role"] == "student" and row["arm"] == "control"
                       and row["representation"] == "R2" and row["condition"] == "source_ablated"]
    source_sensitivity = _rate(source_controls, lambda row: row.get("label") == "unresolved")
    transfer_accuracy = _accuracy(teacher_transfer)
    baseline_accuracy = _accuracy(baseline)
    deterministic_accuracy = _accuracy(deterministic)
    transfer_valid = _rate(teacher_transfer, lambda row: row.get("valid") is True)

    family_regressions = {}
    for family in sorted({row["source_family_id"] for row in teacher_transfer}):
        family_teacher = [row for row in teacher_transfer if row["source_family_id"] == family]
        family_base = [row for row in baseline if row["source_family_id"] == family]
        if family_teacher and family_base:
            family_regressions[family] = _accuracy(family_teacher) - _accuracy(family_base)

    complete = all(len(group) == 18 for group in (baseline, deterministic, teacher_transfer))
    checks = {
        "complete_primary_arms": complete,
        "transfer_delta_vs_unchanged": None if not complete else transfer_accuracy - baseline_accuracy,
        "transfer_delta_vs_deterministic": None if not complete else transfer_accuracy - deterministic_accuracy,
        "label_stability": label_stability,
        "passage_order_stability": passage_order_stability,
        "source_sensitivity": source_sensitivity,
        "valid_rate": transfer_valid,
        "worst_family_delta": min(family_regressions.values()) if family_regressions else None,
    }
    thresholds = protocol["thresholds"]
    passed = complete and all((
        checks["transfer_delta_vs_unchanged"] >= thresholds["minimum_transfer_accuracy_delta"],
        checks["transfer_delta_vs_deterministic"] >= thresholds["minimum_transfer_accuracy_delta"],
        label_stability is not None and label_stability >= thresholds["label_stability"],
        passage_order_stability is not None and passage_order_stability >= thresholds["passage_order_stability"],
        source_sensitivity is not None and source_sensitivity >= thresholds["source_sensitivity"],
        transfer_valid is not None and transfer_valid >= thresholds["valid_rate"],
        checks["worst_family_delta"] is not None and checks["worst_family_delta"] >= -thresholds["maximum_family_regression"],
    ))
    verdict = "SUPPORTED" if passed else ("NOT_SUPPORTED" if complete else "INCONCLUSIVE")
    return {
        "schema": "uzh-rsd.b8-evaluation/v1",
        "verdict": verdict,
        "claims": {"apertus_transfer": verdict, "official_benchmark_gain": "NOT_MEASURED"},
        "checks": checks,
        "family_deltas": family_regressions,
        "metrics": metrics,
        "ledger_rows": len(rows),
    }


def write_checksums(paths: Sequence[Path], out_path: Path, *, relative_to: Path) -> None:
    if out_path.exists():
        raise FileExistsError(out_path)
    lines = []
    for path in sorted(paths, key=lambda item: str(item)):
        lines.append(f"{sha256(path)}  {path.relative_to(relative_to)}\n")
    out_path.write_text("".join(lines), encoding="utf-8")


def validate_package(package: Path) -> dict:
    protocol, families, cases = load_package(package)
    for case in cases:
        for name in REPRESENTATIONS:
            validate_representation(representation(case, name))
    return {
        "schema": SCHEMA,
        "status": "valid_pre_inference_package",
        "cases": len(cases),
        "families": len(families["families"]),
        "representations": list(REPRESENTATIONS),
        "execution_authorized": protocol["execution_authorized"],
        "model_calls_performed": 0,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--package", type=Path, required=True)
    schedule = sub.add_parser("schedule")
    schedule.add_argument("--package", type=Path, required=True)
    schedule.add_argument("--out", type=Path)
    schedule.add_argument("--ledger", type=Path)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--package", type=Path, required=True)
    evaluate.add_argument("--ledger", type=Path, required=True)
    evaluate.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.command == "validate":
        result = validate_package(args.package)
    else:
        protocol, _, cases = load_package(args.package)
        if args.command == "schedule":
            rows = build_schedule(protocol, cases)
            result = schedule_summary(protocol, rows)
            if args.ledger:
                _write_jsonl(args.ledger, rows)
            if args.out:
                _write_json(args.out, result)
        else:
            result = evaluate_rows(protocol, _jsonl(args.ledger))
            _write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
