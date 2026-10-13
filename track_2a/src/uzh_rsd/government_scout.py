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
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

USER_AGENT = "LostInSwitzerlandResearch/1.0 (+https://github.com/blackmath88/apertushackathon-uzh; bounded audit)"
PROFILE_SCHEMA = "lost-in-switzerland/government-source-profile/v1"
SCOUT_SCHEMA = "lost-in-switzerland/government-scout/v1"
MAX_BODY_BYTES = 1_000_000
MAX_ROBOTS_BYTES = 128_000
MAX_REDIRECTS = 3
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


def validate_public_host(url: str, resolver: Callable[..., object] = socket.getaddrinfo) -> None:
    """Reject private/special DNS answers immediately before each request."""
    host = urlsplit(url).hostname
    if not host:
        raise ValueError("URL has no hostname")
    answers = resolver(host, 443, type=socket.SOCK_STREAM)
    if not answers:
        raise ValueError("hostname did not resolve")
    for answer in answers:
        address = answer[4][0]
        if not ipaddress.ip_address(address).is_global:
            raise ValueError(f"target resolved to non-public address: {address}")


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


@dataclass(frozen=True)
class FetchResponse:
    status: int
    url: str
    headers: Mapping[str, str]
    body: bytes
    redirects: tuple[dict[str, object], ...] = ()


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _network_fetch(url: str, profile: SourceProfile, *, timeout: float, max_bytes: int,
                   resolver: Callable[..., object] = socket.getaddrinfo) -> FetchResponse:
    opener = build_opener(NoRedirects())
    current = normalize_url(url, profile)
    redirects: list[dict[str, object]] = []
    for hop in range(MAX_REDIRECTS + 1):
        validate_public_host(current, resolver)
        try:
            response = opener.open(Request(current, headers={"User-Agent": USER_AGENT, "Accept": "text/html"}), timeout=timeout)
        except HTTPError as exc:
            response = exc
        status = int(response.status)
        if status in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location")
            if not location or hop >= MAX_REDIRECTS:
                raise RuntimeError("redirect missing location or redirect limit exceeded")
            target = normalize_url(location, profile, current)
            validate_public_host(target, resolver)
            redirects.append({"from": current, "to": target, "status": status, "validated": True})
            current = target
            continue
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError("response exceeded byte ceiling")
        return FetchResponse(status, current, dict(response.headers.items()), body, tuple(redirects))
    raise RuntimeError("unreachable redirect state")


def candidate_score(url: str) -> int:
    return (-8 if NOISE.search(url) else 0) - max(0, len(urlsplit(url).path.split("/")) - 4)


