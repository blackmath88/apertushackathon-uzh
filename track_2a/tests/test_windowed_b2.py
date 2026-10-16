import json
import tempfile
import unittest
from pathlib import Path

from uzh_rsd.backends import Generation
from uzh_rsd.data_adapter import InferenceInput
from uzh_rsd.tokens import tokenize
from uzh_rsd.windowed_b2 import (METHOD_VERSION, align_windows, execute_document,
                                 plan_document, replay_document, split_windows)


def item(text_a: str, text_b: str, identifier: str = "admin_de_900") -> InferenceInput:
    return InferenceInput(identifier, "de", tokenize(text_a), tokenize(text_b), "", "")


class QueueBackend:
    def __init__(self, generations):
        self.generations = list(generations)
        self.calls = 0

    def generate(self, prompt, max_new_tokens):
        result = self.generations[self.calls]
        self.calls += 1
        return result


class PlanningTests(unittest.TestCase):
    def test_sentence_windows_are_bounded_overlap_and_cover_exact_indices(self):
        tokens = tuple(f"word{i}{'.' if i % 53 == 52 else ''}" for i in range(901))
        windows = split_windows(tokens, side="a")
        self.assertTrue(all(len(window.tokens) <= 320 for window in windows))
        self.assertEqual({i for window in windows for i in range(window.start, window.end)}, set(range(len(tokens))))
        self.assertTrue(all(windows[i + 1].start < windows[i].end for i in range(len(windows) - 1)))
        self.assertTrue(all(window.tokens == tokens[window.start:window.end] for window in windows))

    def test_shared_anchor_can_pair_reordered_windows(self):
        # Force three windows. The numbered anchors appear in reverse order on B.
        a = tuple(["Section", "111"] + ["alpha"] * 318 + ["Section", "222"] + ["beta"] * 318)
        b = tuple(["Abschnitt", "222"] + ["beta"] * 318 + ["Abschnitt", "111"] + ["alpha"] * 318)
        left, right = split_windows(a, side="a"), split_windows(b, side="b")
        pairs = align_windows(left, right, left_total=len(a), right_total=len(b))
        anchored = [(p.left.index, p.right.index) for p in pairs if p.shared_anchors]
        self.assertIn((0, 1), anchored)
        self.assertIn((1, 0), anchored)

    def test_bidirectional_plan_covers_asymmetric_sides(self):
        doc = item(" ".join(["English"] * 40), " ".join([f"Deutsch{i}." for i in range(900)]))
        pairs = plan_document(doc)
        self.assertEqual({i for p in pairs for i in range(p.left.start, p.left.end)}, set(range(len(doc.text_a))))
        self.assertEqual({i for p in pairs for i in range(p.right.start, p.right.end)}, set(range(len(doc.text_b))))


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = Path(self.tmp.name) / "ledger.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_explicit_no_difference_is_complete_processed_zero(self):
        doc = item("The deadline is 30 days .", "Die Frist beträgt 30 Tage .")
        backend = QueueBackend([Generation('{"differences": []}', prompt_tokens=100, completion_tokens=6,
                                           finish_reason="stop", latency_s=1.2)])
        result = execute_document(backend, doc, self.ledger, run_id="r")
        self.assertEqual((result["status"], result["method"]), ("complete", METHOD_VERSION))
        self.assertEqual(result["labels_a"], [0.0] * len(doc.text_a))
        self.assertEqual(result["processed_tokens_a"], len(doc.text_a))
        events = [json.loads(line)["event"] for line in self.ledger.read_text().splitlines()]
        self.assertEqual(events, ["intent", "return"])

    def test_overlap_merges_max_at_original_indices_and_replays_identically(self):
        tokens = [f"t{i}" for i in range(350)]
        doc = item(" ".join(tokens), " ".join(tokens))
        pairs = plan_document(doc)
        generations = []
        for pair in pairs:
            target = pair.left.tokens[0]
            generations.append(Generation(json.dumps({"differences": [{"a": target, "b": target,
                                                                         "kind": "CHANGE", "severity": 3}]}),
                                          finish_reason="stop", latency_s=0.1))
        result = execute_document(QueueBackend(generations), doc, self.ledger, run_id="r")
        self.assertEqual(result["status"], "complete")
        rows = [json.loads(line) for line in self.ledger.read_text().splitlines()]
        replay = replay_document(doc, rows)
        self.assertEqual(replay["labels_a"], result["labels_a"])
        self.assertEqual(replay["labels_b"], result["labels_b"])

    def test_truncated_or_unlocatable_response_fails_without_vectors(self):
        doc = item("One two three .", "Eins zwei drei .")
        cases = [
            Generation('{"differences": []}', finish_reason="length"),
            Generation('{"differences":[{"a":"not present","b":"","kind":"OMISSION","severity":5}]}',
                       finish_reason="stop"),
        ]
        for number, generation in enumerate(cases):
            with self.subTest(number=number):
                ledger = Path(self.tmp.name) / f"ledger-{number}.jsonl"
                result = execute_document(QueueBackend([generation]), doc, ledger, run_id="r")
                self.assertEqual(result["status"], "incomplete")
                self.assertIsNone(result["labels_a"])
                self.assertIn("unprocessed_tokens", " ".join(result["problems"]))

    def test_deadline_after_intent_makes_uncertain_request_visible_and_does_not_call(self):
        doc = item("One two .", "Eins zwei .")
        backend = QueueBackend([])
        result = execute_document(backend, doc, self.ledger, run_id="r", total_deadline=0.0, clock=lambda: 1.0)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(backend.calls, 0)
        rows = [json.loads(line) for line in self.ledger.read_text().splitlines()]
        self.assertEqual([row["event"] for row in rows], ["intent"])


if __name__ == "__main__":
    unittest.main()
