"""Bounded, conservative public-page discovery for the Stadt Zürich semantic pilot.

Adapted in concept from blackmath88/accessibility-red-team/src/scout.
No LLM calls. This is NOT the SwissGov-RSD benchmark input pipeline.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser

HOST = "www.stadt-zuerich.ch"
USER_AGENT = "LostInSwitzerlandResearch/0.1 (bounded public-site pilot)"
ASSET = re.compile(r"\.(?:jpg|jpeg|png|gif|webp|svg|ico|css|js|zip|mp4|mp3|woff2?|ttf|pdf)$", re.I)
NOISE = re.compile(r"impressum|datenschutz|privacy|cookie|login|newsletter|facebook|instagram", re.I)
SERVICE = re.compile(r"dienstleistung|service|schalter|formular|antrag|gesuch|abfall|umzug|bewilligung|lebenslagen|neu-in-zuerich", re.I)
TRACKING = {"fbclid", "gclid", "pk_campaign", "pk_kwd"}
MAX_BODY_BYTES = 1_000_000


def normalize_url(value: str, base: str | None = None) -> str:
    """Strict host and scheme constraint; stable URL identity; no path guessing."""
    parts = urlsplit(urljoin(base or "", value))
    if parts.scheme != "https" or parts.hostname != HOST or parts.username or parts.password or parts.port:
        raise ValueError("out-of-scope URL (https and exact city host required)")
    if ASSET.search(parts.path):
        raise ValueError("non-HTML asset excluded")
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                             if not k.lower().startswith("utm_") and k.lower() not in TRACKING))
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(("https", HOST, path, query, ""))


class PageLinks(HTMLParser):
    """Extract explicit page links and hreflang relationships only."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[str] = []
        self.alternates: dict[str, list[str]] = {}
        self.canonicals: list[str] = []
        self.title = ""
        self._title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.anchors.append(a["href"] or "")
        if tag == "link" and a.get("href"):
            rel = (a.get("rel") or "").lower().split()
            if "alternate" in rel and a.get("hreflang"):
                self.alternates.setdefault((a.get("hreflang") or "").lower(), []).append(a["href"] or "")
            if "canonical" in rel:
                self.canonicals.append(a["href"] or "")
        if tag == "title":
            self._title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._title = False

    def handle_data(self, data: str) -> None:
        if self._title:
            self.title += data


@dataclass(frozen=True)
class Captured:
    url: str
    retrieved_at_utc: str
    sha256_html: str
    title: str
    depth: int
    alternates: dict[str, list[str]]
    canonical: str | None
    extraction_version: str = "lis-html-links-v1"


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # No redirects are followed implicitly; caller records HTTP 3xx as a failure.
        return None


def candidate_score(url: str) -> int:
    value = url.lower()
    score = 8 if SERVICE.search(value) else 0
    if NOISE.search(value):
        score -= 8
    return score - max(0, len(urlsplit(url).path.split("/")) - 4)


def parse_page(html: bytes, url: str) -> tuple[PageLinks, dict[str, list[str]], str | None]:
    parser = PageLinks()
    parser.feed(html.decode("utf-8", errors="replace"))
    normalized: dict[str, list[str]] = {}
    for lang, links in parser.alternates.items():
        for link in links:
            try:
                normalized.setdefault(lang, []).append(normalize_url(link, url))
            except ValueError:
                continue
    canonical = None
    for link in parser.canonicals:
        try:
            canonical = normalize_url(link, url)
            break
        except ValueError:
            continue
    return parser, normalized, canonical


def potential_pairs(pages: list[Captured]) -> list[dict[str, str]]:
    """Only explicit reciprocal hreflang DE/EN pairs; never infer from URL slugs."""
    lookup = {p.url: p for p in pages}
    pairs: dict[tuple[str, str], dict[str, str]] = {}
    for p in pages:
        for lang, others in p.alternates.items():
            if not lang.startswith(("de", "en")):
                continue
            for other_url in others:
                other = lookup.get(other_url)
                if other is None or other.url == p.url:
                    continue
                back = any(p.url in destinations for destinations in other.alternates.values())
                if not back:
                    continue
                if lang.startswith("de") and any(k.startswith("en") and p.url in vv for k, vv in other.alternates.items()):
                    de, en = other.url, p.url
                elif lang.startswith("en") and any(k.startswith("de") and p.url in vv for k, vv in other.alternates.items()):
                    de, en = p.url, other.url
                else:
                    continue
                key = (de, en)
                pairs[key] = {"de": de, "en": en, "pairing": "reciprocal_hreflang", "review": "candidate"}
    return [pairs[key] for key in sorted(pairs)]


