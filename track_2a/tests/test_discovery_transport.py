"""Offline #34 tests: guarded transport, ledger/budgets, URL identity, per-host robots, durable frontier."""
import gzip
import os
import sqlite3
import sys
import tempfile
import urllib.request
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uzh_rsd import government_scout as gs
from uzh_rsd.discovery_transport import (
    Budgets, BudgetExceeded, DiscoveryStore, GuardedTransport, PinnedHTTPSConnection, Purpose, RedirectLoop,
    RequestLedger, bounded_body, build_guarded_opener, validate_public_host,
)
from uzh_rsd.government_scout import FetchResponse, SourceProfile, fetch_url, scout

BFE = "https://www.bfe.admin.ch"
OK_ROBOTS = b"User-agent: *\nDisallow:\n"


class Resp:
    def __init__(self, status, body=b"", headers=None):
        self.status, self._body, self.headers, self.closed = status, body, headers or {}, False

    def read(self, n):
        body, self._body = self._body[:n], self._body[n:]
        return body

    def close(self):
        self.closed = True


class Opener:
    def __init__(self, *responses):
        self.responses, self.urls = list(responses), []

    def open(self, request, timeout):
        self.urls.append(request.full_url)
        return self.responses.pop(0)


def public(*_a, **_k):
    return [(None, None, None, None, ("8.8.8.8", 443))]


def make(budgets=None, delay=2.0, opener=None):
    store = DiscoveryStore()
    ledger = RequestLedger(store, "r", budgets or Budgets(), delay_seconds=delay)
    scope = gs._scope_check(gs.PROFILES[0])
    return store, ledger, GuardedTransport(ledger, scope, resolver=public, opener_factory=lambda: opener)


