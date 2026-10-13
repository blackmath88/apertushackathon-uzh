import json
import shutil
import tempfile
import unittest
from pathlib import Path

from uzh_rsd.audit import _b2_items, tree_hashes, write_audit
from uzh_rsd.data_adapter import LANGUAGES, InferenceInput, local_path
from uzh_rsd.evaluation import DEFAULT_OFFICIAL_DIR, OFFICIAL_FILES
from uzh_rsd.methods import B2_MAX_EXCERPT_TOKENS, parse_b2
from uzh_rsd.runner import load_manifest
from uzh_rsd.tokens import tokenize

TRACK = Path(__file__).resolve().parents[1]
MANIFEST = TRACK / "manifests" / "s1-dev.json"
PILOT = TRACK / "results" / "20261012T062327Z-ff965461"
FETCHED = all(local_path("dev", language).exists() for language in LANGUAGES) and all(
    (DEFAULT_OFFICIAL_DIR / relative).exists() for relative in OFFICIAL_FILES)


def item(text_a="The fee is 30 francs .", text_b="Die Gebühr beträgt 60 Franken ."):
    return InferenceInput(id="admin_de_1", language="de", text_a=tokenize(text_a), text_b=tokenize(text_b), page_en="en", page_other="o")


class ItemAccountingTests(unittest.TestCase):
    def test_statuses_follow_parse_b2_rules(self):
        long = " ".join(["word"] * (B2_MAX_EXCERPT_TOKENS + 1))
        response = json.dumps({"differences": [
            {"a": "30 francs", "b": "60 Franken", "kind": "CHANGE", "severity": 4},  # complete
            {"a": "", "b": "Gebühr", "kind": "ADDITION", "severity": 2},              # complete, one-sided by design
            {"a": "30 francs", "b": "nicht da", "kind": "CHANGE", "severity": 3},     # partial: b not found
            {"a": long, "b": long, "kind": "CHANGE", "severity": 3},                  # unprojected: both over cap
            {"a": "x", "b": "y", "kind": "CHANGE", "severity": 9},                    # invalid severity
        ]})
        items = _b2_items(item(), response)
        self.assertEqual([i["status"] for i in items],
                         ["projected_complete", "projected_complete", "projected_partial", "unprojected", "invalid_severity"])
        self.assertEqual([s["match"] for s in items[3]["sides"]], ["too_long", "too_long"])
        projected = sum(i["status"].startswith("projected") for i in items)
        self.assertEqual(projected, parse_b2(item(), response).diagnostics["projected"])

    def test_excerpt_text_is_referenced_by_hash_not_copied(self):
        items = _b2_items(item(), json.dumps({"differences": [{"a": "30 francs", "b": "", "kind": "OMISSION", "severity": 3}]}))
        self.assertNotIn("francs", json.dumps(items))
        self.assertEqual(items[0]["sides"][0]["excerpt_tokens"], 2)


@unittest.skipUnless(FETCHED, "run `make s1-fetch` first (dev data and evaluator)")
class PilotAuditTests(unittest.TestCase):
    def test_pilot_audit_matches_committed_coverage_and_leaves_run_unchanged(self):
        before = tree_hashes(PILOT)
        with tempfile.TemporaryDirectory() as tmp:
            audit = write_audit(PILOT, Path(tmp) / "diag", load_manifest(MANIFEST), "test")
            self.assertTrue((Path(tmp) / "diag" / "audit_supplement.md").exists())
        self.assertEqual(before, tree_hashes(PILOT))
        spans = json.loads((PILOT / "results.json").read_text())["coverage"]["b2"]["spans"]
        b2 = audit["summary"]["b2"]
        self.assertEqual(b2["items_total"], spans["items"])
        self.assertEqual(b2["excerpts"]["too_long"], spans["spans_too_long"])
        self.assertEqual(b2["excerpts"]["not_found"], spans["spans_not_found"])
        self.assertEqual(b2["items"]["projected_complete"] + b2["items"]["projected_partial"], spans["projected"])
        self.assertEqual(b2["excerpts_total"], 2 * b2["items_total"])
        b0 = audit["summary"]["b0"]
        self.assertEqual((b0["parseable"], b0["strictly_valid"], b0["fallback_tokens"], b0["tokens_in_parseable_documents"]), (3, 0, 46, 541))

    def test_output_inside_run_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            shutil.copytree(PILOT, run)
            with self.assertRaises(ValueError):
                write_audit(run, run / "diag", load_manifest(MANIFEST), "test")


if __name__ == "__main__":
    unittest.main()
