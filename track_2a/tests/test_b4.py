import inspect
import math
import tempfile
import unittest
from pathlib import Path

from uzh_rsd.b4 import (average_precision, diffalign_scores,
                        load_alignment_predictions, oracle_vector, run_oracle,
                        sentence_segments, upstream_url)
from uzh_rsd.data_adapter import InferenceInput
from uzh_rsd.splits import SplitNotAllowedError
from uzh_rsd.tokens import tokenize


class OracleRepresentationTests(unittest.TestCase):
    def test_sentence_boundaries_unicode_punctuation_urls_and_decimals(self):
        tokens = tokenize("Voir https://admin.ch/a.b et 3.14 aujourd’hui . Ça va ? Sì …").tokens
        self.assertEqual(sentence_segments(tokens), [(0, 6), (6, 9), (9, 11)])

    def test_expansion_and_contraction_boundaries(self):
        tokens = tuple("a b c d e f g".split())
        gold = (0.0, 0.0, 0.4, 0.4, 0.4, 0.0, 0.0)
        self.assertEqual(oracle_vector("A5_expand_1", tokens, gold), [0.0, 0.4, 0.4, 0.4, 0.4, 0.4, 0.0])
        self.assertEqual(oracle_vector("A6_contract_1", tokens, gold), [0.0, 0.0, 0.0, 0.4, 0.0, 0.0, 0.0])
        self.assertEqual(oracle_vector("A6_contract_3", tokens, gold), [0.0] * 7)

    def test_score_ties_use_threshold_level_average_precision(self):
        self.assertAlmostEqual(average_precision([1, 1, 0, 0], [1, 0, 1, 0]), 0.5)


class AlignmentContractTests(unittest.TestCase):
    def test_reordered_correspondence_is_order_invariant(self):
        original = diffalign_scores([[0.9, 0.1], [0.2, 0.8]])
        reversed_target = diffalign_scores([[0.1, 0.9], [0.8, 0.2]])
        self.assertEqual(original[0], reversed_target[0])
        self.assertEqual(original[1], list(reversed(reversed_target[1])))

    def test_duplicate_counterparts_are_not_dropped(self):
        left, right = diffalign_scores([[0.8, 0.8], [0.3, 0.3]])
        self.assertEqual([round(value, 6) for value in left], [0.2, 0.7])
        self.assertEqual([round(value, 6) for value in right], [0.2, 0.2])

    def test_missing_counterpart_is_maximally_anomalous(self):
        self.assertEqual(diffalign_scores([[], []]), ([1.0, 1.0], []))

    def test_non_finite_and_ragged_matrices_are_refused(self):
        with self.assertRaises(ValueError):
            diffalign_scores([[0.1], [0.2, 0.3]])
        with self.assertRaises(ValueError):
            diffalign_scores([[math.nan]])

    def test_prediction_loader_has_no_gold_argument(self):
        parameters = inspect.signature(load_alignment_predictions).parameters
        self.assertNotIn("gold", parameters)
        item = InferenceInput("admin_de_1", "de", tokenize("A"), tokenize("B"), "u", "v")
        self.assertFalse(hasattr(item, "labels_a"))


class ExperimentSafetyTests(unittest.TestCase):
    def test_test_split_refused_before_url_or_filesystem_access(self):
        with self.assertRaises(SplitNotAllowedError):
            upstream_url("de", split="test")
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "already-exists"
            out.mkdir()
            with self.assertRaises(SplitNotAllowedError):
                run_oracle(Path(directory) / "missing.json", out, split="test")

    def test_immutable_output_directory_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "artifact"
            out.mkdir()
            with self.assertRaises(FileExistsError):
                run_oracle(Path(directory) / "missing.json", out, split="dev")

    def test_token_offsets_remain_exact(self):
        value = tokenize("Grüezi  30 % — bientôt")
        self.assertEqual([value.text[start:end] for start, end in value.offsets], list(value.tokens))


if __name__ == "__main__":
    unittest.main()