class TransportTest(unittest.TestCase):
    def make(self, *args, **kwargs):
        store, ledger, transport = make(*args, **kwargs)
        self.addCleanup(store.close)
        return store, ledger, transport

    def test_hostile_proxy_environment_is_ignored(self):
        env = {"HTTPS_PROXY": "http://evil:8080", "ALL_PROXY": "http://evil:8080", "https_proxy": "http://evil:8080"}
        with patch.dict(os.environ, env):
            opener = build_guarded_opener(public)
            default = urllib.request.build_opener()
        is_proxy = lambda o: [h for h in o.handlers if h.__class__.__name__ == "ProxyHandler"]  # noqa: E731
        self.assertTrue(is_proxy(default))  # the stdlib default would have honoured the environment
        self.assertEqual(is_proxy(opener), [])

    def test_connection_time_pinning_rejects_rebinding_and_connects_to_validated_ip(self):
        answers = iter([public(), [(None, None, None, None, ("10.0.0.5", 443))]])
        resolver = lambda *a, **k: next(answers)  # noqa: E731
        validate_public_host(BFE, resolver)  # preflight passes with the public answer...
        conn = PinnedHTTPSConnection("www.bfe.admin.ch", resolver=resolver)
        with patch("uzh_rsd.discovery_transport.socket.create_connection") as connect:
            with self.assertRaises(ValueError):  # ...but the connection-time answer is private
                conn.connect()
            connect.assert_not_called()
        conn = PinnedHTTPSConnection("www.bfe.admin.ch", resolver=public)
        conn._context = type("C", (), {"wrap_socket": lambda self, sock, server_hostname: (sock, server_hostname)})()
        with patch("uzh_rsd.discovery_transport.socket.create_connection", return_value="sock") as connect:
            conn.connect()
        self.assertEqual(connect.call_args[0][0], ("8.8.8.8", 443))
        self.assertEqual(conn.sock, ("sock", "www.bfe.admin.ch"))

    def test_private_dns_refused_but_attempt_still_counted(self):
        store = DiscoveryStore()
        self.addCleanup(store.close)
        ledger = RequestLedger(store, "r", Budgets(), delay_seconds=0)
        private = lambda *a, **k: [(None, None, None, None, ("127.0.0.1", 443))]  # noqa: E731
        transport = GuardedTransport(ledger, gs._scope_check(gs.PROFILES[0]), resolver=private, opener_factory=lambda: Opener())
        with self.assertRaises(ValueError):
            transport.fetch(BFE + "/de/a")
        self.assertEqual((ledger.total, ledger.page), (1, 1))
        self.assertEqual(store.attempts("r")[0]["state"], "failed")

    def test_every_redirect_hop_consumes_budget_and_is_paced(self):
        opener = Opener(Resp(302, headers={"Location": "/de/b"}), Resp(302, headers={"Location": "/de/c"}),
                        Resp(200, b"<html></html>", {"Content-Type": "text/html"}))
        store, ledger, transport = self.make(opener=opener)
        with patch("uzh_rsd.discovery_transport.time.sleep") as sleep:
            response = transport.fetch(BFE + "/de/a")
        self.assertEqual((ledger.total, ledger.page), (3, 3))
        self.assertEqual(sleep.call_count, 2)  # hops 2 and 3 wait on the same host gate
        self.assertEqual([a["state"] for a in store.attempts("r")], ["completed"] * 3)
        self.assertEqual(len(response.redirects), 2)

    def test_redirect_loop_and_off_host_target_fail_after_counting(self):
        store, ledger, transport = self.make(opener=Opener(Resp(302, headers={"Location": "/de/a"})))
        with self.assertRaises(RedirectLoop), patch("uzh_rsd.discovery_transport.time.sleep"):
            transport.fetch(BFE + "/de/a")
        self.assertEqual(ledger.total, 1)
        store, ledger, transport = self.make(opener=Opener(Resp(302, headers={"Location": "https://evil.test/x"})))
        with self.assertRaises(ValueError):
            transport.fetch(BFE + "/de/a")
        self.assertEqual(ledger.total, 1)

    def test_failed_request_is_accounted_and_response_closed(self):
        resp = Resp(200, b"x" * 50)
        store, ledger, transport = self.make(opener=Opener(resp))
        transport.ledger.budgets  # noqa: B018
        with patch("uzh_rsd.discovery_transport.RESPONSE_CEILING", {p: 10 for p in Purpose}):
            with self.assertRaises(ValueError):
                transport.fetch(BFE + "/de/a")
        self.assertTrue(resp.closed)
        self.assertEqual(ledger.bytes, 11)  # overflow sentinel also counts
        self.assertEqual(store.attempts("r")[0]["error"], "ValueError")

    def test_typed_purposes_count_against_total_not_page_budget(self):
        opener = Opener(Resp(200, b"<urlset/>"), Resp(200, b"<rss/>"), Resp(200, b"x"))
        store, ledger, transport = self.make(Budgets(max_total_attempts=3, max_page_attempts=1), opener=opener)
        with patch("uzh_rsd.discovery_transport.time.sleep"):
            transport.fetch(BFE + "/sitemap.xml", Purpose.SITEMAP)  # .xml allowed only for sitemap/feed
            transport.fetch(BFE + "/feed.xml", Purpose.FEED)
            transport.fetch(BFE + "/de/a", Purpose.HTML)
            with self.assertRaises(BudgetExceeded) as cm:
                transport.fetch(BFE + "/de/b", Purpose.ROBOTS)
        self.assertEqual(cm.exception.reason, "total_attempt_budget")
        self.assertEqual((ledger.total, ledger.page), (3, 1))
        self.assertEqual([a["purpose"] for a in store.attempts("r")], ["sitemap", "feed", "html"])
        with self.assertRaises(ValueError):
            gs.fetch_url(BFE + "/x.xml", "bfe")

    def test_byte_and_decompression_ceilings(self):
        self.assertEqual(bounded_body(gzip.compress(b"a" * 10), "gzip", 10), b"a" * 10)
        with self.assertRaises(ValueError):
            bounded_body(gzip.compress(b"a" * 10_000), "gzip", 100)  # decompression bomb
        with self.assertRaises(ValueError):
            bounded_body(b"x", "br", 100)

    def test_byte_budget_stops_before_next_dispatch(self):
        store, ledger, transport = self.make(Budgets(max_body_bytes=5), opener=Opener(Resp(200, b"123456789")))
        with self.assertRaises(BudgetExceeded):
            transport.fetch(BFE + "/de/a")
        self.assertEqual(ledger.bytes, 5)
        self.assertEqual(store.attempts("r")[0]["bytes"], 5)
        with self.assertRaises(BudgetExceeded) as cm:
            transport.fetch(BFE + "/de/b")
        self.assertEqual(cm.exception.reason, "byte_budget")


    def test_partial_failed_read_keeps_byte_accounting(self):
        response = Mock(status=200, headers={})
        response.read.side_effect = [b"abc", TimeoutError("interrupted body")]
        store, ledger, transport = self.make(opener=Opener(response))
        with self.assertRaises(TimeoutError):
            transport.fetch(BFE + "/de/a")
        self.assertEqual(ledger.bytes, 3)
        self.assertEqual(store.attempts("r")[0]["bytes"], 3)
        response.close.assert_called_once()

    def test_truncated_and_concatenated_compression_are_not_valid_captures(self):
        raw = gzip.compress(b"evidence")
        for invalid in (raw[:-3], raw + raw):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                bounded_body(invalid, "gzip", 100)
        store, ledger, transport = self.make(opener=Opener(Resp(200, raw[:-3], {"content-encoding": "gzip"})))
        with self.assertRaises(ValueError):
            transport.fetch(BFE + "/de/a")
        self.assertEqual(ledger.bytes, len(raw) - 3)

    def test_lowercase_headers_work_for_redirect_and_encoding(self):
        raw = gzip.compress(b"evidence")
        opener = Opener(Resp(302, headers={"location": "/de/b"}), Resp(200, raw, {"content-encoding": "gzip", "content-type": "text/html"}))
        _, _, transport = self.make(delay=0, opener=opener)
        response = transport.fetch(BFE + "/de/a")
        self.assertEqual(response.body, b"evidence")
        self.assertEqual(response.headers["Content-Type"], "text/html")

    def test_pacing_cannot_dispatch_after_deadline(self):
        opener = Opener(Resp(200, b"ok"))
        store, ledger, transport = self.make(opener=opener)
        with patch.object(ledger, "pace", side_effect=lambda _: setattr(ledger, "started", ledger.clock() - 601)):
            with self.assertRaises(BudgetExceeded):
                transport.fetch(BFE + "/de/a")
        self.assertEqual(opener.urls, [])
        self.assertEqual(store.attempts("r")[0]["state"], "failed")

    def test_failed_tls_handshake_closes_socket(self):
        conn = PinnedHTTPSConnection("www.bfe.admin.ch", resolver=public)
        conn._context = Mock()
        conn._context.wrap_socket.side_effect = OSError("handshake failed")
        sock = Mock()
        with patch("uzh_rsd.discovery_transport.socket.create_connection", return_value=sock), self.assertRaises(OSError):
            conn.connect()
        sock.close.assert_called_once()

    def test_store_context_closes_on_interruption(self):
        store = DiscoveryStore()
        self.addCleanup(store.close)
        with self.assertRaises(KeyboardInterrupt):
            with store:
                raise KeyboardInterrupt
        with self.assertRaises(sqlite3.ProgrammingError):
            store.db.execute("SELECT 1")


