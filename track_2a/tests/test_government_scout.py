"""Offline safety and compatibility tests for the profile-based Scout."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uzh_rsd.government_scout import (
    Captured, FetchResponse, PROFILES, _network_fetch, decode_html, get_profile,
    normalize_url, parse_page, potential_pairs, scout,
)


class FakeResponse:
    def __init__(self, status, url, body=b"", headers=None):
        self.status = status
        self.url = url
        self._body = body
        self.headers = headers or {}

    def read(self, limit):
        body, self._body = self._body[:limit], self._body[limit:]
        return body


class FakeOpener:
    def __init__(self, responses):
        self.responses = iter(responses)

    def open(self, _request, timeout):
        self.timeout = timeout
        return next(self.responses)


def public_resolver(*_args, **_kwargs):
    return [(None, None, None, None, ("8.8.8.8", 443))]


class GovernmentScoutTest(unittest.TestCase):
    def test_profiles_and_aliases_have_required_order(self):
        self.assertEqual([p.id for p in PROFILES], ["bfe-federal", "ch-citizen", "zurich-city"])
        self.assertEqual(get_profile("bfe"), PROFILES[0])
        self.assertEqual(get_profile("stadt-zuerich"), PROFILES[2])

    def test_exact_host_https_and_non_asset_scope(self):
        good = "https://www.bfe.admin.ch/de/page?utm_source=x&a=2"
        self.assertEqual(normalize_url(good, "bfe"), "https://www.bfe.admin.ch/de/page?a=2")
        unsafe = [
            "http://www.bfe.admin.ch/de/page", "https://bfe.admin.ch/de/page",
            "https://www.bfe.admin.ch.evil.test/de/page", "https://evil.test/?next=www.bfe.admin.ch",
            "https://user:pass@www.bfe.admin.ch/de/page", "https://www.bfe.admin.ch:443/de/page",
            "https://www.bfe.admin.ch/de/file.pdf", "https://www.bfe.admin.ch/de/file.xml",
        ]
        for value in unsafe:
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_url(value, "bfe-federal")

    def test_redirect_target_is_revalidated_before_follow(self):
        opener = FakeOpener([FakeResponse(302, "https://www.bfe.admin.ch/de/a", headers={"Location": "https://evil.test/x"})])
        with patch("uzh_rsd.government_scout.build_opener", return_value=opener):
            with self.assertRaises(ValueError):
                _network_fetch("https://www.bfe.admin.ch/de/a", PROFILES[0], timeout=1, max_bytes=100,
                               resolver=public_resolver)

    def test_same_host_redirect_records_validated_hop(self):
        opener = FakeOpener([
            FakeResponse(302, "https://www.bfe.admin.ch/de/a", headers={"Location": "/de/b"}),
            FakeResponse(200, "https://www.bfe.admin.ch/de/b", b"<html></html>", {"Content-Type": "text/html"}),
        ])
        with patch("uzh_rsd.government_scout.build_opener", return_value=opener):
            response = _network_fetch("https://www.bfe.admin.ch/de/a", PROFILES[0], timeout=1, max_bytes=100,
                                      resolver=public_resolver)
        self.assertEqual(response.url, "https://www.bfe.admin.ch/de/b")
        self.assertTrue(response.redirects[0]["validated"])

    def test_robots_unavailable_fails_closed_before_pages(self):
        calls = []
        def unavailable(url, *_args, **_kwargs):
            calls.append(url)
            raise TimeoutError
        result = scout("bfe", fetcher=unavailable)
        self.assertEqual(calls, ["https://www.bfe.admin.ch/robots.txt"])
        self.assertEqual(result["page_request_count"], 0)
        self.assertEqual(result["audit"][0]["state"], "ROBOTS_UNAVAILABLE")

    def test_robots_disallow_is_audited_without_page_request(self):
        calls = []
        def fake(url, *_args, **_kwargs):
            calls.append(url)
            return FetchResponse(200, url, {"Content-Type": "text/plain"}, b"User-agent: *\nDisallow: /de\nDisallow: /fr\n")
        result = scout("bfe", fetcher=fake)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["page_request_count"], 0)
        self.assertEqual([item["state"] for item in result["audit"]].count("ROBOTS_DISALLOW"), 2)

    def test_encoding_and_duplicate_page_discovery(self):
        de = "https://www.bfe.admin.ch/de/dunstabzugshauben"
        fr = "https://www.bfe.admin.ch/fr/hottes-domestiques"
        pages = {
            de: ("text/html; charset=iso-8859-1", f'<html lang="de"><head><title>Ger\xe4t</title><link rel="alternate" hreflang="fr" href="{fr}"></head><body><a href="{fr}">fr</a><a href="{fr}">again</a></body></html>'.encode("latin-1")),
            fr: ("text/html", f'<html lang="fr"><head><title>Hotte</title><link rel="alternate" hreflang="de" href="{de}"></head><body></body></html>'.encode()),
        }
        def fake(url, *_args, **_kwargs):
            if url.endswith("robots.txt"):
                return FetchResponse(200, url, {"Content-Type": "text/plain"}, b"User-agent: *\nDisallow:\n")
            ctype, body = pages[url]
            return FetchResponse(200, url, {"Content-Type": ctype}, body)
        with patch("uzh_rsd.government_scout.time.sleep"):
            result = scout("bfe", fetcher=fake, delay_seconds=2)
        self.assertEqual(len(result["captured"]), 2)
        self.assertEqual(result["captured"][0]["title"], "Gerät")
        self.assertEqual(len(result["pairs"]), 1)
        self.assertEqual(result["pairs"][0]["status"], "CANDIDATE")

    def test_pair_states_require_reciprocal_evidence_and_languages(self):
        de = Captured("https://www.bfe.admin.ch/de/a", "t", "0" * 64, "", 0,
                      {"fr": ["https://www.bfe.admin.ch/fr/b"]}, None, "de")
        fr = Captured("https://www.bfe.admin.ch/fr/b", "t", "1" * 64, "", 0,
                      {}, None, "fr")
        self.assertEqual(potential_pairs([de, fr], "de", "fr"), [])
        fr = Captured(fr.url, "t", "1" * 64, "", 0, {"de": [de.url]}, None, "fr")
        self.assertEqual(potential_pairs([de, fr], "de", "fr")[0]["pairing_evidence"], ["reciprocal_hreflang"])


if __name__ == "__main__":
    unittest.main()
