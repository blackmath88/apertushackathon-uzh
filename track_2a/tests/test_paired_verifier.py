import json
import tempfile
import unittest
from pathlib import Path

from uzh_rsd.paired_verifier import _parse_keep, freeze


class PairedVerifierTests(unittest.TestCase):
    def test_keep_schema_is_strict(self):
        self.assertEqual(_parse_keep('{"keep":[2,0]}', 3)[0], [0, 2])
        for value in ('{"keep":[0,0]}', '{"keep":[3]}', '{"keep":[true]}', '{"keep":"0"}', 'bad'):
            self.assertIsNone(_parse_keep(value, 3)[0])

    def test_freeze_rejects_test_before_reading_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "development-only"):
                freeze(Path(tmp) / "missing", Path(tmp) / "out", base_commit="x", split="test")

    def test_freeze_uses_unexecuted_validation_pool(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); package = root / "package"; package.mkdir()
            rows = []
            for group in range(6):
                for language in ("de", "fr", "it"):
                    rows.append({"id": f"admin_{language}_{group}", "language": language,
                                 "group_key": str(group), "stratum": ("short", "medium", "long")[group // 2]})
            (package / "subset-manifest.json").write_text(json.dumps({"validation_pool": rows, "validation_execution": []}))
            result = freeze(package, root / "out", base_commit="abc")
            self.assertEqual(result["sample_count"], 18)
            self.assertEqual(result["budget"]["call_ceiling"], 36)
            self.assertEqual(result["generator"]["attempts"], 1)


if __name__ == "__main__":
    unittest.main()