class IdentityTest(unittest.TestCase):
    def test_fetch_url_keeps_meaningful_distinctions(self):
        self.assertEqual(fetch_url(BFE + "/de/a/?b=2&a=1#frag", "bfe"), BFE + "/de/a/?b=2&a=1")
        self.assertNotEqual(fetch_url(BFE + "/de/a/", "bfe"), fetch_url(BFE + "/de/a", "bfe"))
        self.assertNotEqual(fetch_url(BFE + "/de/a?a=1&b=2", "bfe"), fetch_url(BFE + "/de/a?b=2&a=1", "bfe"))
        self.assertIn("utm_source", fetch_url(BFE + "/de/a?utm_source=x", "bfe"))
        # legacy capture identity is unchanged
        self.assertEqual(gs.normalize_url(BFE + "/de/a/?b=2&a=1", "bfe"), BFE + "/de/a?a=1&b=2")


def page(links=""):
    return FetchResponse(200, "", {"Content-Type": "text/html"}, f"<html><body>{links}</body></html>".encode())


class ScoutTest(unittest.TestCase):
    def run_scout(self, handler, **kw):
        calls = []

        def fetcher(url, profile, **_k):
            calls.append(url)
            return handler(url)
        with patch("uzh_rsd.discovery_transport.time.sleep"):
            return scout("bfe", fetcher=fetcher, seeds=[BFE + "/de/a"], **kw), calls

    def test_trailing_slash_and_query_order_are_distinct_frontier_entries(self):
        links = '<a href="/de/b">1</a><a href="/de/b/">2</a><a href="/de/c?x=1&y=2">3</a><a href="/de/c?y=2&x=1">4</a>'
        def handler(url):
            return FetchResponse(200, url, {"Content-Type": "text/plain"}, OK_ROBOTS) if url.endswith("robots.txt") \
                else FetchResponse(200, url, {"Content-Type": "text/html"}, page(links if url.endswith("/a") else "").body)
        result, calls = self.run_scout(handler)
        self.assertEqual(len(result["frontier"]["entries"]), 5)
        self.assertEqual(result["stop_reason"], "frontier_exhausted")

    def test_page_budget_leaves_unvisited_visible_with_reason(self):
        links = "".join(f'<a href="/de/p{i}">x</a>' for i in range(5))
        def handler(url):
            if url.endswith("robots.txt"):
                return FetchResponse(200, url, {}, OK_ROBOTS)
            return FetchResponse(200, url, {"Content-Type": "text/html"}, page(links).body)
        result, calls = self.run_scout(handler, max_pages=2)
        self.assertEqual(result["page_request_count"], 2)
        self.assertEqual(result["stop_reason"], "page_attempt_budget")
        self.assertEqual(result["frontier"]["counts"]["unvisited_at_budget"], 4)
        self.assertEqual(result["frontier"]["counts"]["queued"], 0)

    def test_redirect_hops_reported_by_injected_fetcher_are_charged(self):
        def handler(url):
            if url.endswith("robots.txt"):
                return FetchResponse(200, url, {}, OK_ROBOTS)
            return FetchResponse(200, url, {"Content-Type": "text/html"}, page().body,
                                 ({"from": url, "to": url, "status": 302},))
        result, _ = self.run_scout(handler)
        self.assertEqual(result["page_request_count"], 2)

    def test_failed_requests_consume_budget(self):
        def handler(url):
            if url.endswith("robots.txt"):
                return FetchResponse(200, url, {}, OK_ROBOTS)
            raise TimeoutError
        result, _ = self.run_scout(handler)
        self.assertEqual(result["page_request_count"], 1)
        self.assertEqual(result["frontier"]["counts"]["failed"], 1)

    def test_robots_failure_blocks_content_and_hosts_do_not_bleed(self):
        profile = SourceProfile("two", ("a.admin.ch", "b.admin.ch"), ("https://a.admin.ch/x", "https://b.admin.ch/y"), ("de", "fr"))
        calls = []

        def fetcher(url, _p, **_k):
            calls.append(url)
            if url == "https://a.admin.ch/robots.txt":
                raise TimeoutError
            if url.endswith("robots.txt"):
                return FetchResponse(200, url, {}, b"User-agent: *\nDisallow: /y\n")
            raise AssertionError("content must not be requested")
        with patch("uzh_rsd.discovery_transport.time.sleep"):
            result = scout(profile, fetcher=fetcher)
        self.assertEqual(sorted(calls), ["https://a.admin.ch/robots.txt", "https://b.admin.ch/robots.txt"])
        states = {e["fetch_url"]: e["reason"] for e in result["frontier"]["entries"]}
        self.assertEqual(states, {"https://a.admin.ch/x": "robots_unavailable", "https://b.admin.ch/y": "robots_disallow"})
        self.assertEqual(result["page_request_count"], 0)

    def test_hostile_environment_never_reaches_scout_default_transport(self):
        with patch.dict(os.environ, {"HTTPS_PROXY": "http://evil:1"}), patch("uzh_rsd.government_scout.build_opener") as b:
            b.return_value = Opener(Resp(404, headers={}))
            scout("bfe", resolver=public)
        self.assertEqual(b.call_args[0][0].proxies, {})


