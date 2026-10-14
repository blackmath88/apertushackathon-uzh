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
import math
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

HOST = "www.stadt-zuerich.ch"
USER_AGENT = "LostInSwitzerlandResearch/0.2 (+https://github.com/blackmath88/apertushackathon-uzh)"
ASSET = re.compile(r"\.(?:jpg|jpeg|png|gif|webp|svg|ico|css|js|json|xml|zip|mp4|mp3|woff2?|ttf|pdf)$", re.I)
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
    if re.search(r"/(?:app|apps|appl|mk|login|auth)(?:/|$)", parts.path, re.I):
        raise ValueError("interactive/account surface excluded")
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
        self.language: str | None = None
        self.language_links: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "html":
            self.language = (a.get("lang") or "").lower() or None
        if (tag == "a" or tag.startswith("stzh-")) and a.get("href"):
            self.anchors.append(a["href"] or "")
        if tag == "a" and a.get("href") and a.get("hreflang"):
            self.language_links.setdefault(a["hreflang"].lower(), []).append(a["href"])
        if tag == "stzh-header" and a.get("languages"):
            try:
                entries = json.loads(a["languages"])
                if isinstance(entries, list):
                    for entry in entries:
                        if not isinstance(entry, dict):
                            continue
                        lang = entry.get("language") or entry.get("lang")
                        if not lang:
                            lang = {"Information in English": "en", "Deutsch": "de", "English": "en"}.get(entry.get("text") or entry.get("label"))
                        href = entry.get("href") or entry.get("value")
                        if isinstance(lang, str) and isinstance(href, str):
                            self.language_links.setdefault(lang.lower(), []).append(href)
            except (ValueError, TypeError):
                pass
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
    language: str | None = None
    language_links: dict[str, list[str]] | None = None


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # No redirects are followed implicitly; caller records HTTP 3xx as a failure.
        return None


def candidate_score(url: str) -> int:
    value = url.lower()
    score = 8 if SERVICE.search(value) else 0
    if "/other-languages/en.html" in value or "/en/" in value:
        score += 20
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


class RobotsPolicy:
    """Longest-match Allow/Disallow, wildcard and terminal $, per RFC 9309.

    Fail closed for unsupported percent-encoded/non-ASCII rule paths rather than
    pretending urllib.robotparser implements Google's wildcard syntax.
    """
    def __init__(self, text: str):
        groups = []
        agents, rules, delay = [], [], 0.0
        started = False
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, value = (x.strip() for x in line.split(":", 1))
            key = key.lower()
            if key == "user-agent":
                if started:
                    groups.append((agents, rules, delay))
                    agents, rules, delay, started = [], [], 0.0, False
                agents.append(value.lower())
            elif agents:
                started = True
                if key in ("allow", "disallow") and value:
                    rules.append((key == "allow", value))
                elif key == "crawl-delay":
                    delay = max(delay, float(value))
                elif key == "request-rate":
                    count, seconds = value.split("/")
                    delay = max(delay, float(seconds) / float(count))
        groups.append((agents, rules, delay))
        token = USER_AGENT.split("/", 1)[0].lower()
        specific = [g for g in groups if token in g[0]]
        selected = specific or [g for g in groups if "*" in g[0]]
        self.rules = [r for _, rr, _ in selected for r in rr]
        self.delay = max((d for _, _, d in selected), default=0.0)
        if not math.isfinite(self.delay) or self.delay < 0:
            raise ValueError("invalid robots rate")
        if any("%" in rule or not rule.isascii() for _, rule in self.rules):
            raise ValueError("unsupported encoded robots rule; refusing crawl")

    def can_fetch(self, _agent: str, url: str) -> bool:
        parts = urlsplit(url)
        target = parts.path + ("?" + parts.query if parts.query else "")
        # Encoded/non-ASCII targets cannot be evaluated by this conservative subset.
        if "%" in target or not target.isascii():
            return False
        matched = []
        for allow, rule in self.rules:
            terminal = rule.endswith("$")
            pattern = re.escape(rule[:-1] if terminal else rule).replace(r"\*", ".*")
            if re.match("^" + pattern + ("$" if terminal else ""), target):
                matched.append((len(rule.replace("*", "").rstrip("$")), allow))
        return max(matched, default=(0, True))[1]


