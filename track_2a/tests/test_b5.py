import inspect
import tempfile
import unittest
from pathlib import Path

from uzh_rsd.b5 import candidate_universe, freeze_a, select_groups
from uzh_rsd.splits import SplitNotAllowedError


class SelectorTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "id": "admin_de_1", "side": "a",
            "tokens": ["Alpha", "2025", "x", "Alpha", "z", "end"],
            "anomaly_scores": [0.1, 0.8, 0.2, 0.7, 0.3, 0.4],
        }

    def test_candidate_positions_are_original_and_clipped(self):
        candidates = candidate_universe(self.record)
        self.assertEqual((candidates[0]["start"], candidates[0]["end"]), (0, 3))
        self.assertEqual((candidates[-1]["start"], candidates[-1]["end"]), (3, 6))
        self.assertEqual(candidates[1]["features"]["cue_density"], 3 / 4)

    def test_selection_is_deterministic_and_non_overlapping(self):
        universe = candidate_universe(self.record)
        first = select_groups(universe, "suspicious_v1", 1)
        second = select_groups(universe, "suspicious_v1", 1)
        self.assertEqual(first, second)
        self.assertEqual(first[0]["center"], 1)

    def test_selector_api_has_no_gold_parameter(self):
        self.assertNotIn("gold", inspect.signature(candidate_universe).parameters)
        self.assertNotIn("gold", inspect.signature(freeze_a).parameters)


class SafetyTests(unittest.TestCase):
    def test_test_split_refused_before_io(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SplitNotAllowedError):
                freeze_a(Path(directory) / "missing.jsonl", Path(directory) / "out.json", split="test")

    def test_freeze_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "out.json"
            out.write_text("existing")
            with self.assertRaises(FileExistsError):
                freeze_a(Path(directory) / "missing.jsonl", out)


if __name__ == "__main__":
    unittest.main()