def scout(seed: str, *, max_pages: int = 15, max_depth: int = 2,
          delay_seconds: float = 2.0, timeout: float = 12.0,
          out: str | Path | None = None) -> dict:
    """Opt-in network action; fails closed when robots.txt cannot be retrieved."""
    if not 1 <= max_pages <= 20 or not 0 <= max_depth <= 2 or delay_seconds < 2.0:
        raise ValueError("pilot limits: 1..20 pages, depth 0..2, delay >=2s")
    seed = normalize_url(seed)
    opener = build_opener(NoRedirects())
    robots_url = f"https://{HOST}/robots.txt"
    try:
        with opener.open(Request(robots_url, headers={"User-Agent": USER_AGENT}), timeout=timeout) as response:
            robots_txt = response.read(128_001)
            if len(robots_txt) > 128_000:
                raise ValueError("robots file too large")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("robots retrieval unavailable: refusing crawl") from exc
    robot = RobotFileParser()
    robot.parse(robots_txt.decode("utf-8", "replace").splitlines())
    queue = [(seed, 0)]
    seen: set[str] = set()
    pages: list[Captured] = []
    failures: list[dict[str, str]] = []
    last_request: float | None = None
    while queue and len(seen) < max_pages:
        queue.sort(key=lambda item: (-candidate_score(item[0]), item[1], item[0]))
        url, depth = queue.pop(0)
        if url in seen or depth > max_depth:
            continue
        seen.add(url)
        if not robot.can_fetch(USER_AGENT, url):
            failures.append({"url": url, "reason": "robots_disallow"})
            continue
        if last_request is not None:
            time.sleep(max(0.0, delay_seconds - (time.monotonic() - last_request)))
        last_request = time.monotonic()
        try:
            with opener.open(Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"}),
                             timeout=timeout) as response:
                if not response.headers.get("Content-Type", "").lower().startswith("text/html"):
                    failures.append({"url": url, "reason": "not_html"})
                    continue
                html = response.read(MAX_BODY_BYTES + 1)
                if len(html) > MAX_BODY_BYTES:
                    failures.append({"url": url, "reason": "too_large"})
                    continue
                # Conservative: redirects never followed, response URL still validated.
                actual = normalize_url(response.geturl())
                if actual != url:
                    failures.append({"url": url, "reason": "url_changed"})
                    continue
            parsed, alt, canonical = parse_page(html, url)
            pages.append(Captured(url=url, depth=depth, retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                                  sha256_html=sha256(html).hexdigest(), title=parsed.title.strip()[:180],
                                  alternates=alt, canonical=canonical))
            if depth < max_depth:
                additions = set()
                for href in parsed.anchors:
                    try:
                        link = normalize_url(href, url)
                    except ValueError:
                        continue
                    if link not in seen:
                        additions.add(link)
                queue.extend((link, depth + 1) for link in sorted(additions)
                             if link not in {item[0] for item in queue})
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            failures.append({"url": url, "reason": type(exc).__name__})
    result = {
        "schema": "lost-in-switzerland/zurich-scout/v1",
        "seed": seed,
        "retrieval_policy": {"host": HOST, "max_pages": max_pages, "max_depth": max_depth,
                             "delay_seconds": delay_seconds, "robots": "enforced"},
        "captured": [asdict(p) for p in pages],
        "pairs": potential_pairs(pages),
        "unpaired_count": len(pages) - len({u for p in potential_pairs(pages) for u in (p["de"], p["en"])}),
        "failures": failures,
        "model_calls": 0,
        "disclaimer": "Discovery and pairing candidates only; no semantic findings or benchmark scores.",
    }
    if out is not None:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result
