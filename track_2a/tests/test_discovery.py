"""Offline #35 tests with authored fixtures only; all requests go through the guarded ledger."""
import gzip
import json
import tempfile
import threading
import unittest
from unittest.mock import patch

from uzh_rsd import discovery
from uzh_rsd.campaign_center import Store
from uzh_rsd.discovery_transport import Budgets
from uzh_rsd.government_scout import FetchResponse

H = "https://www.bfe.admin.ch"
NS = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml"'


def urlset(*entries):
    body = "".join(f"<url><loc>{loc}</loc>" + "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{h}"/>' for l, h in alts) + "</url>"
                   for loc, alts in entries)
    return f"<urlset {NS}>{body}</urlset>".encode()


def index(*locs):
    return f"<sitemapindex {NS}>" + "".join(f"<sitemap><loc>{l}</loc></sitemap>" for l in locs) + "</sitemapindex>"


SEED_DE = H + "/de/dunstabzugshauben"
SEED_FR = H + "/fr/hottes-domestiques"
HTML = {
    SEED_DE: f'<html lang="de"><head><link rel="alternate" hreflang="fr" href="{SEED_FR}"><link rel="alternate" type="application/rss+xml" href="/feed.xml"></head>'
             f'<body><nav><a href="/it/cappe" hreflang="it">IT</a><a href="https://evil.test/x">x</a></nav></body></html>',
    SEED_FR: '<html lang="fr"><body></body></html>',
}


def site(extra=None, robots=None):
    files = {
        H + "/robots.txt": (b"User-agent: *\nDisallow:\nSitemap: " + (H + "/sitemap-index.xml\nSitemap: https://evil.test/s.xml\n").encode()
                            if robots is None else robots),
        H + "/sitemap-index.xml": index(H + "/sm-a.xml.gz", H + "/sitemap-index.xml", H + "/sm-b.xml").encode(),
        H + "/sm-a.xml.gz": gzip.compress(urlset((H + "/en/hoods", [("de", SEED_DE), ("en", H + "/en/hoods")]),
                                                  (H + "/fr/other", [("fr", H + "/fr/other-a"), ("fr", H + "/fr/other-b")]))),
        H + "/sm-b.xml": urlset((H + "/de/solo", [])),
        H + "/feed.xml": b'<rss><channel><item><link>' + (H + "/de/news").encode() + b'</link></item></channel></rss>',
    }
    files.update(extra or {})
    calls = []

    def fetcher(url, _profile, **_k):
        calls.append(url)
        if url in HTML:
            return FetchResponse(200, url, {"Content-Type": "text/html"}, HTML[url].encode())
        if url in files:
            body = files[url]
            return FetchResponse(200, url, {"Content-Type": "application/xml"}, body if isinstance(body, bytes) else body.encode())
        return FetchResponse(404, url, {}, b"")
    return fetcher, calls


def run(fetcher, **kw):
    with patch("uzh_rsd.discovery_transport.time.sleep"):
        return discovery.discover("bfe", fetcher=fetcher, delay_seconds=0, **kw)


