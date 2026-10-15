"""Guarded discovery transport: request ledger, budgets, pacing and durable frontier.

Stdlib only. Every HTTP attempt (robots, sitemap, feed, HTML, each redirect hop,
failures included) is reserved in one ledger *before* dispatch, paced per host,
and its outcome is recorded separately. No model calls occur here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import http.client
import ipaddress
import json
import socket
import sqlite3
import ssl
import time
from typing import Callable, Mapping
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener
from urllib.error import HTTPError
import zlib

USER_AGENT = "LostInSwitzerlandResearch/1.0 (+https://github.com/blackmath88/apertushackathon-uzh; bounded audit)"
MAX_REDIRECTS = 3
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class Purpose(str, Enum):
    ROBOTS = "robots"
    SITEMAP = "sitemap"
    FEED = "feed"
    HTML = "html"


ACCEPT = {
    Purpose.ROBOTS: "text/plain",
    Purpose.SITEMAP: "application/xml, text/xml",
    Purpose.FEED: "application/atom+xml, application/rss+xml, application/xml",
    Purpose.HTML: "text/html",
}
# Per-purpose response ceilings (bytes), applied to wire bytes and after decompression.
RESPONSE_CEILING = {
    Purpose.ROBOTS: 128_000, Purpose.SITEMAP: 2_000_000, Purpose.FEED: 1_000_000, Purpose.HTML: 1_000_000,
}


@dataclass(frozen=True)
class FetchResponse:
    status: int
    url: str
    headers: Mapping[str, str]
    body: bytes
    redirects: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True)
class Budgets:
    """Explicit, separately counted ceilings. Values other than page attempts/depth/delay are
    PROPOSED defaults (research report), not measured optima."""
    max_page_attempts: int = 20          # HTML-purpose dispatches, redirect hops and failures included
    max_total_attempts: int = 40         # all purposes (robots, sitemap, feed, HTML), all hops
    max_body_bytes: int = 20 * 1024 * 1024
    max_candidates: int = 500            # parsed in-scope link candidates admitted to the frontier
    max_wall_seconds: float = 600.0


class BudgetExceeded(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class RedirectLoop(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DiscoveryStore:
    """SQLite frontier + attempt ledger. Opening a store never replays interrupted work."""

    STATES = ("queued", "leased", "fetched", "blocked", "failed", "excluded", "unvisited_at_budget", "interrupted")

    def __init__(self, path: str | None = None) -> None:
        self.db = sqlite3.connect(path or ":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY, profile TEXT, config TEXT, started_at TEXT, stop_reason TEXT);
            CREATE TABLE IF NOT EXISTS frontier(run_id TEXT, dedup_key TEXT, fetch_url TEXT, depth INTEGER, source_url TEXT,
                state TEXT, reason TEXT, status INTEGER, seq INTEGER, updated_at TEXT, PRIMARY KEY(run_id, dedup_key));
            CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, purpose TEXT, host TEXT,
                url TEXT, hop INTEGER, state TEXT, status INTEGER, error TEXT, bytes INTEGER, note TEXT,
                reserved_at TEXT, completed_at TEXT);
        """)
        # Crash recovery: record, never retry. Leased work and un-settled attempts become uncertain.
        cur = self.db.execute("UPDATE frontier SET state='interrupted', reason='interrupted_before_outcome', updated_at=? "
                              "WHERE state='leased'", (_now(),))
        self.recovered_interrupted = cur.rowcount
        cur = self.db.execute("UPDATE attempts SET state='uncertain', completed_at=? WHERE state='reserved'", (_now(),))
        self.recovered_attempts = cur.rowcount
        self.db.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def close(self) -> None:
        self.db.close()

    def begin_run(self, run_id: str, profile: str, config: dict[str, object]) -> None:
        self.db.execute("INSERT INTO runs VALUES(?,?,?,?,NULL)", (run_id, profile, json.dumps(config, sort_keys=True), _now()))
        self.db.commit()

    def end_run(self, run_id: str, stop_reason: str) -> None:
        self.db.execute("UPDATE runs SET stop_reason=? WHERE run_id=?", (stop_reason, run_id))
        self.db.commit()

    def enqueue(self, run_id: str, key: str, url: str, depth: int, source: str | None,
                state: str = "queued", reason: str | None = None) -> bool:
        seq = self.db.execute("SELECT COALESCE(MAX(seq),0)+1 FROM frontier WHERE run_id=?", (run_id,)).fetchone()[0]
        cur = self.db.execute("INSERT OR IGNORE INTO frontier VALUES(?,?,?,?,?,?,?,NULL,?,?)",
                              (run_id, key, url, depth, source, state, reason, seq, _now()))
        self.db.commit()
        return cur.rowcount == 1

    def queued(self, run_id: str) -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM frontier WHERE run_id=? AND state='queued' ORDER BY seq", (run_id,)).fetchall()

    def set_state(self, run_id: str, key: str, state: str, reason: str | None = None, status: int | None = None) -> None:
        self.db.execute("UPDATE frontier SET state=?, reason=?, status=?, updated_at=? WHERE run_id=? AND dedup_key=?",
                        (state, reason, status, _now(), run_id, key))
        self.db.commit()

    def mark_unvisited(self, run_id: str, reason: str) -> int:
        cur = self.db.execute("UPDATE frontier SET state='unvisited_at_budget', reason=?, updated_at=? "
                              "WHERE run_id=? AND state='queued'", (reason, _now(), run_id))
        self.db.commit()
        return cur.rowcount

    def entries(self, run_id: str) -> list[dict[str, object]]:
        rows = self.db.execute("SELECT dedup_key, fetch_url, depth, source_url, state, reason, status FROM frontier "
                               "WHERE run_id=? ORDER BY seq", (run_id,)).fetchall()
        return [dict(row) for row in rows]

    def counts(self, run_id: str) -> dict[str, int]:
        counts = {state: 0 for state in self.STATES}
        for row in self.db.execute("SELECT state, COUNT(*) n FROM frontier WHERE run_id=? GROUP BY state", (run_id,)):
            counts[row["state"]] = row["n"]
        return counts

    def attempts(self, run_id: str) -> list[dict[str, object]]:
        return [dict(row) for row in self.db.execute("SELECT * FROM attempts WHERE run_id=? ORDER BY id", (run_id,))]

    def foreign_interrupted(self, run_id: str) -> list[dict[str, object]]:
        """Interrupted entries from earlier runs: visible, never auto-resumed."""
        rows = self.db.execute("SELECT run_id, fetch_url, depth FROM frontier WHERE run_id<>? AND state='interrupted'", (run_id,))
        return [dict(row) for row in rows]


