import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uzh_rsd.backends import Generation
from uzh_rsd.evaluation import load_official_compute_correlations, spearman
from uzh_rsd.full_dev_baseline import (
    CONTEXT_TOKENS,
    OUTPUT_TOKENS,
    PRIVATE_FIELDS,
    build_freeze,
    context_preflight,
    exclusive_runner,
    ledger_state,
    reconcile_unresolved_failure,
    run_resumable,
    validate_backend_contract,
)
from uzh_rsd.splits import SplitNotAllowedError
from uzh_rsd.tokens import tokenize


class FakeBackend:
    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at

    def generate(self, prompt, max_new_tokens):
        self.calls.append((prompt, max_new_tokens))
        if len(self.calls) == self.fail_at:
            return Generation(None, "timeout")
        return Generation("{}", completion_tokens=1, finish_reason="stop")


class FreezeSafetyTests(unittest.TestCase):
    def test_disallowed_split_refused_before_io(self):
        with mock.patch("uzh_rsd.full_dev_baseline.load_split", side_effect=AssertionError("I/O")):
            with self.assertRaises(SplitNotAllowedError):
                build_freeze(split="test", source_data_dir=Path("never"), official_dir=Path("never"), private_dir=Path("never"))

    def test_private_field_contract_covers_gold(self):
        self.assertTrue({"labels_a", "labels_b", "gold_sha256"}.issubset(PRIVATE_FIELDS))

    def test_context_overflow_is_explicit(self):
        plan = [{"id": "x", "prompt_sha256": "h"}]
        result = context_preflight(plan, lambda _text: CONTEXT_TOKENS - OUTPUT_TOKENS + 1, {"h": "synthetic"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["overflow"][0]["required"], CONTEXT_TOKENS + 1)

    def test_timeout_and_runtime_identity_are_frozen(self):
        validate_backend_contract({"backend": "openai-compatible", "endpoint": "http://127.0.0.1:11436",
                                   "model": "Apertus-v1.5-8B-Q8_0", "timeout_s": 600.0, "max_attempts": 1})
        with self.assertRaises(ValueError):
            validate_backend_contract({"backend": "openai-compatible", "endpoint": "http://127.0.0.1:11436",
                                       "model": "Apertus-v1.5-8B-Q8_0", "timeout_s": 601.0, "max_attempts": 1})


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.plan = [
            {"sequence": i, "id": f"synthetic-{i}", "pair": "en-de", "prompt_sha256": f"h{i}",
             "manifest_sha256": "m", "config_sha256": "c", "max_new_tokens": OUTPUT_TOKENS}
            for i in range(3)
        ]
        self.prompts = {f"h{i}": f"synthetic prompt {i}" for i in range(3)}

    def test_one_request_at_a_time_and_failure_pauses(self):
        backend = FakeBackend(fail_at=2)
        result = run_resumable(backend, self.plan, self.prompts, self.tmp)
        self.assertEqual(len(backend.calls), 2)
        self.assertEqual(result["failed_this_invocation"], 1)
        self.assertEqual(result["unstarted"], 1)
        self.assertTrue(all(cap == OUTPUT_TOKENS for _, cap in backend.calls))

    def test_context_overflow_is_resolved_without_endpoint_call(self):
        backend = FakeBackend()
        prompt_tokens = {0: CONTEXT_TOKENS - OUTPUT_TOKENS + 1, 1: 1, 2: 1}
        result = run_resumable(backend, self.plan, self.prompts, self.tmp, prompt_tokens=prompt_tokens)
        self.assertEqual([prompt for prompt, _ in backend.calls], ["synthetic prompt 1", "synthetic prompt 2"])
        self.assertEqual(result["intended_this_invocation"], 3)
        self.assertEqual(result["attempted_this_invocation"], 2)
        self.assertEqual(result["context_overflow_this_invocation"], 1)
        state = ledger_state(self.tmp / "ledger.jsonl")
        self.assertEqual(state["terminal"][0]["status"], "context_overflow")

    def test_resume_only_runs_never_started(self):
        first = FakeBackend(fail_at=2)
        run_resumable(first, self.plan, self.prompts, self.tmp)
        second = FakeBackend()
        result = run_resumable(second, self.plan, self.prompts, self.tmp)
        self.assertEqual(second.calls, [("synthetic prompt 2", OUTPUT_TOKENS)])
        self.assertEqual(result["resolved_total"], 3)

    def test_unresolved_intent_is_never_resent(self):
        ledger = self.tmp / "ledger.jsonl"
        row = {"schema": "uzh-rsd.full-dev-b0-ledger/v1", "event": "intent", **self.plan[0]}
        ledger.write_text(json.dumps(row) + "\n")
        backend = FakeBackend()
        run_resumable(backend, self.plan, self.prompts, self.tmp)
        self.assertEqual([p for p, _ in backend.calls], ["synthetic prompt 1", "synthetic prompt 2"])
        self.assertEqual(ledger_state(ledger)["unresolved"], [0])

    def test_interrupted_intent_can_be_reconciled_without_resend(self):
        ledger = self.tmp / "ledger.jsonl"
        row = {"schema": "uzh-rsd.full-dev-b0-ledger/v1", "event": "intent", **self.plan[0]}
        ledger.write_text(json.dumps(row) + "\n")
        reconcile_unresolved_failure(self.tmp, 0, error="confirmed process exit after host restart")
        state = ledger_state(ledger)
        self.assertEqual(state["unresolved"], [])
        self.assertEqual(state["terminal"][0]["status"], "transport_or_runtime_failure")
        self.assertIsNone(state["terminal"][0]["generation"]["text"])

    def test_raw_response_integrity_is_verified(self):
        run_resumable(FakeBackend(), self.plan[:1], self.prompts, self.tmp)
        ledger = self.tmp / "ledger.jsonl"
        text = ledger.read_text().replace('"text":"{}"', '"text":"tampered"')
        ledger.write_text(text)
        with self.assertRaisesRegex(ValueError, "integrity"):
            ledger_state(ledger)

    def test_lock_refuses_competing_runner(self):
        lock = self.tmp / "runner.lock"
        with exclusive_runner(lock):
            with self.assertRaises(RuntimeError):
                with exclusive_runner(lock):
                    pass


class EvaluatorParityTests(unittest.TestCase):
    def test_pinned_evaluator_parity_on_synthetic_vector(self):
        try:
            official = load_official_compute_correlations()
        except Exception as error:
            self.skipTest(str(error))
        import numpy
        numpy.random.seed(0)
        generator = random.Random(20261014)
        prediction = [round(generator.random(), 3) for _ in range(120)]
        gold = [generator.choice((0.0, 0.0, 0.2, 0.5, 1.0, -1.0)) for _ in range(120)]
        (rho, _interval), _kendall = official(prediction, gold, False)
        kept = [(p, g) for p, g in zip(prediction, gold) if g != -1]
        self.assertAlmostEqual(float(rho), spearman([x[0] for x in kept], [x[1] for x in kept]), places=12)


if __name__ == "__main__":
    unittest.main()
