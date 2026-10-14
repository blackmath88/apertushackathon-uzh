"""Selected page families -> reproducible evidence captures (issue #36). Zero model calls.

Requests go only through the #34 guarded transport for reviewed profiles. Raw bodies are stored
content-addressed; each retrieval keeps its own identity even when bodies are byte-identical.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import re
from urllib.parse import urlsplit

from . import discovery, federal_desk as desk
from . import government_scout as gs
from .discovery_transport import DiscoveryStore, GuardedTransport, LegacyFetcherTransport, Purpose, RequestLedger, RESPONSE_CEILING
from .live_government_pilot import (
    BLOCK_TAGS, EXTRACTION_REVISION, IGNORED_TAGS, MainContentParser, capture_html,
)

SCHEMA = "lost-in-switzerland/capture-evidence/v1"
WORD = re.compile(r"\w+", re.UNICODE)
KEPT_HEADERS = ("content-type", "content-language", "last-modified", "etag", "content-length")


class _AllText(MainContentParser):
    """Same region rules as the extractor, but records every visible text node."""
    def __init__(self) -> None:
        super().__init__()
        self.all_text: list[str] = []

    def handle_data(self, data: str) -> None:
        if self._active() and not self.ignored_depth:
            self.all_text.append(data)
        super().handle_data(data)


def completeness(html_text: str, extracted_text: str, blocks: list[dict[str, object]]) -> dict[str, object]:
    """Words visible in the content region but absent from the extraction are reported, never dropped silently."""
    parser = _AllText()
    parser.feed(html_text); parser.close()
    raw = Counter(w.casefold() for chunk in parser.all_text for w in WORD.findall(chunk))
    got = Counter(w.casefold() for w in WORD.findall(extracted_text))
    missing = {w: n - got[w] for w, n in raw.items() if n > got[w]}
    return {"status": "complete" if not missing else "partial", "block_count": len(blocks),
            "unmatched_words": dict(sorted(missing.items())[:40]), "unmatched_total": sum(missing.values()),
            "truncated": False, "check": "visible content-region words vs extracted words (multiset)"}


def _blocked(blockers, **extra):
    return {"schema": SCHEMA, "status": "blocked", "blockers": blockers, "requests": 0, "bundle": None, **extra}


def eligibility(snapshot, family_id, pairing, fixture):
    blockers = []
    profile = discovery.profile_for_site(snapshot["site_id"])
    fam = next((f for f in snapshot["families"] if f["family_id"] == family_id), None)
    if not profile: blockers.append("unsupported_site")
    if not fam: return profile, None, None, None, blockers + ["unknown_family"]
    if fam["status"] == "contradictory": blockers.append("contradictory_family")
    sides = {}
    for key in ("left", "right"):
        lang = (pairing or {}).get(key + "_language")
        members = fam["languages"].get(lang, []) if lang in discovery.LANGUAGES else []
        if len(members) != 1: blockers.append(f"{key}_language_not_single_observed:{lang}")
        else:
            url = members[0]["url"]
            if profile and urlsplit(url).hostname not in profile.hosts: blockers.append(f"unsupported_host:{url}")
            sides[key] = {"url": url, "language": lang}
    if (pairing or {}).get("left_language") == (pairing or {}).get("right_language"): blockers.append("same_language")
    p = pairing or {}
    if p.get("certified") is not True or not all(isinstance(p.get(k), str) and p[k].strip() for k in ("reviewer", "pairing_rationale", "rights_basis")):
        blockers.append("uncertified_pair")
    if not fixture and p.get("content_use_permitted") is not True: blockers.append("content_use_not_permitted")
    return profile, fam, sides.get("left"), sides.get("right"), blockers


def capture_family(snapshot, family_id, pairing, *, fetcher=None, raw_dir, fixture=False, delay_seconds=2.0,
                   resolver=None, timeout=12.0, clock=lambda: datetime.now(timezone.utc)):
    profile, fam, left, right, blockers = eligibility(snapshot, family_id, pairing, fixture)
    base = {"family_id": family_id, "snapshot_id": snapshot["id"], "site_id": snapshot["site_id"]}
    if blockers:
        return _blocked(blockers, **base)
    store = DiscoveryStore()
    ledger = RequestLedger(store, "capture", discovery.Budgets(max_page_attempts=8, max_total_attempts=8), delay_seconds=delay_seconds)
    scope = gs._scope_check(profile)
    transport = (LegacyFetcherTransport(ledger, fetcher, profile, scope, timeout=timeout) if fetcher
                 else GuardedTransport(ledger, scope, timeout=timeout, **({"resolver": resolver} if resolver else {})))
    retrievals, bodies, failures = {}, {}, []
    for key, side in (("left", left), ("right", right)):
        at = clock().isoformat()
        try:
            resp = transport.fetch(side["url"], Purpose.HTML)
            ctype = resp.headers.get("Content-Type", "")
            if resp.status != 200 or not ctype.lower().startswith("text/html"):
                raise RuntimeError(f"HTTP {resp.status} {ctype}")
        except Exception as exc:
            failures.append(f"fetch_failed:{key}:{type(exc).__name__}")
            retrievals[key] = {"requested_url": side["url"], "retrieved_at_utc": at, "state": "failed", "error": type(exc).__name__}
            continue
        raw_hash = sha256(resp.body).hexdigest()
        retrievals[key] = {
            "retrieval_id": sha256(f"{side['url']}\n{resp.url}\n{at}\n{raw_hash}".encode()).hexdigest()[:24],
            "requested_url": side["url"], "final_url": resp.url, "redirects": list(resp.redirects),
            "status": resp.status, "headers": {k: v for k, v in ((h.lower(), resp.headers[h]) for h in resp.headers) if k in KEPT_HEADERS},
            "retrieved_at_utc": at, "bytes": len(resp.body), "sha256_raw": raw_hash, "content_address": f"sha256:{raw_hash}",
            "state": "retrieved", "language": side["language"],
            "permission": {"fixture": fixture, "content_use_permitted": pairing.get("content_use_permitted") is True,
                           "rights_basis": pairing["rights_basis"], "reviewer": pairing["reviewer"]}}
        bodies[key] = resp.body
    evidence = {"schema": SCHEMA, **base, "retrievals": retrievals, "accounting": ledger.snapshot(),
                "extraction": {}, "family": {"status": fam["status"], "edges": fam["edges"],
                                             "language_availability": fam["language_availability"]},
                "model_calls": 0}
    if failures:
        return {**base, "schema": SCHEMA, "status": "failed", "blockers": failures, "requests": ledger.total, "bundle": None, "evidence": evidence}
    extraction_blockers, partial = [], []
    for key in ("left", "right"):
        r = retrievals[key]
        info = {"revision": EXTRACTION_REVISION, "config": {"block_tags": sorted(BLOCK_TAGS), "ignored_tags": sorted(IGNORED_TAGS)}}
        try:
            cap = capture_html(html_bytes=bodies[key], source_url=r["requested_url"], canonical_url=r["final_url"],
                               locale=r["language"], profile=profile.id, retrieved_at_utc=r["retrieved_at_utc"],
                               rights_note=pairing["rights_basis"], raw_dir=raw_dir, fixture=fixture)
            if not cap["extracted_text"]: raise ValueError("empty extraction")
            info.update(status="ok", offset_basis=cap["offset_basis"], sha256_extract=cap["sha256_extract"],
                        completeness=completeness(bodies[key].decode("utf-8"), cap["extracted_text"], cap["blocks"]))
            if info["completeness"]["status"] != "complete": partial.append(key)
        except Exception as exc:
            info.update(status="failed", error=type(exc).__name__)
            extraction_blockers.append(f"extraction_failed:{key}")
        evidence["extraction"][key] = info
    evidence["omission_confirmation"] = {"allowed": not extraction_blockers and not partial,
        "blockers": extraction_blockers + [f"extraction_partial:{k}" for k in partial]}
    if extraction_blockers:
        return {**base, "schema": SCHEMA, "status": "extraction_failed", "blockers": extraction_blockers, "requests": ledger.total,
                "bundle": None, "evidence": evidence}
    meta = {"rights_basis": pairing["rights_basis"], "pairing_rationale": pairing["pairing_rationale"], "reviewer": pairing["reviewer"],
            "captured_at_utc": max(r["retrieved_at_utc"] for r in retrievals.values()),
            "content_use_permitted": pairing.get("content_use_permitted") is True,
            "left": {"url": left["url"], "language": left["language"]}, "right": {"url": right["url"], "language": right["language"]}}
    bundle = desk.prepare(bodies["left"], bodies["right"], meta, fixture)
    evidence["links"] = {k: {"live_original": retrievals[k]["requested_url"], "live_note": "current page; may differ from the capture",
                            "captured_evidence": retrievals[k]["content_address"], "retrieved_at_utc": retrievals[k]["retrieved_at_utc"]}
                         for k in ("left", "right")}
    evidence["pairing"] = {"status": "CANDIDATE", "certified_by": pairing["reviewer"], "rationale": pairing["pairing_rationale"],
                           "uncertainty": [f"family_status:{fam['status']}", "pairing_is_a_reviewer_assertion_not_verified_equivalence"]}
    bundle["capture_evidence"] = evidence
    desk.seal(bundle); desk.validate(bundle)
    return {**base, "schema": SCHEMA, "status": "captured", "blockers": [], "requests": ledger.total, "bundle": bundle, "evidence": evidence}
