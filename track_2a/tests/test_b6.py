import json
import tempfile
import unittest
from pathlib import Path

from uzh_rsd.b6 import freeze, sanitize_identities, score


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "experiments" / "b6-semantic-risk-atlas"


class B6ContractTests(unittest.TestCase):
    def assert_no_forbidden_keys(self, value):
        if isinstance(value, dict):
            self.assertTrue({"gold", "labels_a", "labels_b", "gold_sha256", "stratum"}.isdisjoint(value))
            for child in value.values():
                self.assert_no_forbidden_keys(child)
        elif isinstance(value, list):
            for child in value:
                self.assert_no_forbidden_keys(child)

    def test_identity_sanitizer_excludes_gold_and_strata(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "identity.json"
            result = sanitize_identities(
                ROOT / "experiments/b2-projection-evidence/manifest.json", target
            )
            self.assertEqual(len(result["entries"]), 30)
            self.assert_no_forbidden_keys(result)

    def test_freeze_api_has_no_gold_argument_and_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            identity = tmp / "identity.json"
            sanitize_identities(ROOT / "experiments/b2-projection-evidence/manifest.json", identity)
            outputs = []
            for name in ("one.json", "two.json"):
                out = tmp / name
                outputs.append(freeze(
                    ROOT / "experiments/b4-alignment-first-sdm/alignment-20261013/evidence.jsonl",
                    identity,
                    PACKAGE / "atlas-v1.json",
                    ROOT / "experiments/b5-competitive-semantic-alignment/selector-manifest.json",
                    out,
                ))
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0]["strategies"], ["A0_b5", "A1_risk", "A2_family", "uniform_random", "cue_first"])
            self.assert_no_forbidden_keys(outputs[0])

    def test_test_split_refused_before_input_io(self):
        missing = Path("/definitely/missing")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "not available in development"):
                freeze(missing, missing, missing, missing, Path(tmp) / "x", split="test")
            with self.assertRaisesRegex(ValueError, "not available in development"):
                score(missing, "0" * 64, missing, missing, Path(tmp) / "y", split="test")


if __name__ == "__main__":
    unittest.main()
