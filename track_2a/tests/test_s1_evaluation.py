"""S1-EVAL: our evaluator vs the pinned official SwissGov-RSD evaluator.

Every prediction vector in this file is SYNTHETIC (fixed numbers or a seeded
generator). Nothing here is a model result or a benchmark score.
Parity tests skip with an explicit reason unless the pinned official files
have been fetched and nlpstats is installed (`make s1-setup s1-fetch`).
"""

import math
import random
import unittest

from uzh_rsd import data_adapter
from uzh_rsd.data_adapter import GoldLabels, load_split, local_path
from uzh_rsd.evaluation import (
    LanguageResult,
    OfficialEvaluatorUnavailable,
    assemble,
    evaluate_language,
    load_official_compute_correlations,
    macro_average,
    spearman,
)
from uzh_rsd.tokens import LengthMismatchError


def gold(id_, a, b):
    return GoldLabels(id_, tuple(a), tuple(b))


class OurEvaluatorTests(unittest.TestCase):
    def test_hand_computed_spearman(self):
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [1, 2, 3, 4]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        # ties: ranks x=[1.5,1.5,3], y=[1,2,3] -> rho = 0.8660254
        self.assertAlmostEqual(spearman([0.0, 0.0, 1.0], [0.1, 0.2, 0.3]), math.sqrt(3) / 2)

    def test_undefined_cases_return_none_not_a_number(self):
        self.assertIsNone(spearman([0.3, 0.3, 0.3], [0.0, 1.0, 0.5]))
        self.assertIsNone(spearman([0.0, 1.0], [0.4, 0.4]))
        self.assertIsNone(spearman([0.5], [0.5]))
        with self.assertRaises(ValueError):
            spearman([math.nan, 1.0], [0.0, 1.0])

    def test_assembly_masks_gold_punctuation_and_skips_fully_masked_side_b(self):
        items = [
            (gold("d1", [0.0, -1, 1.0], [0.5, -1]), [0.1, 0.9, 0.8], [0.4, 0.0]),
            (gold("d2", [0.2], [-1, -1]), [0.3], []),  # side b fully masked: predictions not needed
        ]
        predictions, gold_values, masked = assemble(items)
        self.assertEqual(predictions, [0.1, 0.8, 0.4, 0.3])
        self.assertEqual(gold_values, [0.0, 1.0, 0.5, 0.2])
        self.assertEqual(masked, 2)

    def test_length_mismatch_is_fatal_not_repaired(self):
        for prediction_a, prediction_b in (([0.1], [0.2, 0.3]), ([0.1, 0.2, 0.3], [0.2, 0.3]), ([0.1, 0.2], [0.2])):
            with self.subTest(a=prediction_a, b=prediction_b), self.assertRaises(LengthMismatchError):
                assemble([(gold("d", [0.0, 1.0], [0.0, 1.0]), prediction_a, prediction_b)])

    def test_macro_requires_all_three_defined_languages(self):
        defined = {language: LanguageResult(language, 1, 10, 0, 0.3) for language in ("de", "fr", "it")}
        self.assertAlmostEqual(macro_average(defined)[0], 0.3)
        partial = dict(defined)
        partial.pop("it")
        self.assertIsNone(macro_average(partial)[0])
        undefined = dict(defined)
        undefined["fr"] = LanguageResult("fr", 1, 10, 0, None, "constant prediction or gold vector")
        value, reason = macro_average(undefined)
        self.assertIsNone(value)
        self.assertIn("fr", reason)

    def test_language_result_reports_reason(self):
        result = evaluate_language("de", [(gold("d", [0.0, 1.0, 0.5], [-1]), [0.2, 0.2, 0.2], [])])
        self.assertIsNone(result.spearman)
        self.assertEqual(result.undefined_reason, "constant prediction or gold vector")


