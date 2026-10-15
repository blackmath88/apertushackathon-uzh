import inspect
import tempfile
import unittest
from pathlib import Path

from uzh_rsd.b5_alignment import (match_m0, match_m1, match_m2, match_m3,
                                  official_word_ids, score_b)
from uzh_rsd.splits import SplitNotAllowedError


class MatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        cls.np = np
        cls.similarity = np.asarray([[0.9, 0.1, 0.2], [0.8, 0.3, 0.1], [0.1, 0.2, 0.95]], dtype=float)

    def test_m0_reuses_target_and_is_finite(self):
        a, b, links_a, _links_b = match_m0(self.similarity)
        self.assertEqual(list(links_a), [0, 0, 2])
        self.assertTrue(self.np.isfinite(a).all() and self.np.isfinite(b).all())

    def test_m1_uses_real_reciprocity_and_margin(self):
        a, _b, links_a, _links_b = match_m1(self.similarity)
        self.assertGreater(a[1], 1 - 0.8)
        self.assertEqual(list(links_a), [0, 0, 2])

    def test_m2_capacity_and_explicit_null(self):
        matrix = self.np.asarray([[0.9, 0.1], [0.8, 0.1], [0.1, 0.1]], dtype=float)
        _a, _b, links_a, links_b = match_m2(matrix)
        self.assertEqual(sum(value >= 0 for value in links_a), 1)
        self.assertEqual(sum(value >= 0 for value in links_b), 1)
        self.assertEqual(len(set(value for value in links_a if value >= 0)), 1)

    def test_m3_is_monotone_and_nulls_outside_local_path(self):
        matrix = self.np.asarray([[0.9, 0.1, 0.1], [0.1, 0.9, 0.1], [0.1, 0.1, 0.1]], dtype=float)
        _a, _b, links_a, _links_b = match_m3(matrix)
        paired = [(index, int(value)) for index, value in enumerate(links_a) if value >= 0]
        self.assertEqual(paired, [(0, 0), (1, 1)])
        self.assertEqual(int(links_a[2]), -1)


class SafetyTests(unittest.TestCase):
    def test_model_offsets_map_to_exact_whitespace_positions(self):
        tokens = ["alpha", ".", "2025"]
        self.assertEqual(official_word_ids(tokens, [(0, 0), (0, 5), (5, 6), (6, 7), (8, 12)]),
                         [-1, 0, -1, 1, 2])

    def test_score_refuses_test_before_io(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            with self.assertRaises(SplitNotAllowedError):
                score_b(missing, missing, missing, missing, missing, missing, missing, split="test")

    def test_score_api_has_no_tuning_or_test_argument(self):
        parameters = inspect.signature(score_b).parameters
        self.assertNotIn("null_threshold", parameters)
        self.assertNotIn("gap_open", parameters)


if __name__ == "__main__":
    unittest.main()
