import tempfile
import unittest
from collections import Counter
from pathlib import Path

from uzh_rsd.staged_error_analysis import _load_private_rows, _selected_rows


class StagedErrorAnalysisTests(unittest.TestCase):
    def test_fixed_sample_is_balanced_and_uses_first_two_groups(self):
        rows = []
        for stratum in ("short", "medium", "long"):
            for group in range(4):
                for language in ("de", "fr", "it"):
                    rows.append({"id": f"{stratum}-{group}-{language}", "stratum": stratum,
                                 "group_key": f"{stratum}-{group}", "language": language})
        selected = _selected_rows({"validation_execution": rows})
        self.assertEqual(len(selected), 18)
        self.assertEqual(Counter(row["language"] for row in selected), {"de": 6, "fr": 6, "it": 6})
        self.assertEqual(Counter(row["stratum"] for row in selected), {"short": 6, "medium": 6, "long": 6})
        self.assertEqual({row["group_key"] for row in selected if row["stratum"] == "short"}, {"short-0", "short-1"})

    def test_non_dev_manifest_is_refused_before_private_io(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "development split"):
                _load_private_rows(Path(directory), {"split": "test"})


if __name__ == "__main__":
    unittest.main()