class OfficialParityTests(unittest.TestCase):
    """Executes compute_correlations from the pinned official script."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.official = staticmethod(load_official_compute_correlations())
        except OfficialEvaluatorUnavailable as error:
            raise unittest.SkipTest(str(error))

    def official_spearman(self, predictions, gold_values):
        (rho, _interval), _kendall = self.official(list(predictions), list(gold_values), False)
        return float(rho)

    def test_synthetic_fixture_with_ties_and_masking(self):
        items = [
            (gold("admin_de_0", [0.0, 0.0, 0.0, 0.0, 1.0, -1], [0.0, 0.0, 0.0, 0.0, 1.0, -1]), [0.1, 0.0, 0.0, 0.2, 0.9, 0.5], [0.0, 0.1, 0.1, 0.0, 0.7, 0.0]),
            (gold("admin_de_1", [0.0, 0.0, 0.8, 0.2, 0.0, -1], [0.0, 0.8, 0.0, 0.2, 0.0, -1]), [0.0, 0.0, 0.6, 0.6, 0.1, 0.3], [0.2, 0.6, 0.0, 0.0, 0.0, 0.0]),
            (gold("admin_de_2", [0.0, 0.0, -1, 1.0, 1.0, 1.0, -1], [-1, -1]), [0.0, 0.2, 0.0, 0.8, 0.8, 0.4, 0.0], []),
        ]
        predictions, gold_values, _ = assemble(items)
        # The official function masks gold -1 itself; feed it the unmasked concatenation.
        raw_predictions, raw_gold = [], []
        for labels, prediction_a, prediction_b in items:
            raw_predictions += prediction_a
            raw_gold += labels.labels_a
            if not all(label == -1 for label in labels.labels_b):
                raw_predictions += prediction_b
                raw_gold += labels.labels_b
        self.assertAlmostEqual(spearman(predictions, gold_values), self.official_spearman(raw_predictions, raw_gold), places=12)

    def test_seeded_random_vectors_including_heavy_ties(self):
        generator = random.Random(20261007)
        for trial in range(25):
            size = generator.randint(5, 400)
            gold_values = [generator.choice([-1, 0.0, 0.0, 0.0, 0.2, 0.5, 1.0]) for _ in range(size)]
            if sum(1 for g in gold_values if g != -1) < 3 or len({g for g in gold_values if g != -1}) < 2:
                continue
            predictions = [round(generator.random(), generator.choice([1, 3])) for _ in range(size)]
            kept = [(p, g) for p, g in zip(predictions, gold_values) if g != -1]
            if len({p for p, _ in kept}) < 2:
                continue
            ours = spearman([p for p, _ in kept], [g for _, g in kept])
            with self.subTest(trial=trial):
                self.assertAlmostEqual(ours, self.official_spearman(predictions, gold_values), places=12)

    def test_official_cannot_score_constant_predictions(self):
        # Observed with the pinned code under both numpy 2.0.2/scipy 1.13.1 and the S1 lock:
        # nlpstats' bootstrap receives only NaN samples and np.percentile raises.
        with self.assertRaises(IndexError):
            self.official([0.3, 0.3, 0.3, 0.3], [0.0, 1.0, 0.5, 0.2], False)
        self.assertIsNone(spearman([0.3, 0.3, 0.3, 0.3], [0.0, 1.0, 0.5, 0.2]))

    @unittest.skipUnless(all(local_path("dev", language).exists() for language in data_adapter.LANGUAGES), "pinned dev files not fetched")
    def test_real_dev_gold_with_synthetic_predictions_per_language_and_macro(self):
        results, official = {}, {}
        for language in data_adapter.LANGUAGES:
            generator = random.Random(f"s1-parity-{language}")
            items, raw_predictions, raw_gold = [], [], []
            for _inference, labels in load_split("dev", language)[:40]:
                prediction_a = [generator.random() for _ in labels.labels_a]
                prediction_b = [generator.random() for _ in labels.labels_b]
                items.append((labels, prediction_a, prediction_b))
                raw_predictions += prediction_a
                raw_gold += labels.labels_a
                if not all(label == -1 for label in labels.labels_b):
                    raw_predictions += prediction_b
                    raw_gold += labels.labels_b
            results[language] = evaluate_language(language, items)
            official[language] = self.official_spearman(raw_predictions, raw_gold)
            self.assertAlmostEqual(results[language].spearman, official[language], places=10)
        ours_macro, _ = macro_average(results)
        self.assertAlmostEqual(ours_macro, sum(official.values()) / 3, places=10)


if __name__ == "__main__":
    unittest.main()
