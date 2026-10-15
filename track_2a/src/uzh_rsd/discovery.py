"""Bounded site discovery through the guarded Scout transport (issue #35).

Sources: robots-declared sitemaps (index + gzip), feeds, navigation and page hreflang. Nothing is fetched
outside the ledger/budgets, no model is called, and ownership or translation is never inferred: a family
only joins URLs that some observed source explicitly linked, with direction and provenance retained.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import re
import socket
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import uuid
import xml.etree.ElementTree as ET
import zlib

from . import government_scout as gs
from .robots_policy import RobotsPolicy, RobotsDenied
from .discovery_transport import (
    Budgets, BudgetExceeded, DiscoveryStore, GuardedTransport, LegacyFetcherTransport, Purpose, RequestLedger,
    RESPONSE_CEILING, bounded_body,
)

SCHEMA = "lost-in-switzerland/discovery-snapshot/v1"
LANGUAGES = ("de", "fr", "it", "en")
SITE_PROFILES = {"bfe": "bfe-federal"}  # reviewed source profiles only; the rest are honestly unavailable
MAX_SITEMAP_DEPTH = 2
MAX_SITEMAPS = 8
MAX_URLS_PER_SITEMAP = 2000
DISCOVERY_BUDGETS = Budgets(max_page_attempts=6, max_total_attempts=20, max_body_bytes=10 * 1024 * 1024,
                            max_candidates=500, max_wall_seconds=300.0)


def profile_for_site(site_id: str):
    name = SITE_PROFILES.get(site_id)
    return gs.get_profile(name) if name else None


def preview(site_id: str, budgets: Budgets = DISCOVERY_BUDGETS) -> dict[str, object]:
    """What a start would do. No network."""
    profile = profile_for_site(site_id)
    if not profile:
        return {"site_id": site_id, "eligible": False, "reason": "no_reviewed_source_profile",
                "detail": "Listed in the directory only; no reviewed source profile, so nothing can be requested."}
    return {"site_id": site_id, "eligible": True, "profile": profile.id, "profile_version": profile.version,
            "hosts": list(profile.hosts), "seeds": list(profile.seeds), "budgets": asdict(budgets),
            "min_delay_seconds": 2.0, "languages": list(LANGUAGES),
            "sources": ["robots.txt sitemap declarations", "sitemap index / gzip", "feeds linked from seed pages",
                        "navigation and hreflang on seed pages"],
            "notes": ["Robots failure blocks the host.", "Seed pages only are fetched; other candidates stay unvisited.",
                      "Families record what sources declared; translation is not inferred."]}


class Observer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.nav: list[tuple[str, str | None]] = []
        self.alternates: list[tuple[str, str]] = []
        self.feeds: list[str] = []
        self._nav = 0

    def handle_starttag(self, tag, attrs):  # noqa: ANN001
        a = dict(attrs)
        if tag == "nav":
            self._nav += 1
        if tag == "a" and a.get("href") and (self._nav or a.get("hreflang")):
            self.nav.append((a["href"], (a.get("hreflang") or "").lower() or None))
        if tag == "link" and a.get("href"):
            rel = (a.get("rel") or "").lower().split()
            kind = (a.get("type") or "").lower()
            if "alternate" in rel and a.get("hreflang"):
                self.alternates.append((a["hreflang"].lower(), a["href"]))
            elif "alternate" in rel and kind in {"application/rss+xml", "application/atom+xml"}:
                self.feeds.append(a["href"])

    def handle_endtag(self, tag):  # noqa: ANN001
        if tag == "nav" and self._nav:
            self._nav -= 1


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_sitemap(body: bytes) -> tuple[str, list[dict[str, object]]]:
    """Return ('index'|'urlset', entries). DOCTYPE/entities are refused (no XML expansion)."""
    if re.search(rb"<!(?:DOCTYPE|ENTITY)", body.replace(b"\x00", b""), re.I):
        raise ValueError("sitemap DTD/entities refused")
    root = ET.fromstring(body)
    if _local(root.tag) not in {"sitemapindex", "urlset"}:
        raise ValueError("unsupported sitemap root")
    kind = "index" if _local(root.tag) == "sitemapindex" else "urlset"
    entries = []
    for node in root:
        loc = next((c.text.strip() for c in node if _local(c.tag) == "loc" and c.text), None)
        if not loc:
            continue
        alts = [(c.get("hreflang", "").lower(), c.get("href", "")) for c in node
                if _local(c.tag) == "link" and c.get("rel") == "alternate" and c.get("hreflang") and c.get("href")]
        entries.append({"loc": loc, "alternates": alts})
    return kind, entries


def parse_feed(body: bytes) -> list[str]:
    if re.search(rb"<!(?:DOCTYPE|ENTITY)", body.replace(b"\x00", b""), re.I):
        raise ValueError("feed DTD/entities refused")
    root = ET.fromstring(body)
    urls = []
    for node in root.iter():
        name = _local(node.tag)
        if name == "link":
            href = node.get("href") or (node.text or "").strip()
            if href and node.get("rel", "alternate") == "alternate":
                urls.append(href)
    return urls


def _lang_of(url: str, declared: str | None = None) -> tuple[str, str]:
    if declared:
        return declared.split("-", 1)[0], "declared"
    first = gs._path_locale(url).split("-", 1)[0]
    return (first, "path_prefix") if first else ("unknown", "none")


class Collector:
    def __init__(self, profile, max_candidates=500) -> None:  # noqa: ANN001
        self.profile = profile
        self.max_candidates = max_candidates
        self.candidates: dict[str, dict[str, object]] = {}
        self.edges: list[dict[str, object]] = []

    def add(self, url: str, kind: str, via: str, state: str = "observed_not_fetched", reason: str | None = None) -> str | None:
        try:
            clean = gs.fetch_url(url, self.profile, via if via.startswith("https://") else None)
        except ValueError as exc:
            key = url[:300]
            self.check_capacity(key)
            rec = self.candidates.setdefault(key, {"url": key, "state": "excluded", "reason": str(exc), "sources": []})
            rec["sources"].append({"kind": kind, "via": via})
            return None
        self.check_capacity(clean)
        rec = self.candidates.setdefault(clean, {"url": clean, "state": state, "reason": reason, "sources": []})
        rec["sources"].append({"kind": kind, "via": via})
        return clean

    def check_capacity(self, key):
        if key not in self.candidates and len(self.candidates) >= self.max_candidates:
            raise BudgetExceeded("candidate_budget")

    def edge(self, source: str, target: str, language: str, kind: str, declared_by: str) -> None:
        self.edges.append({"from": source, "to": target, "language": language.split("-", 1)[0], "kind": kind,
                           "declared_by": declared_by})


def families(collector: Collector) -> list[dict[str, object]]:
    parent: dict[str, str] = {}

    def find(x):  # noqa: ANN001
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for url, rec in collector.candidates.items():
        if rec["state"] != "excluded":
            find(url)
    for e in collector.edges:
        if e["from"] in parent and e["to"] in parent:
            parent[find(e["from"])] = find(e["to"])
    groups: dict[str, list[str]] = {}
    for url in sorted(parent):
        groups.setdefault(find(url), []).append(url)
    out = []
    for members in groups.values():
        member_edges = [e for e in collector.edges if e["from"] in members and e["to"] in members]
        langs: dict[str, list[dict[str, object]]] = {l: [] for l in LANGUAGES}
        langs["unknown"] = []
        declared_langs: dict[str, set[str]] = {}
        for e in member_edges:
            declared_langs.setdefault(e["to"], set()).add(e["language"])
        for url in members:
            declared = sorted(declared_langs.get(url, ()))
            lang, how = _lang_of(url, declared[0] if len(declared) == 1 else None)
            conflict = len(declared) > 1
            if conflict:
                lang, how = "unknown", "contradictory_declarations"
            langs.setdefault(lang if lang in LANGUAGES else "unknown", []).append(
                {"url": url, "language_source": how, "state": collector.candidates[url]["state"]})
        pairs = {(e["from"], e["to"]) for e in member_edges}
        contradictions = []
        for lang in LANGUAGES:
            if len(langs[lang]) > 1:
                contradictions.append({"language": lang, "urls": [m["url"] for m in langs[lang]],
                                       "detail": "more than one URL declared or placed for this language"})
        for url, ls in declared_langs.items():
            if len(ls) > 1:
                contradictions.append({"url": url, "languages": sorted(ls), "detail": "declared under different languages"})
        directional = [e for e in member_edges if (e["to"], e["from"]) not in pairs]
        status = ("contradictory" if contradictions else "single_page" if len(members) == 1
                  else "one_directional" if directional else "reciprocal_declarations")
        out.append({
            "family_id": sha256("\n".join(members).encode()).hexdigest()[:16], "status": status,
            "languages": {l: langs[l] for l in LANGUAGES}, "unknown_language": langs["unknown"],
            "language_availability": {l: ("observed" if langs[l] else "not_observed") for l in LANGUAGES},
            "edges": member_edges, "contradictions": contradictions, "member_count": len(members),
            "note": "not_observed means no fetched source declared it; it is not evidence of absence or of a translation."})
    return sorted(out, key=lambda f: f["family_id"])


def _body(response, ceiling):  # noqa: ANN001
    raw = response.body
    if raw[:2] == b"\x1f\x8b":
        return bounded_body(raw, "gzip", ceiling)
    return raw


def discover(site_id: str, *, fetcher=None, budgets: Budgets = DISCOVERY_BUDGETS, delay_seconds: float = 2.0,
             frontier_path=None, progress=None, resolver=socket.getaddrinfo, timeout: float = 12.0) -> dict[str, object]:
    profile = profile_for_site(site_id)
    if not profile:
        raise ValueError("no reviewed source profile for this site")
    run_id = uuid.uuid4().hex[:12]
    store = DiscoveryStore(str(frontier_path) if frontier_path else None)
    store.begin_run(run_id, profile.id, {"discovery": True, "budgets": asdict(budgets), "site_id": site_id})
    ledger = RequestLedger(store, run_id, budgets, delay_seconds=delay_seconds)
    scope = gs._scope_check(profile)
    transport = (LegacyFetcherTransport(ledger, fetcher, profile, scope, timeout=timeout) if fetcher
                 else GuardedTransport(ledger, scope, timeout=timeout, resolver=resolver))
    col = Collector(profile, budgets.max_candidates)
    request_policy = RobotsPolicy({})
    transport.request_policy = request_policy
    notes: list[dict[str, object]] = []
    stop = "completed"

    def step(phase):  # noqa: ANN001
        if progress:
            progress({"phase": phase, **ledger.snapshot(), "candidates": len(col.candidates)})
    try:
        host = profile.hosts[0]
        robots_url = f"https://{host}/robots.txt"
        step("robots")
        robot, sitemaps_declared = None, []
        try:
            r = transport.fetch(robots_url, Purpose.ROBOTS)
            if r.status != 200:
                raise RuntimeError(f"robots HTTP {r.status}")
            if urlsplit(r.url).hostname != host:
                raise ValueError("robots redirect changed host")
            robot = RobotFileParser()
            robot.parse(gs.decode_html(r.body, r.headers.get("Content-Type", "")).splitlines())
            sitemaps_declared = robot.site_maps() or []
            notes.append({"source": "robots", "state": "loaded", "sitemaps_declared": len(sitemaps_declared)})
        except BudgetExceeded:
            raise
        except Exception as exc:
            notes.append({"source": "robots", "state": "unavailable", "detail": type(exc).__name__})
        if robot is None:
            stop = "robots_unavailable"
            raise _Stop
        request_policy.rules[host] = robot
        # sitemaps (index recursion, cycle guard, depth/count ceilings)
        queue = [(u, 0, "robots") for u in sitemaps_declared]
        seen_maps: set[str] = set()
        fetched_maps = 0
        while queue:
            url, depth, via = queue.pop(0)
            try:
                clean = gs.fetch_url(url, profile, allow_assets=True)
            except ValueError as exc:
                notes.append({"source": "sitemap", "url": url[:300], "state": "excluded", "detail": str(exc)})
                continue
            if clean in seen_maps:
                notes.append({"source": "sitemap", "url": clean, "state": "cycle_or_duplicate_skipped"})
                continue
            seen_maps.add(clean)
            if depth > MAX_SITEMAP_DEPTH or fetched_maps >= MAX_SITEMAPS:
                notes.append({"source": "sitemap", "url": clean, "state": "unvisited_ceiling"})
                continue
            if not robot.can_fetch(gs.USER_AGENT, clean):
                notes.append({"source": "sitemap", "url": clean, "state": "blocked_robots"})
                continue
            step("sitemap")
            fetched_maps += 1
            try:
                resp = transport.fetch(clean, Purpose.SITEMAP)
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                kind, entries = parse_sitemap(_body(resp, RESPONSE_CEILING[Purpose.SITEMAP]))
            except BudgetExceeded:
                raise
            except RobotsDenied as exc:
                notes.append({"source": "request_policy", "url": exc.url, "state": "blocked", "detail": exc.reason})
                continue
            except (Exception, zlib.error) as exc:
                notes.append({"source": "sitemap", "url": clean, "state": "failed", "detail": type(exc).__name__})
                continue
            notes.append({"source": "sitemap", "url": clean, "state": "loaded", "kind": kind, "entries": len(entries), "depth": depth})
            if kind == "index":
                queue += [(e["loc"], depth + 1, clean) for e in entries]
                continue
            for e in entries[:MAX_URLS_PER_SITEMAP]:
                page = col.add(e["loc"], "sitemap", clean)
                if page:
                    for lang, href in e["alternates"]:
                        target = col.add(href, "sitemap_alternate", clean)
                        if target:
                            col.edge(page, target, lang, "sitemap_hreflang", clean)
            if len(entries) > MAX_URLS_PER_SITEMAP:
                notes.append({"source": "sitemap", "url": clean, "state": "truncated", "entries": len(entries)})
        # seed pages: navigation, hreflang, feeds
        feeds: list[tuple[str, str]] = []
        for seed in profile.seeds:
            seed_url = gs.fetch_url(seed, profile)
            col.add(seed_url, "seed", "profile")
            if not robot.can_fetch(gs.USER_AGENT, seed_url):
                col.candidates[seed_url].update(state="blocked", reason="robots_disallow")
                continue
            step("pages")
            try:
                resp = transport.fetch(seed_url, Purpose.HTML)
                if resp.status != 200 or not resp.headers.get("Content-Type", "").lower().startswith("text/html"):
                    raise RuntimeError(f"HTTP {resp.status} / not HTML")
            except BudgetExceeded:
                raise
            except RobotsDenied as exc:
                col.candidates[seed_url].update(state="blocked", reason=exc.reason, blocked_url=exc.url)
                continue
            except Exception as exc:
                col.candidates[seed_url].update(state="failed", reason=type(exc).__name__)
                continue
            col.candidates[seed_url].update(state="fetched", reason=None, final_url=resp.url, redirects=list(resp.redirects))
            document_url = resp.url
            obs = Observer()
            obs.feed(gs.decode_html(resp.body, resp.headers.get("Content-Type", "")))
            for lang, href in obs.alternates:
                target = col.add(href, "page_hreflang", document_url)
                if target:
                    col.edge(seed_url, target, lang, "page_hreflang", seed_url)
            for href, lang in obs.nav:
                target = col.add(href, "navigation", document_url)
                if target and lang:
                    col.edge(seed_url, target, lang, "navigation_hreflang", seed_url)
            feeds += [(f, document_url) for f in obs.feeds]
        for href, via in feeds:
            try:
                feed = gs.fetch_url(href, profile, via, allow_assets=True)
            except ValueError as exc:
                notes.append({"source": "feed", "url": href[:300], "state": "excluded", "detail": str(exc)})
                continue
            if not robot.can_fetch(gs.USER_AGENT, feed):
                notes.append({"source": "feed", "url": feed, "state": "blocked_robots"})
                continue
            step("feeds")
            try:
                resp = transport.fetch(feed, Purpose.FEED)
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                links = parse_feed(_body(resp, RESPONSE_CEILING[Purpose.FEED]))
            except BudgetExceeded:
                raise
            except RobotsDenied as exc:
                notes.append({"source": "request_policy", "url": exc.url, "state": "blocked", "detail": exc.reason})
                continue
            except (Exception, zlib.error) as exc:
                notes.append({"source": "feed", "url": feed, "state": "failed", "detail": type(exc).__name__})
                continue
            notes.append({"source": "feed", "url": feed, "state": "loaded", "entries": len(links)})
            for link in links:
                col.add(link, "feed", feed)
    except BudgetExceeded as exc:
        stop = exc.reason
    except _Stop:
        pass
    finally:
        counts_unvisited = sum(1 for c in col.candidates.values() if c["state"] == "observed_not_fetched")
        snapshot = {
            "schema": SCHEMA, "id": uuid.uuid4().hex, "site_id": site_id, "profile": profile.id,
            "profile_version": profile.version, "observed_at": datetime.now(timezone.utc).isoformat(),
            "stop_reason": stop, "budgets": asdict(budgets), "accounting": ledger.snapshot(),
            "policy_decisions": request_policy.decisions,
            "sources": notes, "candidates": sorted(col.candidates.values(), key=lambda c: c["url"]),
            "unvisited_count": counts_unvisited, "families": families(col), "languages": list(LANGUAGES),
            "model_calls": 0,
            "disclaimer": "Observed links only. Families are source-declared groupings; not verified translations, and not ownership claims.",
        }
        store.end_run(run_id, stop)
        store.close()
    if progress:
        progress({"phase": "done", **snapshot["accounting"], "candidates": len(col.candidates)})
    return snapshot


class _Stop(Exception):
    pass
