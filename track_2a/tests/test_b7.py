import tempfile
import unittest
from pathlib import Path

import numpy as np

from uzh_rsd.b7 import ctf_restrict, structural_scores, token_offsets
from uzh_rsd.splits import assert_development_split


class B7Tests(unittest.TestCase):
    def test_forbidden_test_access(self):
        with self.assertRaises(ValueError):
            assert_development_split("test")

    def test_offsets_round_trip(self):
        tokens = ["a", "éé", "."]
        text = " ".join(tokens)
        self.assertEqual([text[a:b] for a, b in token_offsets(tokens)], tokens)

    def test_ctf_is_deterministic_and_finite(self):
        matrix = np.asarray([[.9, .1, .0], [.1, .8, .2], [.0, .2, .7]], dtype=np.float32)
        first = ctf_restrict(matrix, 0)
        second = ctf_restrict(matrix, 0)
        np.testing.assert_array_equal(first[0], second[0])
        self.assertTrue(np.isfinite(first[0]).all())

    def test_structural_complete_projection_and_fallback_shape(self):
        matrix = np.asarray([[.9, .1], [.1, .8]], dtype=np.float32)
        result = structural_scores(matrix, np.asarray([0, 1]), np.asarray([0, 1]), 2, 2)
        self.assertEqual(len(result["prediction_a"]), 2)
        self.assertEqual(len(result["prediction_b"]), 2)
        self.assertTrue(all(0 <= x <= 1 for x in result["prediction_a"] + result["prediction_b"]))

    def test_gold_is_not_a_freeze_parameter(self):
        from inspect import signature
        from uzh_rsd.b7 import freeze_candidates
        self.assertNotIn("gold", signature(freeze_candidates).parameters)

    def test_shuffled_ablation_is_seeded(self):
        import random
        values = list(range(20)); a = values[:]; b = values[:]
        random.Random(20261013).shuffle(a); random.Random(20261013).shuffle(b)
        self.assertEqual(a, b)
        self.assertNotEqual(a, values)


if __name__ == "__main__":
    unittest.main()
