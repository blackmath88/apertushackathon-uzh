import tempfile
import unittest
from pathlib import Path
from unittest import mock

from uzh_rsd.b4_probe import CASES, CONDITIONS, build_prompt, inspect_capabilities, run_probe
from uzh_rsd.splits import SplitNotAllowedError


class ProbeContractTests(unittest.TestCase):
    def test_budget_balanced_and_one_attempt_conditions(self):
        self.assertEqual(len(CASES), 4)
        self.assertEqual(sum(case["expected"] == "equivalent" for case in CASES), 2)
        self.assertEqual(sum(case["expected"] == "different" for case in CASES), 2)
        self.assertEqual(len(CASES) * len(CONDITIONS), 16)
        self.assertTrue(any(condition["reverse"] for condition in CONDITIONS))
        self.assertGreater(len({tuple(sorted(condition["labels"].items())) for condition in CONDITIONS}), 1)

    def test_prompt_has_no_rationale_or_gold_and_rotates_labels(self):
        system, user = build_prompt(CASES[0], CONDITIONS[2])
        self.assertIn("2 = materially equivalent", system)
        self.assertNotIn("rationale", (system + user).casefold())
        self.assertNotIn("expected", (system + user).casefold())

    def test_endpoint_and_test_split_are_refused_before_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SplitNotAllowedError):
                run_probe("http://127.0.0.1:11436", Path(directory) / "out", split="test")
            with self.assertRaises(ValueError):
                run_probe("http://127.0.0.1:11435", Path(directory) / "out", split="dev")

    def test_tokenization_inspection_precedes_inference(self):
        replies = [
            {"status": "ok"},
            {"data": [{"id": "apertus-v1.5-8b-text-q8_0"}]},
            {"chat_template_caps": {}, "default_generation_settings": {"params": {"n_probs": 0}}},
            {"tokens": [{"id": 1, "piece": "0"}]},
            {"tokens": [{"id": 2, "piece": "1"}]},
            {"tokens": [{"id": 3, "piece": "2"}]},
        ]
        with mock.patch("uzh_rsd.b4_probe._request", side_effect=replies) as request:
            result = inspect_capabilities("http://127.0.0.1:11436")
        self.assertEqual(request.call_count, 6)
        self.assertEqual(result["tokenization"]["2"][0]["piece"], "2")


if __name__ == "__main__":
    unittest.main()
