"""Capture, fixture replay, method and viewer tests. No network or benchmark data."""
import json
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uzh_rsd.live_government_pilot import (
    PAIR_STATES, analyze_pair, build_demo, capture_html, extract_content, main, render_viewer,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "live_government_pilot"
POLICY = ROOT / "live_government_pilot" / "v1" / "policy" / "bfe-policy-review-20261013.json"


class LiveGovernmentPilotTest(unittest.TestCase):
    def test_offsets_hashes_order_and_noise_exclusion(self):
        html = '<html><body><nav>noise</nav><main><h1>A &amp; B</h1><p>Text here.</p><ul><li>One</li></ul><table><tr><td>Cell</td></tr></table><form><p>secret</p></form></main></body></html>'
        result = extract_content(html)
        self.assertEqual([b["kind"] for b in result["blocks"]], ["heading", "paragraph", "list_item", "table_cell"])
        self.assertNotIn("noise", result["extracted_text"])
        self.assertNotIn("secret", result["extracted_text"])
        for block in result["blocks"]:
            self.assertEqual(result["extracted_text"][block["start"]:block["end"]], block["text"])
        self.assertEqual(result["sha256_extract"], sha256(result["extracted_text"].encode()).hexdigest())

    def test_content_address_is_immutable_and_pair_states_validate(self):
        body = (FIXTURES / "bfe-de.html").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            kwargs = dict(html_bytes=body, source_url="https://www.bfe.admin.ch/de/fixture-a",
                          canonical_url="https://www.bfe.admin.ch/de/fixture-a", locale="de-CH",
                          profile="bfe", retrieved_at_utc="2026-10-13T00:00:00Z", rights_note="synthetic",
                          raw_dir=tmp, fixture=True)
            first = capture_html(**kwargs)
            second = capture_html(**kwargs)
            self.assertEqual(first["content_address"], second["content_address"])
            self.assertEqual(len(list(Path(tmp).rglob("*.html"))), 1)
        self.assertEqual(PAIR_STATES, {"CANDIDATE", "UNKNOWN", "UNRESOLVED", "HUMAN_VERIFIED", "REJECTED"})
        with self.assertRaises(ValueError):
            analyze_pair(first, first, pair_status="VERIFIED_BY_MODEL", pairing_evidence=[], reviewer=None)

    def test_fixture_replay_and_non_apertus_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = build_demo(tmp, FIXTURES, POLICY)
            written = json.loads((Path(tmp) / "demonstration-manifest.json").read_text())
            self.assertTrue(manifest["fixture"])
            self.assertEqual(written["analysis"]["apertus_calls"], 0)
            self.assertFalse(written["analysis"]["gold_labels"])
            self.assertFalse(written["analysis"]["spearman_claim"])
            self.assertEqual(written["analysis"]["candidates"][0]["status"], "UNRESOLVED")
            self.assertEqual(written["analysis"]["pair_status"], "HUMAN_VERIFIED")

    def test_policy_blocked_direct_entrypoint_returns_three_without_scout(self):
        with tempfile.TemporaryDirectory() as tmp, patch(
            "uzh_rsd.live_government_pilot.scout"
        ) as live_scout:
            output = Path(tmp) / "blocked.json"
            code = main([
                "live", "--confirm-live", "--policy", str(POLICY), "--out", str(output),
            ])
            self.assertEqual(code, 3)
            self.assertEqual(json.loads(output.read_text())["status"], "POLICY_BLOCKED")
            live_scout.assert_not_called()

    def test_viewer_escapes_content_and_has_safe_source_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = build_demo(tmp, FIXTURES, POLICY)
            manifest["pair"]["left"]["blocks"][0]["minimal_excerpt"] = '<script>alert("x")</script>'
            html = render_viewer(manifest)
            self.assertNotIn('<script>alert("x")</script>', html)
            self.assertIn('&lt;script&gt;', html)
            self.assertIn('rel="noopener noreferrer"', html)
            self.assertIn("Open source URL", html)
            self.assertIn("non-Apertus", html)
            self.assertNotIn("Apertus-powered", html)
            manifest["pair"]["left"]["source_url"] = "javascript:alert(1)"
            with self.assertRaises(ValueError):
                render_viewer(manifest)


if __name__ == "__main__":
    unittest.main()
