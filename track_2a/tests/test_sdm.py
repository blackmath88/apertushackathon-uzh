import json
import unittest

from uzh_rsd.backends import Generation
from uzh_rsd.data_adapter import InferenceInput
from uzh_rsd.sdm.contracts import ClassifierResponse, DifferenceKind, Relation
from uzh_rsd.sdm.pipeline import (POLICY, build_tasks, classifier_prompt,
                                  project_decisions, segment, validate_response)
from uzh_rsd.sdm.zurich import ZurichPair, adapt
from uzh_rsd.tokens import tokenize


def item(a: str, b: str, *, identifier: str = "admin_de_1") -> InferenceInput:
    return InferenceInput(identifier, "de", tokenize(a), tokenize(b), "https://en", "https://de")


class SegmentationAlignmentTests(unittest.TestCase):
    def test_offsets_are_exact_half_open_and_multilingual_punctuation(self):
        value = tokenize("Grüezi! Ça va? Sì; bene…")
        parts = segment(value.tokens)
        self.assertEqual([(p.start_token, p.end_token) for p in parts], [(0, 1), (1, 3), (3, 4), (4, 5)])
        for part in parts:
            self.assertEqual(part.text, " ".join(value.tokens[part.start_token:part.end_token]))

    def test_cross_lingual_reorder_uses_unique_numeric_anchor(self):
        tasks, diag = build_tasks(item("First 10 days. Then 20 days.", "Dann 20 Tage. Zuerst 10 Tage."))
        self.assertFalse(diag["overflow"])
        self.assertEqual([t.alignment_basis for t in tasks], ["unique_numeric_anchor", "unique_numeric_anchor"])
        self.assertIn("10", tasks[0].right.text)

    def test_duplicate_anchor_is_not_treated_as_unique(self):
        tasks, _ = build_tasks(item("Pay 10 now. Wait 10 days.", "Zahle 10 jetzt. Warte 10 Tage."))
        self.assertTrue(all(t.alignment_basis == "proportional_order" for t in tasks))

    def test_one_to_many_is_explicit(self):
        tasks, _ = build_tasks(item("One unsplit passage", "Erster Satz. Zweiter Satz."))
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].left, tasks[1].left)

    def test_empty_documents_make_no_tasks(self):
        tasks, diag = build_tasks(item("", ""))
        self.assertEqual(tasks, [])
        self.assertEqual(diag["status"], "empty")

    def test_overflow_is_explicit_and_never_truncated(self):
        previous = POLICY["max_tasks_per_document"]
        POLICY["max_tasks_per_document"] = 1
        try:
            tasks, diag = build_tasks(item("A. B.", "C. D."))
        finally:
            POLICY["max_tasks_per_document"] = previous
        self.assertEqual(tasks, [])
        self.assertTrue(diag["overflow"])
        self.assertEqual(diag["required_tasks"], 2)

    def test_numeric_change_routes_structurally(self):
        tasks, _ = build_tasks(item("Deadline 30 days.", "Deadline 60 days."))
        self.assertEqual(tasks[0].route, "structural_numeric")

    def test_qualifier_requires_model(self):
        tasks, _ = build_tasks(item("You may apply.", "You may apply only online."))
        self.assertEqual(tasks[0].route, "model")


class ResponseProjectionTests(unittest.TestCase):
    def test_strict_valid_response(self):
        response, failure = validate_response(Generation('{"relation":"DIFFERENT","kind":"QUALIFICATION_CHANGE"}', finish_reason="stop"))
        self.assertIsNone(failure)
        self.assertEqual(response.kind, DifferenceKind.QUALIFICATION_CHANGE)

    def test_invalid_json_unsupported_extra_and_truncation_are_unresolved(self):
        cases = [
            (Generation("{'relation':'EQUIVALENT','kind':'NONE'}", finish_reason="stop"), "invalid_json"),
            (Generation('{"relation":"SAME","kind":"NONE"}', finish_reason="stop"), "unsupported_label"),
            (Generation('{"relation":"EQUIVALENT","kind":"NONE","offset":1}', finish_reason="stop"), "schema_mismatch"),
            (Generation('{"relation":"EQUIVALENT","kind":"NONE"}', finish_reason="length"), "truncated"),
        ]
        for generation, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(validate_response(generation), (None, expected))

    def test_uncertainty_is_explicit_abstention(self):
        response, failure = validate_response(Generation('{"relation":"UNCERTAIN","kind":"UNKNOWN"}', finish_reason="stop"))
        self.assertIsNone(failure)
        self.assertEqual(response.relation, Relation.UNCERTAIN)

    def test_ambiguous_relation_kind_is_rejected(self):
        self.assertEqual(validate_response(Generation('{"relation":"EQUIVALENT","kind":"OTHER"}', finish_reason="stop")),
                         (None, "ambiguous_relation_kind"))

    def test_exact_vector_lengths_and_unknown_mask(self):
        source = item("One two. Three four.", "Eins zwei. Drei vier.")
        tasks, _ = build_tasks(source)
        projection = project_decisions(source, tasks, [ClassifierResponse(Relation.DIFFERENT, DifferenceKind.OTHER), None])
        self.assertEqual(len(projection["prediction_a"]), len(source.text_a))
        self.assertEqual(len(projection["prediction_b"]), len(source.text_b))
        self.assertFalse(projection["semantic_complete"])
        self.assertEqual(projection["evaluation_default"], 0.0)

    def test_prompt_is_bounded_pair_only_and_contains_no_gold(self):
        source = item("Left passage.", "Rechte Passage.")
        task = build_tasks(source)[0][0]
        prompt = classifier_prompt(task)
        self.assertIn(task.left.text, prompt)
        self.assertIn(task.right.text, prompt)
        self.assertNotIn("offset", prompt.casefold())
        self.assertNotIn("severity", prompt.casefold())
        self.assertNotIn("confidence", prompt.casefold())
        self.assertNotIn("labels_a", prompt)

    def test_task_and_call_limits_are_frozen(self):
        self.assertEqual(POLICY["max_tasks_per_document"], 12)
        self.assertEqual(POLICY["max_calls_total"], 300)
        self.assertEqual(POLICY["max_completion_tokens"], 96)
        tasks, _ = build_tasks(item(" ".join(f"S{i}." for i in range(50)), " ".join(f"T{i}." for i in range(50))))
        self.assertLessEqual(len(tasks), 12)


class ZurichContractTests(unittest.TestCase):
    def test_contract_only_adapter(self):
        result = adapt(ZurichPair("x", "Hello.", "Hallo.", "https://example/en", "https://example/de"))
        self.assertEqual(result.pair, "en-de")
        self.assertEqual(result.text_a.tokens, ("Hello.",))

    def test_unreviewed_pair_refused(self):
        with self.assertRaises(ValueError):
            adapt(ZurichPair("x", "A", "B", "u", "v", pairing="guessed"))


if __name__ == "__main__":
    unittest.main()