class RequestLedger:
    """Reserve-before-dispatch accounting plus a per-host pacing gate shared by every purpose."""

    def __init__(self, store: DiscoveryStore, run_id: str, budgets: Budgets, *, delay_seconds: float = 2.0,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.store, self.run_id, self.budgets, self.delay = store, run_id, budgets, delay_seconds
        self.clock = clock
        self.started = clock()
        self.total = self.page = self.bytes = 0
        self.last_dispatch: dict[str, float] = {}

    def check(self, purpose: Purpose) -> None:
        if self.clock() - self.started >= self.budgets.max_wall_seconds:
            raise BudgetExceeded("wall_clock_budget")
        if self.total >= self.budgets.max_total_attempts:
            raise BudgetExceeded("total_attempt_budget")
        if purpose is Purpose.HTML and self.page >= self.budgets.max_page_attempts:
            raise BudgetExceeded("page_attempt_budget")
        if self.bytes >= self.budgets.max_body_bytes:
            raise BudgetExceeded("byte_budget")

    def reserve(self, purpose: Purpose, url: str, hop: int = 0, note: str | None = None) -> int:
        self.check(purpose)
        self.total += 1
        if purpose is Purpose.HTML:
            self.page += 1
        cur = self.store.db.execute(
            "INSERT INTO attempts(run_id,purpose,host,url,hop,state,note,reserved_at) VALUES(?,?,?,?,?,'reserved',?,?)",
            (self.run_id, purpose.value, urlsplit(url).hostname, url, hop, note, _now()))
        self.store.db.commit()
        return int(cur.lastrowid)

    def pace(self, url: str) -> None:
        host = urlsplit(url).hostname or ""
        last = self.last_dispatch.get(host)
        if last is not None:
            time.sleep(max(0.0, self.delay - (self.clock() - last)))
        self.last_dispatch[host] = self.clock()

    def complete(self, attempt_id: int, *, status: int | None = None, error: str | None = None, nbytes: int = 0) -> None:
        self.bytes += nbytes
        self.store.db.execute("UPDATE attempts SET state=?, status=?, error=?, bytes=?, completed_at=? WHERE id=?",
                              ("failed" if error else "completed", status, error, nbytes, _now(), attempt_id))
        self.store.db.commit()

    def charge(self, purpose: Purpose, url: str, hop: int, status: int | None, note: str) -> None:
        """Account for a hop a legacy fetcher already performed internally (counted, never refused)."""
        self.total += 1
        if purpose is Purpose.HTML:
            self.page += 1
        self.store.db.execute(
            "INSERT INTO attempts(run_id,purpose,host,url,hop,state,status,note,bytes,reserved_at,completed_at) "
            "VALUES(?,?,?,?,?,'completed',?,?,0,?,?)",
            (self.run_id, purpose.value, urlsplit(url).hostname, url, hop, status, note, _now(), _now()))
        self.store.db.commit()

    def snapshot(self) -> dict[str, object]:
        return {"total_attempts": self.total, "page_attempts": self.page, "body_bytes": self.bytes,
                "elapsed_seconds": round(self.clock() - self.started, 3)}


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def validate_public_host(url: str, resolver: Callable[..., object] = socket.getaddrinfo) -> None:
    """Preflight address check. NOT sufficient against rebinding; connection-time pinning is the control."""
    host = urlsplit(url).hostname
    if not host:
        raise ValueError("URL has no hostname")
    _public_addresses(host, 443, resolver)


def _public_addresses(host: str, port: int, resolver: Callable[..., object]) -> list[str]:
    answers = resolver(host, port, type=socket.SOCK_STREAM)
    if not answers:
        raise ValueError("hostname did not resolve")
    addresses = []
    for answer in answers:
        address = answer[4][0]
        if not ipaddress.ip_address(address).is_global:
            raise ValueError(f"target resolved to non-public address: {address}")
        addresses.append(address)
    return addresses


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Resolves, validates and connects to the *same* validated address at connection time."""

    def __init__(self, *args, resolver: Callable[..., object] = socket.getaddrinfo, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._resolver = resolver

    def connect(self) -> None:
        port = self.port or 443
        last: Exception | None = None
        for address in _public_addresses(self.host, port, self._resolver):
            try:
                sock = socket.create_connection((address, port), self.timeout, self.source_address)
                break
            except OSError as exc:
                last = exc
        else:
            raise last or OSError("no usable address")
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


class PinnedHTTPSHandler(HTTPSHandler):
    def __init__(self, resolver: Callable[..., object] = socket.getaddrinfo) -> None:
        super().__init__(context=ssl.create_default_context())
        self._pin_resolver = resolver

    def https_open(self, req):  # noqa: ANN001
        def factory(host, **kwargs):  # noqa: ANN001
            return PinnedHTTPSConnection(host, resolver=self._pin_resolver, **kwargs)
        return self.do_open(factory, req, context=self._context)


def build_guarded_opener(resolver: Callable[..., object] = socket.getaddrinfo):
    # ProxyHandler({}) ignores HTTP(S)_PROXY/ALL_PROXY from the environment.
    return build_opener(ProxyHandler({}), NoRedirects(), PinnedHTTPSHandler(resolver))


def bounded_body(raw: bytes, encoding: str, max_bytes: int) -> bytes:
    encoding = (encoding or "identity").lower().strip()
    if encoding in {"", "identity"}:
        data = raw
    elif encoding in {"gzip", "x-gzip", "deflate"}:
        wbits = zlib.MAX_WBITS | 16 if "gzip" in encoding else zlib.MAX_WBITS
        decoder = zlib.decompressobj(wbits)
        data = decoder.decompress(raw, max_bytes + 1)
        if len(data) <= max_bytes and (not decoder.eof or decoder.unused_data):
            raise ValueError("incomplete or trailing compressed response")
    else:
        raise ValueError(f"unsupported content-encoding: {encoding}")
    if len(data) > max_bytes:
        raise ValueError("response exceeded byte ceiling")
    return data


ScopeCheck = Callable[[str, "str | None", Purpose], str]


class GuardedTransport:
    """Single-request-per-hop fetcher: every hop reserved, paced and settled through the ledger."""

    def __init__(self, ledger: RequestLedger, scope: ScopeCheck, *, timeout: float = 12.0,
                 resolver: Callable[..., object] = socket.getaddrinfo,
                 opener_factory: Callable[[], object] | None = None) -> None:
        self.ledger, self.scope, self.timeout, self.resolver = ledger, scope, timeout, resolver
        self.opener_factory = opener_factory or (lambda: build_guarded_opener(resolver))
        self.request_policy = None

    def fetch(self, url: str, purpose: Purpose = Purpose.HTML, max_bytes: int | None = None) -> FetchResponse:
        ceiling = min(max_bytes or RESPONSE_CEILING[purpose], RESPONSE_CEILING[purpose])
        opener = self.opener_factory()
        current = self.scope(url, None, purpose)
        redirects: list[dict[str, object]] = []
        seen = {current}
        for hop in range(MAX_REDIRECTS + 1):
            if self.request_policy is not None:
                self.request_policy(current, purpose)
            attempt = self.ledger.reserve(purpose, current, hop)
            response = None
            received = 0
            try:
                self.ledger.pace(current)
                remaining_time = self.ledger.budgets.max_wall_seconds - (self.ledger.clock() - self.ledger.started)
                if remaining_time <= 0:
                    raise BudgetExceeded("wall_clock_budget")
                validate_public_host(current, self.resolver)
                remaining_time = self.ledger.budgets.max_wall_seconds - (self.ledger.clock() - self.ledger.started)
                if remaining_time <= 0:
                    raise BudgetExceeded("wall_clock_budget")
                request = Request(current, headers={"User-Agent": USER_AGENT, "Accept": ACCEPT[purpose],
                                                    "Accept-Encoding": "gzip, identity"})
                try:
                    response = opener.open(request, timeout=min(self.timeout, remaining_time))
                except HTTPError as exc:
                    response = exc
                status = int(response.status)
                headers = {k.title(): v for k, v in response.headers.items()}
                if status in REDIRECT_STATUSES:
                    location = headers.get("Location")
                    self.ledger.complete(attempt, status=status)
                    if not location or hop >= MAX_REDIRECTS:
                        raise RuntimeError("redirect missing location or redirect limit exceeded")
                    target = self.scope(location, current, purpose)
                    if target in seen:
                        raise RedirectLoop("redirect loop")
                    seen.add(target)
                    redirects.append({"from": current, "to": target, "status": status, "validated": True})
                    current = target
                    continue
                # Never read beyond the aggregate body allowance, even on failures.
                # At an exact boundary, completeness is unknown: retain accounting but refuse
                # the response rather than silently accepting a potentially truncated body.
                remaining_bytes = self.ledger.budgets.max_body_bytes - self.ledger.bytes
                read_limit = min(ceiling + 1, remaining_bytes)
                chunks = []
                while received < read_limit:
                    if self.ledger.clock() - self.ledger.started >= self.ledger.budgets.max_wall_seconds:
                        raise BudgetExceeded("wall_clock_budget")
                    try:
                        chunk = response.read(min(65536, read_limit - received))
                    except http.client.IncompleteRead as exc:
                        received += len(exc.partial)
                        raise
                    if not chunk:
                        break
                    chunks.append(chunk)
                    received += len(chunk)
                raw = b"".join(chunks)
                if self.ledger.clock() - self.ledger.started >= self.ledger.budgets.max_wall_seconds:
                    raise BudgetExceeded("wall_clock_budget")
                if received >= remaining_bytes:
                    raise BudgetExceeded("byte_budget")
                if len(raw) > ceiling:
                    raise ValueError("response exceeded byte ceiling")
                body = bounded_body(raw, headers.get("Content-Encoding", ""), ceiling)
                self.ledger.complete(attempt, status=status, nbytes=len(raw))
                return FetchResponse(status, current, headers, body, tuple(redirects))
            except BaseException as exc:
                if self.ledger.store.db.execute("SELECT state FROM attempts WHERE id=?", (attempt,)).fetchone()[0] == "reserved":
                    self.ledger.complete(attempt, error=type(exc).__name__, nbytes=received)
                raise
            finally:
                if response is not None and hasattr(response, "close"):
                    response.close()
        raise RuntimeError("unreachable redirect state")


class LegacyFetcherTransport:
    """Adapts an injected ``fetcher(url, profile, timeout=, max_bytes=)`` to the ledger.

    The adapter reserves/paces the initial dispatch; hops the fetcher reports it followed internally
    are charged afterwards (they cannot be refused retroactively)."""

    def __init__(self, ledger: RequestLedger, fetcher: Callable[..., FetchResponse], profile, scope: ScopeCheck,
                 *, timeout: float) -> None:
        self.ledger, self.fetcher, self.profile, self.scope, self.timeout = ledger, fetcher, profile, scope, timeout
        self.request_policy = None

    def fetch(self, url: str, purpose: Purpose = Purpose.HTML, max_bytes: int | None = None) -> FetchResponse:
        url = self.scope(url, None, purpose)
        if self.request_policy is not None:
            self.request_policy(url, purpose)
        attempt = self.ledger.reserve(purpose, url)
        try:
            self.ledger.pace(url)
            response = self.fetcher(url, self.profile, timeout=self.timeout, max_bytes=max_bytes or RESPONSE_CEILING[purpose])
        except BaseException as exc:
            self.ledger.complete(attempt, error=type(exc).__name__)
            raise
        self.ledger.complete(attempt, status=response.status, nbytes=len(response.body))
        for number, hop in enumerate(response.redirects, 1):
            self.ledger.charge(purpose, str(hop.get("to", url)), number, int(hop.get("status") or 0), "reported_by_fetcher")
        # Legacy injections are trusted test adapters: validation here prevents acceptance,
        # but cannot undo requests the callback already followed internally.
        if self.request_policy is not None:
            for target in [str(hop.get("to", url)) for hop in response.redirects] + [response.url]:
                target = self.scope(target or url, url, purpose)
                self.request_policy(target, purpose)
        return response
