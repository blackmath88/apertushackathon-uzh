import json
import unittest

from uzh_rsd.data_adapter import InferenceInput
from uzh_rsd.evaluation import OfficialEvaluatorUnavailable, load_official_function
from uzh_rsd.methods import extract_json_str, load_json_object, locate, parse_b0, parse_b2
from uzh_rsd.prompts import B2_PROMPT_VERSION, render_b0, render_b2
from uzh_rsd.tokens import tokenize


def item(text_a="The fee is 30 francs .", text_b="Die Gebühr beträgt 60 Franken .", language="de"):
    return InferenceInput(id=f"admin_{language}_1", language=language, text_a=tokenize(text_a), text_b=tokenize(text_b), page_en="en", page_other="o")


TEMPLATE = "Annotate English-German.\n\nSentence 1: {{ sentence1 }}\nSentence 2: {{ sentence2 }}\n\nRespond with the JSON object.\n"


class PromptTests(unittest.TestCase):
    def test_b0_renders_token_lists_like_the_template_examples(self):
        prompt = render_b0(TEMPLATE, item())
        self.assertIn('Sentence 1: ["The", "fee", "is", "30", "francs", "."]', prompt)
        self.assertIn('Sentence 2: ["Die", "Gebühr", "beträgt", "60", "Franken", "."]', prompt)
        self.assertTrue(prompt.endswith("Respond with the JSON object."))  # jinja drops one trailing newline

    def test_b0_template_must_have_each_placeholder_once(self):
        with self.assertRaises(ValueError):
            render_b0("Sentence 1: {{ sentence1 }}", item())

    def test_b2_prompt_contains_texts_and_language(self):
        prompt = render_b2(item(language="fr", text_b="Les frais sont de 60 francs ."))
        self.assertIn("Version B (French):\nLes frais sont de 60 francs .", prompt)
        self.assertIn('{"differences": []}', prompt)
        self.assertTrue(B2_PROMPT_VERSION)

    def test_prompts_carry_no_label_fields(self):
        self.assertFalse(any("label" in field for field in InferenceInput.__dataclass_fields__))


class JsonExtractionTests(unittest.TestCase):
    def test_code_fences_and_preamble_are_stripped_like_upstream(self):
        self.assertEqual(extract_json_str('```json\n{"a": 1}\n```'), '{"a": 1}')
        self.assertEqual(extract_json_str('Here you go: {"a": 1}'), '{"a": 1}')

    def test_python_literal_is_accepted_but_code_is_never_evaluated(self):
        self.assertEqual(load_json_object("{'sentence1': [['a', 5]]}")[0], {"sentence1": [["a", 5]]})
        self.assertIsNone(load_json_object("{'x': __import__('os').system('true')}")[0])

    def test_non_object_json_is_rejected(self):
        self.assertIsNone(load_json_object("[1, 2]")[0])


class B0ParseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.parse_token_labels = staticmethod(load_official_function("parse_token_labels"))
        except OfficialEvaluatorUnavailable as error:
            raise unittest.SkipTest(str(error))

    def b0(self, content, doc=None):
        return parse_b0(doc or item(), content, self.parse_token_labels)

    def test_complete_output_is_strictly_valid_and_mapped(self):
        doc = item()
        content = json.dumps({"sentence1": [[t, 5] for t in doc.text_a.tokens[:3]] + [["30", 1], ["francs", 4], [".", -1]],
                              "sentence2": [[t, 5] for t in doc.text_b.tokens]})
        output = self.b0(content, doc)
        self.assertEqual(output.status, "ok")
        self.assertTrue(output.diagnostics["strict_valid"])
        self.assertEqual([round(v, 6) for v in output.diff_a], [0.0, 0.0, 0.0, 0.8, 0.2, 0.0])
        self.assertEqual(output.diagnostics["a"]["model_punctuation_label"], 1)

    def test_missing_tokens_fall_back_and_are_counted(self):
        output = self.b0(json.dumps({"sentence1": [["The", 0]], "sentence2": []}))
        self.assertEqual(output.status, "ok")
        self.assertFalse(output.diagnostics["strict_valid"])
        self.assertEqual(output.diagnostics["a"]["fallback"], 5)
        self.assertEqual(output.diagnostics["b"]["fallback"], 6)
        self.assertEqual(output.diff_a[0], 1.0)
        self.assertEqual(output.diff_a[1:], [0.0] * 5)

    def test_out_of_range_labels_are_counted_not_used(self):
        output = self.b0(json.dumps({"sentence1": [["The", 9]], "sentence2": []}))
        self.assertEqual(output.diagnostics["a"]["out_of_range"], 1)
        self.assertEqual(output.diff_a[0], 0.0)

    def test_truncated_or_garbage_output_yields_no_vectors(self):
        for content in ('{"sentence1": [["The", 5], ["fee"', "I cannot help with that.", '{"other": 1}'):
            with self.subTest(content=content):
                output = self.b0(content)
                self.assertEqual(output.status, "unparseable")
                self.assertIsNone(output.diff_a)

    def test_failed_call_yields_no_vectors(self):
        output = self.b0(None)
        self.assertEqual(output.status, "call_failed")
        self.assertIsNone(output.diff_a)


class B2ParseTests(unittest.TestCase):
    def test_locate_exact_normalised_missing_and_ambiguous(self):
        tokens = ("the", "Fee", "is", "the", "fee", ".")
        self.assertEqual([(s.start, s.end) for s in locate(tokens, "is the")[0]], [(2, 4)])
        spans, mode = locate(tokens, "THE FEE")
        self.assertEqual((mode, [(s.start, s.end) for s in spans]), ("normalised", [(0, 2), (3, 5)]))
        self.assertEqual(locate(tokens, "price")[1], "not_found")
        self.assertEqual(locate(tokens, "   ")[1], "empty")

    def test_projection_and_counts(self):
        doc = item()
        content = json.dumps({"differences": [
            {"a": "30 francs", "b": "60 Franken", "kind": "CHANGE", "severity": 5},
            {"a": "fee", "b": "", "kind": "WEIRD", "severity": 2},
            {"a": "nonexistent words", "b": "", "kind": "OMISSION", "severity": 3},
            {"a": "The", "b": "Die", "kind": "CHANGE", "severity": 0},
            "not an object",
        ]})
        output = parse_b2(doc, content)
        self.assertEqual(output.status, "ok")
        self.assertEqual(output.diff_a, [0.0, 0.4, 0.0, 1.0, 1.0, 0.0])
        self.assertEqual(output.diff_b, [0.0, 0.0, 0.0, 1.0, 1.0, 0.0])
        diag = output.diagnostics
        self.assertEqual((diag["items"], diag["projected"], diag["unknown_kind"], diag["spans_not_found"], diag["invalid_severity"], diag["invalid_item"]),
                         (5, 2, 1, 1, 1, 1))

    def test_empty_difference_list_is_a_valid_all_equivalent_prediction(self):
        output = parse_b2(item(), '{"differences": []}')
        self.assertEqual(output.status, "ok")
        self.assertEqual(output.diff_a, [0.0] * 6)

    def test_unparseable_and_failed(self):
        self.assertEqual(parse_b2(item(), '{"differences": "none"}').status, "unparseable")
        self.assertEqual(parse_b2(item(), "no json").status, "unparseable")
        self.assertEqual(parse_b2(item(), None).status, "call_failed")


if __name__ == "__main__":
    unittest.main()
