import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from uzh_rsd.b8 import (
    REQUIRED_STUDENT,
    attest_student,
    build_schedule,
    canonical_sha256,
    evaluate_rows,
    load_package,
    representation,
    run_bounded,
    schedule_summary,
    validate_package,
    validate_representation,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "b8-frontier-apertus-transfer"


class B8Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol, cls.families, cls.cases = load_package(PACKAGE)

    def test_frozen_package_and_case_family_split(self):
        result = validate_package(PACKAGE)
        self.assertEqual(result["cases"], 27)
        self.assertEqual(result["families"], 9)
        self.assertFalse(result["execution_authorized"])
        optimization = {case["source_family_id"] for case in self.cases if case["split"] == "optimization"}
        evaluation = {case["source_family_id"] for case in self.cases if case["split"] == "evaluation"}
        self.assertEqual((len(optimization), len(evaluation)), (3, 6))
        self.assertFalse(optimization & evaluation)
        self.assertTrue(all(case["review_status"] == "provisionally_reviewed" for case in self.cases))
        self.assertTrue(all(case["provenance"]["protected_test_data_used"] is False for case in self.cases))

    def test_offsets_round_trip_for_every_language(self):
        for case in self.cases:
            for side, key in (("source", "source_focus"), ("counterpart", "counterpart_focus")):
                span = case["offsets"][key]
                self.assertEqual(case[side]["sentence"][span["start"]:span["end"]], span["exact"])

    def test_all_representations_match_their_contracts(self):
        for case in self.cases:
            for name in ("R0", "R1", "R2", "R3"):
                value = representation(case, name)
                validate_representation(value)
                self.assertEqual(value["representation"], name)

    def test_schedule_is_deterministic_complete_and_within_ceilings(self):
        first = build_schedule(self.protocol, self.cases)
        second = build_schedule(self.protocol, self.cases)
        self.assertEqual(first, second)
        summary = schedule_summary(self.protocol, first)
        self.assertEqual(summary["calls"], 504)
        self.assertEqual(summary["by_arm"], {
            "control": 288, "matched_direct": 144, "teacher_discovery": 36, "transfer": 36
        })
        self.assertLessEqual(summary["estimated_prompt_tokens"], 120000)
        self.assertLessEqual(summary["projected_wall_seconds"], 2700)
        self.assertEqual(summary["model_calls_performed"], 0)

    def test_shuffled_controls_cross_source_families(self):
        rows = build_schedule(self.protocol, self.cases)
        shuffled = [row for row in rows if row["condition"] == "counterpart_shuffled"]
        self.assertEqual(len(shuffled), 72)
        direct_prompts = {row["case_id"]: row["prompt"]["user"] for row in rows
                          if row["model_role"] == "student" and row["arm"] == "matched_direct" and row["representation"] == "R1"}
        self.assertTrue(all(row["prompt"]["user"] != direct_prompts[row["case_id"]] for row in shuffled if row["representation"] == "R1"))

    def test_runner_rejects_authority_and_identity_before_callback(self):
        rows = build_schedule(self.protocol, self.cases)
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ledger.jsonl"
            with self.assertRaises(PermissionError):
                run_bounded(self.protocol, rows, ledger, lambda row: calls.append(row) or {}, authorization={})
            self.assertEqual(calls, [])
            authorization = {
                "approved": True,
                "amends_execution_authorized": True,
                "authorization_id": "test-only",
                "protocol_sha256": canonical_sha256(self.protocol),
            }
            bad_student = dict(REQUIRED_STUDENT)
            bad_student["endpoint"] = "http://127.0.0.1:9999"
            bad_student["attested"] = True
            teacher = {"provider": "test", "model_revision": "immutable", "authorization_id": "test-only"}
            with self.assertRaises(PermissionError):
                run_bounded(self.protocol, rows, ledger, lambda row: calls.append(row) or {},
                            authorization=authorization, student_identity=bad_student, teacher_identity=teacher)
            self.assertEqual(calls, [])

    def test_local_student_attestation_rejects_wrong_bytes_without_server_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "model.gguf"
            model.write_bytes(b"not-the-frozen-model")
            with self.assertRaisesRegex(ValueError, "gguf_sha256"):
                attest_student(model, llama_cpp_commit="7ab4ee7", endpoint="http://127.0.0.1:11436")

    def test_runner_requires_complete_schedule_and_never_silent_retries(self):
        rows = build_schedule(self.protocol, self.cases)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_bounded(self.protocol, rows[:1], Path(tmp) / "ledger.jsonl", lambda row: {}, authorization={})

    def test_bounded_runner_hides_expected_relation_from_injected_callable(self):
        rows = build_schedule(self.protocol, self.cases)
        seen = []

        def fake_call(request):
            self.assertEqual(set(request), {"schema", "call_id", "model_role", "prompt", "configuration"})
            self.assertNotIn("expected_relation", request)
            seen.append(request["call_id"])
            return {"raw_output": "A", "usage": {"prompt_tokens": 1, "completion_tokens": 1}}

        authorization = {
            "approved": True,
            "amends_execution_authorized": True,
            "authorization_id": "test-only",
            "protocol_sha256": canonical_sha256(self.protocol),
        }
        student = {**REQUIRED_STUDENT, "attested": True}
        teacher = {"provider": "test", "model_revision": "immutable", "authorization_id": "test-only"}
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ledger.jsonl"
            result = run_bounded(self.protocol, rows, ledger, fake_call, authorization=authorization,
                                 student_identity=student, teacher_identity=teacher)
            self.assertEqual(result["calls"], 504)
            self.assertEqual(len(seen), 504)
            self.assertEqual(len(ledger.read_text(encoding="utf-8").splitlines()), 504)

    def test_evaluator_is_inconclusive_for_partial_rows(self):
        rows = build_schedule(self.protocol, self.cases)
        partial = []
        for plan in rows[:3]:
            row = deepcopy(plan)
            row.update({"label": row["expected_relation"], "valid": True})
            partial.append(row)
        result = evaluate_rows(self.protocol, partial)
        self.assertEqual(result["verdict"], "INCONCLUSIVE")
        self.assertEqual(result["claims"]["official_benchmark_gain"], "NOT_MEASURED")

    def test_frozen_manifest_records_case_and_family_hashes(self):
        manifest = json.loads((PACKAGE / "freeze-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["case_sha256"], manifest["files"]["synthetic-cases.json"])
        self.assertEqual(manifest["family_sha256"], manifest["files"]["families.json"])
        self.assertEqual(manifest["model_calls_before_freeze"], 0)


if __name__ == "__main__":
    unittest.main()