def scout(seed: str, *, max_pages: int = 15, max_depth: int = 2,
          delay_seconds: float = 2.0, timeout: float = 12.0,
          out: str | Path | None = None, capture_dir: str | Path | None = None,
          additional_seeds: tuple[str, ...] = (), opener=None,
          clock=time.monotonic, sleeper=time.sleep) -> dict:
    """Opt-in network action; fails closed when robots.txt cannot be retrieved."""
    if (type(max_pages) is not int or type(max_depth) is not int or
            not 1 <= max_pages <= 20 or not 0 <= max_depth <= 2 or
            not math.isfinite(delay_seconds) or not 2.0 <= delay_seconds <= 60 or
            not math.isfinite(timeout) or not 0 < timeout <= 60):
        raise ValueError("pilot limits: 1..20 pages, depth 0..2, delay >=2s")
    seed = normalize_url(seed)
    seeds = [seed] + [normalize_url(s) for s in additional_seeds]
    if len(seeds) > max_pages:
        raise ValueError("seed count exceeds page budget")
    opener = opener or build_opener(NoRedirects())
    requests = []
    captures = []
    last_request = clock()
    robots_url = f"https://{HOST}/robots.txt"
    robots_time = datetime.now(timezone.utc).isoformat()
    try:
        with opener.open(Request(robots_url, headers={"User-Agent": USER_AGENT}), timeout=timeout) as response:
            if response.status != 200 or not response.headers.get("Content-Type", "").lower().startswith("text/plain"):
                raise ValueError("robots response is not plain text HTTP 200")
            robots_txt = response.read(128_001)
            if len(robots_txt) > 128_000:
                raise ValueError("robots file too large")
        robot = RobotsPolicy(robots_txt.decode("utf-8", "strict"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, UnicodeError) as exc:
        if out is not None:
            path = Path(out)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as stream:
                json.dump({"schema": "lost-in-switzerland/zurich-scout/v1", "seed": seed,
                           "status": "blocked", "captured": [], "captures": [], "pairs": [],
                           "failures": [{"url": robots_url, "reason": "robots_unavailable", "error_type": type(exc).__name__}],
                           "requests": [{"url": robots_url, "requested_at_utc": robots_time, "status": "failed"}],
                           "model_calls": 0}, stream, indent=2)
        raise RuntimeError("robots retrieval unavailable: refusing crawl") from exc
    delay_seconds = max(delay_seconds, robot.delay)
    if delay_seconds > 60:
        raise RuntimeError("robots delay exceeds pilot budget; refusing crawl")
    queue = [(s, 0, 100 - index) for index, s in enumerate(seeds)]
    requests.append({"url": robots_url, "requested_at_utc": robots_time, "status": "captured",
                     "http_status": 200, "bytes": len(robots_txt)})
    seen: set[str] = set()
    pages: list[Captured] = []
    failures: list[dict[str, str]] = []
    while queue and len(seen) < max_pages:
        queue.sort(key=lambda item: (-item[2], -candidate_score(item[0]), item[1], item[0]))
        url, depth, priority = queue.pop(0)
        if url in seen or depth > max_depth:
            continue
        seen.add(url)
        if not robot.can_fetch(USER_AGENT, url):
            failures.append({"url": url, "reason": "robots_disallow"})
            continue
        if last_request is not None:
            sleeper(max(0.0, delay_seconds - (clock() - last_request)))
        last_request = clock()
        event = {"url": url, "requested_at_utc": datetime.now(timezone.utc).isoformat()}
        requests.append(event)
        try:
            with opener.open(Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"}),
                             timeout=timeout) as response:
                if not response.headers.get("Content-Type", "").lower().startswith("text/html"):
                    event["status"] = "not_html"
                    failures.append({"url": url, "reason": "not_html"})
                    continue
                html = response.read(MAX_BODY_BYTES + 1)
                if len(html) > MAX_BODY_BYTES:
                    event["status"] = "too_large"
                    failures.append({"url": url, "reason": "too_large"})
                    continue
                # Conservative: redirects never followed, response URL still validated.
                actual = normalize_url(response.geturl())
                if actual != url:
                    event["status"] = "url_changed"
                    failures.append({"url": url, "reason": "url_changed"})
                    continue
            parsed, alt, canonical = parse_page(html, url)
            event.update(status="captured", http_status=response.status, bytes=len(html))
            pages.append(Captured(url=url, depth=depth, retrieved_at_utc=datetime.now(timezone.utc).isoformat(),
                                  sha256_html=sha256(html).hexdigest(), title=parsed.title.strip()[:180],
                                  alternates=alt, canonical=canonical, language=parsed.language,
                                  language_links=parsed.language_links))
            if capture_dir is not None:
                from .observatory_capture import save_capture
                captures.append(save_capture(Path(capture_dir), html, pages[-1]))
            if depth < max_depth:
                additions = set()
                alternates = {u for vv in alt.values() for u in vv}
                alternates.update(u for vv in parsed.language_links.values() for u in vv)
                for href in parsed.anchors + list(alternates):
                    try:
                        link = normalize_url(href, url)
                    except ValueError:
                        continue
                    if link not in seen:
                        additions.add(link)
                queue.extend((link, depth + 1, 50 if link in alternates else 0) for link in sorted(additions)
                             if link not in {item[0] for item in queue})
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            event["status"] = type(exc).__name__
            failure = {"url": url, "reason": type(exc).__name__}
            if isinstance(exc, HTTPError):
                event["http_status"] = exc.code
                failure["http_status"] = exc.code
                if exc.headers.get("Location"):
                    failure["redirect_location"] = exc.headers["Location"]
                # Stop rather than retry after server overload/rate-limit signals.
                if exc.code == 429 or exc.code >= 500:
                    failures.append(failure)
                    break
            failures.append(failure)
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
        "requests": requests,
        "captures": captures,
        "robots_sha256": sha256(robots_txt).hexdigest(),
        "robots_retrieved_at_utc": robots_time,
        "remaining_queue": len(queue),
        "disclaimer": "Discovery and pairing candidates only; no semantic findings or benchmark scores.",
    }
    if out is not None:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result