class DiscoveryTest(unittest.TestCase):
    def test_candidate_ceiling_is_enforced_and_incomplete_inventory_is_explicit(self):
        fetch, calls = site()
        snap = run(fetch, budgets=Budgets(max_candidates=2))
        self.assertEqual(len(snap["candidates"]), 2)
        self.assertEqual(snap["stop_reason"], "candidate_budget")
        self.assertEqual(snap["unvisited_count"], 2)
        self.assertNotIn(SEED_DE, calls)

    def test_xml_declarations_are_rejected_beyond_prefix_and_in_utf16(self):
        doc = '<!DOCTYPE urlset [<!ENTITY x "expanded">]><urlset><url><loc>&x;</loc></url></urlset>'
        for body in ((" " * 5000 + doc).encode(), doc.encode("utf-16")):
            for parse in (discovery.parse_sitemap, discovery.parse_feed):
                with self.subTest(parse=parse.__name__), self.assertRaises(ValueError):
                    parse(body)
        with self.assertRaises(ValueError):
            discovery.parse_sitemap(b"<html/>")

    def test_relative_navigation_uses_final_response_url(self):
        base, _ = site(robots=b"User-agent: *\nDisallow:\n")
        def redirected(url, profile, **kwargs):
            if url == SEED_DE:
                return FetchResponse(200, H + "/de/section/page", {"Content-Type": "text/html"}, b'<nav><a href="child">Child</a></nav>')
            return base(url, profile, **kwargs)
        snap = run(redirected)
        urls = {c["url"] for c in snap["candidates"]}
        self.assertIn(H + "/de/section/child", urls)
        self.assertNotIn(H + "/de/child", urls)

    def test_sitemap_index_gzip_feed_navigation_cycle_and_offhost(self):
        fetcher, calls = site()
        snap = run(fetcher)
        sources = {(n["source"], n.get("url", ""), n["state"]) for n in snap["sources"]}
        self.assertIn(("sitemap", H + "/sm-a.xml.gz", "loaded"), sources)
        self.assertIn(("sitemap", H + "/sitemap-index.xml", "cycle_or_duplicate_skipped"), sources)
        self.assertTrue(any(n["state"] == "excluded" and "evil.test" in n["url"] for n in snap["sources"]))
        self.assertNotIn("https://evil.test/s.xml", calls)
        urls = {c["url"]: c for c in snap["candidates"]}
        self.assertIn(H + "/de/news", urls)                       # feed
        self.assertEqual(urls[H + "/de/news"]["state"], "observed_not_fetched")  # unvisited stays visible
        self.assertEqual(urls[SEED_DE]["state"], "fetched")
        self.assertTrue(any(c["state"] == "excluded" for c in snap["candidates"]))  # off-host nav link
        self.assertEqual(snap["model_calls"], 0)

    def test_four_languages_directional_and_contradictory_provenance(self):
        snap = run(site()[0])
        fams = {f["family_id"]: f for f in snap["families"]}
        main = next(f for f in fams.values() if SEED_DE in [m["url"] for l in f["languages"].values() for m in l])
        self.assertEqual(set(main["languages"]), {"de", "fr", "it", "en"})
        self.assertEqual(main["language_availability"]["it"], "observed")  # navigation hreflang
        self.assertEqual(main["status"], "one_directional")  # de page declares fr; fr does not declare back
        self.assertTrue(all(e["declared_by"] for e in main["edges"]))
        bad = next(f for f in fams.values() if H + "/fr/other-a" in [m["url"] for m in f["languages"]["fr"]])
        self.assertEqual(bad["status"], "contradictory")
        self.assertEqual(bad["contradictions"][0]["language"], "fr")
        solo = next(f for f in fams.values() if f["member_count"] == 1 and H + "/de/solo" in [m["url"] for m in f["languages"]["de"]])
        self.assertEqual(solo["language_availability"]["en"], "not_observed")

    def test_robots_failure_blocks_everything(self):
        calls = []

        def fetcher(url, _p, **_k):
            calls.append(url)
            raise TimeoutError
        snap = run(fetcher)
        self.assertEqual(calls, [H + "/robots.txt"])
        self.assertEqual(snap["stop_reason"], "robots_unavailable")
        self.assertEqual(snap["candidates"], [])

    def test_budget_exhaustion_is_visible_and_counts_everything(self):
        fetcher, calls = site()
        snap = run(fetcher, budgets=Budgets(max_page_attempts=1, max_total_attempts=4))
        self.assertEqual(snap["stop_reason"], "total_attempt_budget")
        self.assertEqual(snap["accounting"]["total_attempts"], 4)
        self.assertEqual(len(calls), 4)
        self.assertTrue(snap["unvisited_count"] > 0 or snap["candidates"])

    def test_decompression_bomb_and_dtd_are_refused_not_expanded(self):
        fetcher, _ = site({H + "/sm-a.xml.gz": gzip.compress(b"<urlset>" + b"a" * 20_000_000 + b"</urlset>"),
                           H + "/sm-b.xml": b'<!DOCTYPE x [<!ENTITY a "b">]><urlset/>'})
        snap = run(fetcher)
        states = {(n["url"], n["state"]) for n in snap["sources"] if n["source"] == "sitemap"}
        self.assertIn((H + "/sm-a.xml.gz", "failed"), states)
        self.assertIn((H + "/sm-b.xml", "failed"), states)

    def test_preview_has_no_network_and_unreviewed_sites_are_ineligible(self):
        self.assertTrue(discovery.preview("bfe")["eligible"])
        self.assertEqual(discovery.preview("bafu")["reason"], "no_reviewed_source_profile")


class CampaignFlowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)

    def store(self, fetcher=None):
        s = Store(self.tmp.name, discovery_fetcher=fetcher); s.discovery_delay = 0
        self.addCleanup(s.lease.close)
        return s

    def test_preview_explicit_start_progress_select_save_reload(self):
        s = self.store(site()[0])
        c = s.create("Energy", site_ids=["bfe", "bafu"])
        self.assertTrue(s.discovery_preview(c["id"], "bfe")["eligible"])
        with self.assertRaises(ValueError):
            s.discovery_start(c["id"], "bfe", None)  # preview alone never starts
        with patch("uzh_rsd.discovery_transport.time.sleep"):
            run = s.discovery_start(c["id"], "bfe", True)
            for t in s.threads: t.join(10)
        saved = s.read(c["id"])["discovery_runs"][0]
        self.assertEqual((run["state"], saved["state"]), ("running", "complete"))
        self.assertGreater(saved["progress"]["total_attempts"], 0)
        snap = s.snapshot(c["id"], saved["snapshot_id"])
        fam = snap["families"][0]["family_id"]
        s.page_scope(c["id"], [{"snapshot_id": snap["id"], "family_id": fam}])
        s.lease.close()
        s2 = Store(self.tmp.name); self.addCleanup(s2.lease.close)  # reload
        pf = s2.read(c["id"])["scope"]["page_families"]
        self.assertEqual((pf[0]["family_id"], pf[0]["snapshot_id"]), (fam, snap["id"]))
        self.assertIn("not_observed", pf[0]["language_availability"].values())
        with self.assertRaises(ValueError):
            s2.page_scope(c["id"], [{"snapshot_id": snap["id"], "family_id": "nope"}])
        s2.scope(c["id"], ["bfe"])  # re-saving site scope keeps page families
        self.assertEqual(len(s2.read(c["id"])["scope"]["page_families"]), 1)

    def test_without_authorised_transport_and_for_unreviewed_sites_start_is_blocked_honestly(self):
        s = self.store(None)
        c = s.create("x", site_ids=["bfe", "bafu"])
        self.assertEqual(s.discovery_start(c["id"], "bfe", True)["reason"], "live_discovery_not_authorised")
        self.assertEqual(s.discovery_start(c["id"], "bafu", True)["reason"], "no_reviewed_source_profile")
        with self.assertRaises(ValueError):
            s.discovery_start(c["id"], "bak", True)  # not in scope

    def test_interrupted_run_is_recorded_on_restart(self):
        s = self.store(None)
        c = s.create("x", site_ids=["bfe"])
        d = s.read(c["id"]); d["discovery_runs"] = [{"id": "r", "state": "running", "site_id": "bfe"}]; s.write(d)
        s.lease.close()
        s2 = Store(self.tmp.name); self.addCleanup(s2.lease.close)
        self.assertEqual(s2.read(c["id"])["discovery_runs"][0]["state"], "interrupted")


if __name__ == "__main__":
    unittest.main()
