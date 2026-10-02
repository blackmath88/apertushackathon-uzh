import unittest

from uzh_rsd.contracts import DifferenceKind, SemanticDifference, TokenSpan
from uzh_rsd.projection import project_differences
from uzh_rsd.splits import assert_development_split


class SplitGuardTests(unittest.TestCase):
    def test_dev_is_allowed(self):
        assert_development_split("dev")

    def test_test_is_rejected(self):
        with self.assertRaises(ValueError):
            assert_development_split("test")


class ProjectionTests(unittest.TestCase):
    def test_sparse_difference_projects_deterministically(self):
        difference = SemanticDifference(source=TokenSpan(1, 3), target=TokenSpan(0, 1), kind=DifferenceKind.CHANGE, severity=4.0, confidence=0.9)
        source, target = project_differences(4, 3, [difference])
        self.assertEqual(source, [0.0, 4.0, 4.0, 0.0])
        self.assertEqual(target, [4.0, 0.0, 0.0])

    def test_overlaps_take_max_severity(self):
        differences = [
            SemanticDifference(source=TokenSpan(0, 2), target=None, kind=DifferenceKind.OMISSION, severity=2.0, confidence=0.8),
            SemanticDifference(source=TokenSpan(1, 3), target=None, kind=DifferenceKind.CHANGE, severity=5.0, confidence=0.8),
        ]
        source, _ = project_differences(3, 0, differences)
        self.assertEqual(source, [2.0, 5.0, 5.0])


if __name__ == "__main__":
    unittest.main()
