"""Versioned, profile-scoped government page discovery.

No browser actions, form submissions, sitemap expansion or model calls occur.
Network use is opt-in and every request is constrained to exact HTTPS hosts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import socket
import time
from typing import Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import ProxyHandler, build_opener
from urllib.robotparser import RobotFileParser
import uuid
from dataclasses import replace

from .discovery_transport import (
    Budgets, BudgetExceeded, DiscoveryStore, FetchResponse, GuardedTransport, LegacyFetcherTransport, NoRedirects,
    PinnedHTTPSHandler, Purpose, RequestLedger, RESPONSE_CEILING, USER_AGENT, MAX_REDIRECTS, validate_public_host,
)

PROFILE_SCHEMA = "lost-in-switzerland/government-source-profile/v1"
SCOUT_SCHEMA = "lost-in-switzerland/government-scout/v1"
MAX_BODY_BYTES = 1_000_000
MAX_ROBOTS_BYTES = 128_000
ASSET = re.compile(r"\.(?:jpg|jpeg|png|gif|webp|svg|ico|css|js|json|xml|zip|mp4|mp3|woff2?|ttf|pdf|docx?|xlsx?)$", re.I)
TRACKING = {"fbclid", "gclid", "pk_campaign", "pk_kwd"}
NOISE = re.compile(r"impressum|datenschutz|privacy|cookie|login|newsletter|social", re.I)


@dataclass(frozen=True)
class SourceProfile:
    id: str
    hosts: tuple[str, ...]
    seeds: tuple[str, ...]
    languages: tuple[str, ...]
    version: str = "1"
    schema: str = PROFILE_SCHEMA


# Ordering is part of the public contract.
PROFILES: tuple[SourceProfile, ...] = (
    SourceProfile("bfe-federal", ("www.bfe.admin.ch",), (
        "https://www.bfe.admin.ch/de/dunstabzugshauben",
        "https://www.bfe.admin.ch/fr/hottes-domestiques",
    ), ("de", "fr")),
    SourceProfile("ch-citizen", ("www.ch.ch",), (
        "https://www.ch.ch/en/work/working-in-switzerland-as-a-foreign-national/",
    ), ("de", "fr", "it", "en")),
    SourceProfile("zurich-city", ("www.stadt-zuerich.ch",), (
        "https://www.stadt-zuerich.ch/de/lebenslagen/neu-in-zuerich",
    ), ("de", "en")),
)
PROFILE_ALIASES = {
    "bfe": "bfe-federal", "federal": "bfe-federal", "ch": "ch-citizen",
    "zurich": "zurich-city", "stadt-zuerich": "zurich-city",
}


def get_profile(value: str | SourceProfile) -> SourceProfile:
    if isinstance(value, SourceProfile):
        return value
    wanted = PROFILE_ALIASES.get(value, value)
    for profile in PROFILES:
        if profile.id == wanted:
            return profile
    raise ValueError(f"unknown source profile: {value}")


def normalize_url(value: str, profile: str | SourceProfile, base: str | None = None) -> str:
    """Return stable URL identity after enforcing an exact-host HTTPS allowlist."""
    selected = get_profile(profile)
    parts = urlsplit(urljoin(base or "", value))
    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError("invalid URL port") from exc
    host = (parts.hostname or "").lower()
    if (parts.scheme != "https" or host not in selected.hosts or parts.username is not None
            or parts.password is not None or port is not None):
        raise ValueError("out-of-scope URL (HTTPS, no credentials/port, exact approved host required)")
    path = parts.path.rstrip("/") or "/"
    if ASSET.search(path):
        raise ValueError("non-HTML asset excluded")
    query = urlencode(sorted(
        (key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING
    ))
    return urlunsplit(("https", host, path, query, ""))


def fetch_url(value: str, profile: str | SourceProfile, base: str | None = None, *, allow_assets: bool = False) -> str:
    """Scope-check and return the URL to request, preserving meaningful distinctions.

    Unlike ``normalize_url`` (legacy display/capture identity), trailing slashes, query order and
    tracking-looking parameters are kept; only the fragment is dropped and scheme/host lower-cased."""
    selected = get_profile(profile)
    parts = urlsplit(urljoin(base or "", value))
    try:
        port = parts.port
    except ValueError as exc:
        raise ValueError("invalid URL port") from exc
    host = (parts.hostname or "").lower()
    if (parts.scheme != "https" or host not in selected.hosts or parts.username is not None
            or parts.password is not None or port is not None):
        raise ValueError("out-of-scope URL (HTTPS, no credentials/port, exact approved host required)")
    path = parts.path or "/"
    if not allow_assets and ASSET.search(path):
        raise ValueError("non-HTML asset excluded")
    return urlunsplit(("https", host, path, parts.query, ""))


def dedup_key(url: str) -> str:
    """Frontier identity for an already scope-checked fetch URL (distinct from the legacy normalised form)."""
    return url


class PageLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[str] = []
        self.alternates: dict[str, list[str]] = {}
        self.canonicals: list[str] = []
        self.title = ""
        self.html_lang: str | None = None
        self._title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html" and values.get("lang"):
            self.html_lang = (values["lang"] or "").lower()
        if tag == "a" and values.get("href"):
            self.anchors.append(values["href"] or "")
        if tag == "link" and values.get("href"):
            rel = (values.get("rel") or "").lower().split()
            if "alternate" in rel and values.get("hreflang"):
                self.alternates.setdefault((values.get("hreflang") or "").lower(), []).append(values["href"] or "")
            if "canonical" in rel:
                self.canonicals.append(values["href"] or "")
        if tag == "title":
            self._title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._title = False

    def handle_data(self, data: str) -> None:
        if self._title:
            self.title += data


def decode_html(body: bytes, content_type: str = "") -> str:
    match = re.search(r"charset\s*=\s*['\"]?([\w.-]+)", content_type, re.I)
    if not match:
        match = re.search(r"charset\s*=\s*['\"]?([\w.-]+)", body[:4096].decode("ascii", "ignore"), re.I)
    encoding = match.group(1) if match else "utf-8"
    try:
        return body.decode(encoding, errors="strict")
    except (LookupError, UnicodeDecodeError):
        return body.decode("utf-8", errors="replace")


def parse_page(body: bytes, url: str, profile: str | SourceProfile,
               content_type: str = "text/html; charset=utf-8") -> tuple[PageLinks, dict[str, list[str]], str | None]:
    parser = PageLinks()
    parser.feed(decode_html(body, content_type))
    normalized: dict[str, list[str]] = {}
    for lang, links in parser.alternates.items():
        for link in links:
            try:
                target = normalize_url(link, profile, url)
            except ValueError:
                continue
            normalized.setdefault(lang, []).append(target)
    canonical = None
    for link in parser.canonicals:
        try:
            canonical = normalize_url(link, profile, url)
            break
        except ValueError:
            continue
    return parser, normalized, canonical


@dataclass(frozen=True)
class Captured:
    url: str
    retrieved_at_utc: str
    sha256_html: str
    title: str
    depth: int
    alternates: dict[str, list[str]]
    canonical: str | None
    locale: str | None = None
    status: str = "FETCHED"
    extraction_version: str = "lis-html-links-v2"
    requested_url: str | None = None
    final_url: str | None = None


def potential_pairs(pages: list[Captured], left_language: str, right_language: str) -> list[dict[str, object]]:
    """Require reciprocal hreflang; topical similarity is deliberately ignored."""
    lookup = {page.url: page for page in pages}
    pairs: dict[tuple[str, str], dict[str, object]] = {}
    for page in pages:
        for lang, targets in page.alternates.items():
            if lang.split("-", 1)[0] not in {left_language, right_language}:
                continue
            for target_url in targets:
                target = lookup.get(target_url)
                if not target or target.url == page.url:
                    continue
                if not any(page.url in destinations for destinations in target.alternates.values()):
                    continue
                page_lang = (page.locale or _path_locale(page.url)).split("-", 1)[0]
                target_lang = (target.locale or _path_locale(target.url)).split("-", 1)[0]
                if {page_lang, target_lang} != {left_language, right_language}:
                    continue
                left_url = page.url if page_lang == left_language else target.url
                right_url = page.url if page_lang == right_language else target.url
                pairs[(left_url, right_url)] = {
                    left_language: left_url, right_language: right_url,
                    "pairing_evidence": ["reciprocal_hreflang"], "status": "CANDIDATE", "reviewer": None,
                }
    return [pairs[key] for key in sorted(pairs)]


def _path_locale(url: str) -> str:
    first = urlsplit(url).path.strip("/").split("/", 1)[0].lower()
    return first if re.fullmatch(r"[a-z]{2}(?:-[a-z]{2})?", first) else ""


def _scope_check(profile: SourceProfile) -> Callable[[str, "str | None", Purpose], str]:
    return lambda value, base, purpose: fetch_url(value, profile, base,
                                                  allow_assets=purpose in {Purpose.SITEMAP, Purpose.FEED})


def _network_fetch(url: str, profile: SourceProfile, *, timeout: float, max_bytes: int,
                   resolver: Callable[..., object] = socket.getaddrinfo) -> FetchResponse:
    """One-shot guarded fetch (own ledger, no pacing). Scout itself uses a shared ledger."""
    with DiscoveryStore() as store:
        ledger = RequestLedger(store, "one-shot", Budgets(), delay_seconds=0.0)
        transport = GuardedTransport(ledger, _scope_check(profile), timeout=timeout, resolver=resolver,
                                     opener_factory=lambda: build_opener(
                                         ProxyHandler({}), NoRedirects(), PinnedHTTPSHandler(resolver)))
        return transport.fetch(url, Purpose.HTML, max_bytes)


def candidate_score(url: str) -> int:
    return (-8 if NOISE.search(url) else 0) - max(0, len(urlsplit(url).path.split("/")) - 4)


def scout(profile: str | SourceProfile, *, seeds: list[str] | tuple[str, ...] | None = None,
          max_pages: int = 20, max_depth: int = 2, delay_seconds: float = 2.0,
          timeout: float = 12.0, out: str | Path | None = None,
          fetcher: Callable[..., FetchResponse] | None = None,
          budgets: Budgets | None = None, frontier_path: str | Path | None = None,
          resolver: Callable[..., object] = socket.getaddrinfo) -> dict[str, object]:
    """Run a bounded crawl through one request ledger. Robots retrieval is fail-closed per host.

    ``max_pages`` caps HTML attempts (redirect hops and failures included). ``frontier_path`` makes the
    frontier/attempt ledger durable; reopening never resumes or replays interrupted work."""
    selected = get_profile(profile)
    if not 1 <= max_pages <= 20 or not 0 <= max_depth <= 2 or delay_seconds < 2.0:
        raise ValueError("pilot limits: pages 1..20, depth 0..2, delay >=2 seconds")
    selected_seeds = tuple(seeds if seeds is not None else selected.seeds)
    if not selected_seeds:
        raise ValueError("profile has no approved seeds; pass an explicit allowlisted seed")
    seed_urls = tuple(fetch_url(seed, selected) for seed in selected_seeds)
    normalized_seeds = tuple(normalize_url(seed, selected) for seed in selected_seeds)
    limits = replace(budgets or Budgets(), max_page_attempts=max_pages)
    run_id = uuid.uuid4().hex[:12]
    store = DiscoveryStore(str(frontier_path) if frontier_path else None)
    store.begin_run(run_id, selected.id, {"max_pages": max_pages, "max_depth": max_depth, "delay_seconds": delay_seconds,
                                          "budgets": asdict(limits), "profile": selected.id, "profile_version": selected.version})
    ledger = RequestLedger(store, run_id, limits, delay_seconds=delay_seconds)
    scope = _scope_check(selected)
    transport = (LegacyFetcherTransport(ledger, fetcher, selected, scope, timeout=timeout) if fetcher
                 else GuardedTransport(ledger, scope, timeout=timeout, resolver=resolver,
                                       opener_factory=lambda: build_opener(
                                           ProxyHandler({}), NoRedirects(), PinnedHTTPSHandler(resolver))))
    audit: list[dict[str, object]] = []
    robots: dict[str, RobotFileParser | None] = {}
    pages: list[Captured] = []
    candidates = 0
    stop_reason = "frontier_exhausted"
    for url in seed_urls:
        store.enqueue(run_id, dedup_key(url), url, 0, None)
    try:
        while True:
            queued = sorted(store.queued(run_id), key=lambda r: (-candidate_score(r["fetch_url"]), r["depth"], r["fetch_url"]))
            if not queued:
                break
            row = queued[0]
            url, key, depth = row["fetch_url"], row["dedup_key"], row["depth"]
            store.set_state(run_id, key, "leased")
            host = urlsplit(url).hostname or ""
            try:
                if host not in robots:
                    robots[host] = _load_robots(transport, host, audit)
                robot = robots[host]
                if robot is None:
                    store.set_state(run_id, key, "blocked", "robots_unavailable")
                    continue
                if not robot.can_fetch(USER_AGENT, url):
                    audit.append({"url": url, "state": "ROBOTS_DISALLOW"})
                    store.set_state(run_id, key, "blocked", "robots_disallow")
                    continue
                response = transport.fetch(url, Purpose.HTML, RESPONSE_CEILING[Purpose.HTML])
                if response.status != 200:
                    audit.append({"url": url, "state": "HTTP_ERROR", "status": response.status})
                    store.set_state(run_id, key, "failed", "http_error", response.status)
                    continue
                content_type = response.headers.get("Content-Type", "")
                if not content_type.lower().startswith("text/html"):
                    audit.append({"url": url, "state": "NON_HTML_REFUSED", "content_type": content_type})
                    store.set_state(run_id, key, "excluded", "non_html", response.status)
                    continue
                actual = normalize_url(response.url, selected)
                parsed, alternates, canonical = parse_page(response.body, actual, selected, content_type)
                pages.append(Captured(actual, datetime.now(timezone.utc).isoformat(), sha256(response.body).hexdigest(),
                                      parsed.title.strip()[:180], depth, alternates, canonical,
                                      (parsed.html_lang or "").lower() or None,
                                      requested_url=url, final_url=response.url))
                audit.append({"url": url, "state": "FETCHED", "redirects": list(response.redirects)})
                store.set_state(run_id, key, "fetched", None, response.status)
                if depth < max_depth:
                    for href in parsed.anchors:
                        try:
                            target = fetch_url(href, selected, response.url)
                        except ValueError as exc:
                            audit.append({"url": href, "source": actual, "state": "LINK_REFUSED", "detail": str(exc)})
                            continue
                        if candidates >= limits.max_candidates:
                            store.enqueue(run_id, dedup_key(target), target, depth + 1, actual, "excluded", "candidate_ceiling")
                            continue
                        if store.enqueue(run_id, dedup_key(target), target, depth + 1, actual):
                            candidates += 1
            except BudgetExceeded as exc:
                stop_reason = exc.reason
                store.set_state(run_id, key, "queued")
                break
            except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, ValueError) as exc:
                audit.append({"url": url, "state": "REQUEST_REFUSED_OR_FAILED", "detail": type(exc).__name__})
                store.set_state(run_id, key, "failed", type(exc).__name__)
        unvisited = store.mark_unvisited(run_id, stop_reason)
        store.end_run(run_id, stop_reason)
        snapshot = ledger.snapshot()
        left, right = selected.languages[:2]
        result = {
            "schema": SCOUT_SCHEMA, "profile": asdict(selected), "seeds": list(normalized_seeds),
            "retrieval_policy": {"max_pages": max_pages, "max_depth": max_depth, "delay_seconds": delay_seconds,
                "max_body_bytes": RESPONSE_CEILING[Purpose.HTML], "timeout_seconds": timeout,
                "budgets": asdict(limits), "budget_defaults_status": "proposed, not yet frozen (except pages/depth/delay)",
                "redirects": f"manual, <= {MAX_REDIRECTS}, revalidated each hop, every hop counted",
                "robots": "fail_closed_per_host", "proxies": "environment ignored",
                "address_enforcement": "validated at connection time (pinned), not preflight only"},
            "captured": [asdict(page) for page in pages], "pairs": potential_pairs(pages, left, right),
            "audit": audit, "request_count": snapshot["total_attempts"], "page_request_count": snapshot["page_attempts"],
            "model_calls": 0, "stop_reason": stop_reason, "unvisited_count": unvisited, "run_id": run_id,
            "accounting": snapshot, "frontier": {"counts": store.counts(run_id), "entries": store.entries(run_id)},
            "attempts": store.attempts(run_id),
            "interrupted_from_earlier_runs": store.foreign_interrupted(run_id),
            "disclaimer": "Unlabelled live sources; candidates are not semantic findings or benchmark results.",
        }
    finally:
        store.close()
    if out:
        _write_json(out, result)
    return result


def _load_robots(transport, host: str, audit: list[dict[str, object]]) -> RobotFileParser | None:  # noqa: ANN001
    robots_url = f"https://{host}/robots.txt"
    try:
        response = transport.fetch(robots_url, Purpose.ROBOTS, RESPONSE_CEILING[Purpose.ROBOTS])
        if response.status != 200:
            raise RuntimeError(f"robots returned HTTP {response.status}")
        robot = RobotFileParser()
        robot.parse(decode_html(response.body, response.headers.get("Content-Type", "")).splitlines())
        audit.append({"url": robots_url, "state": "ROBOTS_LOADED", "sha256": sha256(response.body).hexdigest()})
        return robot
    except BudgetExceeded:
        raise
    except Exception as exc:
        audit.append({"url": robots_url, "state": "ROBOTS_UNAVAILABLE", "detail": type(exc).__name__})
        return None


def _write_json(path: str | Path, value: object) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
