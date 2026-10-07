"""S1-SCALE: similarity (prompt) <-> severity (IR) <-> difference (gold)."""

import math
import unittest

from uzh_rsd.contracts import DifferenceKind, SemanticDifference, TokenSpan
from uzh_rsd.evaluation import OfficialEvaluatorUnavailable, load_official_function
from uzh_rsd.projection import project_differences
from uzh_rsd.severity import (
    severities_to_differences,
    severity_to_difference,
    similarity_to_difference,
    similarity_to_severity,
)

PUBLISHED_TABLE = {5: 0.0, 4: 0.2, 3: 0.4, 2: 0.6, 1: 0.8, 0: 1.0, -1: -1.0}


class ScaleTests(unittest.TestCase):
    def test_published_similarity_table(self):
        for similarity, difference in PUBLISHED_TABLE.items():
            self.assertAlmostEqual(similarity_to_difference(similarity), difference)

    def test_severity_is_mirror_of_similarity(self):
        for step in range(0, 51):
            similarity = step / 10
            self.assertAlmostEqual(severity_to_difference(similarity_to_severity(similarity)), similarity_to_difference(similarity))

    def test_severity_range_maps_to_gold_range(self):
        self.assertEqual(severity_to_difference(0), 0.0)
        self.assertEqual(severity_to_difference(5), 1.0)

    def test_invalid_values_rejected(self):
        for bad in (math.nan, math.inf, -0.1, 5.1, True, "3", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    severity_to_difference(bad)
                with self.assertRaises(ValueError):
                    similarity_to_difference(bad)
        with self.assertRaises(ValueError):
            severity_to_difference(-1)  # punctuation mask is not a severity

    def test_projected_ir_converts_to_official_scale(self):
        difference = SemanticDifference(TokenSpan(1, 3), None, DifferenceKind.OMISSION, 4.0, 0.9)
        source, target = project_differences(4, 2, [difference])
        self.assertEqual(severities_to_differences(source), [0.0, 0.8, 0.8, 0.0])
        self.assertEqual(severities_to_differences(target), [0.0, 0.0])


class OfficialMappingParityTests(unittest.TestCase):
    def setUp(self):
        try:
            self.official = load_official_function("map_label_from_positive_to_negative")
        except OfficialEvaluatorUnavailable as error:
            self.skipTest(str(error))

    def test_matches_pinned_official_function(self):
        for step in range(-10, 51):
            similarity = step / 10
            if -1 < similarity < 0:
                continue
            with self.subTest(similarity=similarity):
                self.assertAlmostEqual(similarity_to_difference(similarity), self.official(similarity))


if __name__ == "__main__":
    unittest.main()
