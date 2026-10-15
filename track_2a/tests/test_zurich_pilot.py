"""Offline contract tests for city-site scouting. No external network, model or test split."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from uzh_rsd.zurich_pilot import Captured, normalize_url, parse_page, potential_pairs, scout


BASE = "https://www.stadt-zuerich.ch/de/lebenslagen/neu-in-zuerich"
EN = "https://www.stadt-zuerich.ch/en/visit/new"


def record(url, alternates):
    return Captured(url=url, title="", depth=0, retrieved_at_utc="2026-10-13T00:00:00Z",
                    sha256_html="0" * 64, canonical=None, alternates=alternates)


class ZurichPilotTest(unittest.TestCase):
    def test_normalizes_tracking_without_changing_semantic_query(self):
        self.assertEqual(normalize_url(BASE + "/?utm_source=foo&k=a&gclid=z"), BASE + "?k=a")

    def test_external_and_unsafe_inputs_refused(self):
        for url in ("http://www.stadt-zuerich.ch/de", "https://evil.ch/de",
                    "https://www.stadt-zuerich.ch.evil.ch/de", "file:///etc/passwd",
                    "https://www.stadt-zuerich.ch/de/file.pdf",
                    "https://user:pass@www.stadt-zuerich.ch/de"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                normalize_url(url)

    def test_extracts_explicit_alternates(self):
        data = f"""<html><head><title>New arrival</title>
        <link rel="alternate" hreflang="de-CH" href="{BASE}">
        <link rel="canonical" href="{EN}"></head>
        <body><a href="/de/service">service</a></body></html>""".encode()
        parsed, alt, canonical = parse_page(data, EN)
        self.assertEqual(parsed.title, "New arrival")
        self.assertEqual(alt["de-ch"], [BASE])
        self.assertEqual(canonical, EN)

    def test_recipient_requires_recipient_backlink(self):
        german = record(BASE, {"en": [EN]})
        english = record(EN, {})
        self.assertEqual(potential_pairs([german, english]), [])
        english = record(EN, {"de": [BASE]})
        self.assertEqual(potential_pairs([german, english]),
                         [{"de": BASE, "en": EN, "pairing": "reciprocal_hreflang", "review": "candidate"}])

    def test_no_implicit_pairing_by_slug(self):
        german = record(BASE, {})
        english = record(EN, {})
        self.assertEqual(potential_pairs([german, english]), [])

    def test_scouter_refuses_unsafe_budget_before_any_network(self):
        for kwargs in ({"max_pages": 21}, {"max_depth": 3}, {"delay_seconds": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                scout(BASE, **kwargs)


if __name__ == "__main__":
    unittest.main()
