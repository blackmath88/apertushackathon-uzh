import json
import tempfile
import unittest
from pathlib import Path

from uzh_rsd.data_adapter import InferenceInput
from uzh_rsd.staged_comparison import P1_BLOCK, _ledger_state, _strata, render_candidate
from uzh_rsd.tokens import tokenize


class StagedComparisonTests(unittest.TestCase):
    def test_strata_remainder_is_deterministic(self):
        groups = [{"group_key": f"g{i:03}", "max_combined_official_tokens": i} for i in range(163)]
        result = _strata(list(reversed(groups)))
        self.assertEqual({name: len(rows) for name, rows in result.items()}, {"short": 55, "medium": 54, "long": 54})
        self.assertEqual(result["short"][0]["group_key"], "g000")
        self.assertEqual(result["long"][-1]["group_key"], "g162")

    def test_c1_is_single_bounded_insertion(self):
        item = InferenceInput("admin_de_1", "de", tokenize("A text ."), tokenize("Ein Text ."), "source", "target")
        c0 = render_candidate("C0", item)
        c1 = render_candidate("C1", item)
        self.assertNotIn(P1_BLOCK, c0)
        self.assertEqual(c1.count(P1_BLOCK), 1)
        self.assertEqual(c1.replace(P1_BLOCK + "\n", ""), c0)

    def test_unsettled_intent_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            path.write_text(json.dumps({"event": "intent", "task_key": "C0:x"}) + "\n")
            results, intents = _ledger_state(path)
            self.assertEqual(results, {})
            self.assertEqual(intents, {"C0:x"})

    def test_duplicate_intent_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.jsonl"
            row = json.dumps({"event": "intent", "task_key": "C0:x"})
            path.write_text(row + "\n" + row + "\n")
            with self.assertRaisesRegex(ValueError, "duplicate intent"):
                _ledger_state(path)


if __name__ == "__main__":
    unittest.main()