def scout(profile: str | SourceProfile, *, seeds: list[str] | tuple[str, ...] | None = None,
          max_pages: int = 20, max_depth: int = 2, delay_seconds: float = 2.0,
          timeout: float = 12.0, out: str | Path | None = None,
          fetcher: Callable[..., FetchResponse] | None = None) -> dict[str, object]:
    """Run a bounded crawl. Robots retrieval failure always refuses page requests."""
    selected = get_profile(profile)
    if not 1 <= max_pages <= 20 or not 0 <= max_depth <= 2 or delay_seconds < 2.0:
        raise ValueError("pilot limits: pages 1..20, depth 0..2, delay >=2 seconds")
    selected_seeds = tuple(seeds if seeds is not None else selected.seeds)
    if not selected_seeds:
        raise ValueError("profile has no approved seeds; pass an explicit allowlisted seed")
    normalized_seeds = tuple(normalize_url(seed, selected) for seed in selected_seeds)
    transport = fetcher or _network_fetch
    audit: list[dict[str, object]] = []
    robots_url = f"https://{selected.hosts[0]}/robots.txt"
    request_count = 0
    try:
        robots_response = transport(robots_url, selected, timeout=timeout, max_bytes=MAX_ROBOTS_BYTES)
        request_count += 1
        if robots_response.status != 200:
            raise RuntimeError(f"robots returned HTTP {robots_response.status}")
        robot = RobotFileParser()
        robot.parse(decode_html(robots_response.body, robots_response.headers.get("Content-Type", "")).splitlines())
        audit.append({"url": robots_url, "state": "ROBOTS_LOADED", "sha256": sha256(robots_response.body).hexdigest()})
    except Exception as exc:
        result: dict[str, object] = {
            "schema": SCOUT_SCHEMA, "profile": asdict(selected), "seeds": list(normalized_seeds),
            "captured": [], "pairs": [],
            "audit": [{"url": robots_url, "state": "ROBOTS_UNAVAILABLE", "detail": type(exc).__name__}],
            "request_count": request_count, "page_request_count": 0, "model_calls": 0,
        }
        if out:
            _write_json(out, result)
        return result

    queue = [(seed, 0) for seed in normalized_seeds]
    queued, seen = set(normalized_seeds), set()
    pages: list[Captured] = []
    # Robots is a host request too; delay before the first content request.
    last_request: float | None = time.monotonic()
    while queue and len(seen) < max_pages:
        queue.sort(key=lambda item: (-candidate_score(item[0]), item[1], item[0]))
        url, depth = queue.pop(0)
        if url in seen or depth > max_depth:
            continue
        seen.add(url)
        if not robot.can_fetch(USER_AGENT, url):
            audit.append({"url": url, "state": "ROBOTS_DISALLOW"})
            continue
        if last_request is not None:
            time.sleep(max(0.0, delay_seconds - (time.monotonic() - last_request)))
        last_request = time.monotonic()
        try:
            response = transport(url, selected, timeout=timeout, max_bytes=MAX_BODY_BYTES)
            request_count += 1
            if response.status != 200:
                audit.append({"url": url, "state": "HTTP_ERROR", "status": response.status})
                continue
            content_type = response.headers.get("Content-Type", "")
            if not content_type.lower().startswith("text/html"):
                audit.append({"url": url, "state": "NON_HTML_REFUSED", "content_type": content_type})
                continue
            actual = normalize_url(response.url, selected)
            parsed, alternates, canonical = parse_page(response.body, actual, selected, content_type)
            pages.append(Captured(actual, datetime.now(timezone.utc).isoformat(), sha256(response.body).hexdigest(),
                                  parsed.title.strip()[:180], depth, alternates, canonical,
                                  (parsed.html_lang or "").lower() or None))
            audit.append({"url": url, "state": "FETCHED", "redirects": list(response.redirects)})
            if depth < max_depth:
                for href in parsed.anchors:
                    try:
                        target = normalize_url(href, selected, actual)
                    except ValueError as exc:
                        audit.append({"url": href, "source": actual, "state": "LINK_REFUSED", "detail": str(exc)})
                        continue
                    if target not in seen and target not in queued:
                        queued.add(target)
                        queue.append((target, depth + 1))
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, ValueError) as exc:
            audit.append({"url": url, "state": "REQUEST_REFUSED_OR_FAILED", "detail": type(exc).__name__})
    left, right = selected.languages[:2]
    result = {
        "schema": SCOUT_SCHEMA, "profile": asdict(selected), "seeds": list(normalized_seeds),
        "retrieval_policy": {"max_pages": max_pages, "max_depth": max_depth, "delay_seconds": delay_seconds,
            "max_body_bytes": MAX_BODY_BYTES, "timeout_seconds": timeout,
            "redirects": f"manual, <= {MAX_REDIRECTS}, revalidated each hop", "robots": "fail_closed"},
        "captured": [asdict(page) for page in pages], "pairs": potential_pairs(pages, left, right),
        "audit": audit, "request_count": request_count, "page_request_count": max(0, request_count - 1),
        "model_calls": 0,
        "disclaimer": "Unlabelled live sources; candidates are not semantic findings or benchmark results.",
    }
    if out:
        _write_json(out, result)
    return result


def _write_json(path: str | Path, value: object) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