class RestartTest(unittest.TestCase):
    def test_interrupted_work_is_recorded_not_replayed(self):
        class Crash(BaseException):
            pass
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "frontier.sqlite"
            calls = []

            def fetcher(url, _p, **_k):
                calls.append(url)
                if url.endswith("robots.txt"):
                    return FetchResponse(200, url, {}, OK_ROBOTS)
                raise Crash
            with patch("uzh_rsd.discovery_transport.time.sleep"), self.assertRaises(Crash):
                scout("bfe", fetcher=fetcher, frontier_path=path)
            first = len(calls)
            store = DiscoveryStore(str(path))
            self.assertEqual(store.recovered_interrupted, 1)
            self.assertEqual(store.recovered_attempts, 0)  # fetcher settled the attempt via BaseException path
            run = store.db.execute("SELECT run_id FROM runs").fetchone()[0]
            counts = store.counts(run)
            self.assertEqual((counts["interrupted"], counts["queued"]), (1, 1))  # nothing silently dropped
            store.close()
            # A fresh scout on the same store lists the interrupted entry and does not retry it by itself.
            with patch("uzh_rsd.discovery_transport.time.sleep"):
                result = scout("bfe", fetcher=lambda u, _p, **_k: FetchResponse(404, u, {}, OK_ROBOTS), frontier_path=path)
            self.assertEqual(len(result["interrupted_from_earlier_runs"]), 1)
            self.assertEqual(first, 2)

    def test_state_round_trip(self):
        store = DiscoveryStore()
        self.addCleanup(store.close)
        store.begin_run("r", "p", {})
        store.enqueue("r", "k", "https://x/", 0, None)
        self.assertFalse(store.enqueue("r", "k", "https://x/", 0, None))
        store.set_state("r", "k", "blocked", "robots_disallow")
        self.assertEqual(store.counts("r")["blocked"], 1)


if __name__ == "__main__":
    unittest.main()
