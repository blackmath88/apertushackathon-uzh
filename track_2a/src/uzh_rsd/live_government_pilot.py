"""Offline-first capture, deterministic analysis and static evidence viewer."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from .government_scout import get_profile, normalize_url, scout

SCHEMA = "live_government_pilot/v1"
EXTRACTION_REVISION = "lis-main-content-v1"
METHOD = "deterministic-lexical-structural-v1"
PAIR_STATES = {"CANDIDATE", "UNKNOWN", "UNRESOLVED", "HUMAN_VERIFIED", "REJECTED"}
BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "th", "td"}
IGNORED_TAGS = {"script", "style", "nav", "footer", "header", "aside", "form", "button", "noscript"}
TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)


class MainContentParser(HTMLParser):
    """Extract ordered semantic blocks; offsets reference the exact extracted_text."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.main_depth = 0
        self.body_depth = 0
        self.ignored_depth = 0
        self.current_tag: str | None = None
        self.current_parts: list[str] = []
        self.blocks: list[tuple[str, str]] = []
        self.saw_main = False

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag == "main":
            self.main_depth += 1
            self.saw_main = True
        elif tag == "body":
            self.body_depth += 1
        if tag in IGNORED_TAGS:
            self.ignored_depth += 1
        if tag in BLOCK_TAGS and self._active() and not self.ignored_depth:
            self._flush()
            self.current_tag = tag

    def handle_endtag(self, tag: str) -> None:
        if tag == self.current_tag:
            self._flush()
        if tag in IGNORED_TAGS and self.ignored_depth:
            self.ignored_depth -= 1
        if tag == "main" and self.main_depth:
            self.main_depth -= 1
        elif tag == "body" and self.body_depth:
            self.body_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.current_tag and self._active() and not self.ignored_depth:
            self.current_parts.append(data)

    def close(self) -> None:
        super().close()
        self._flush()

    def _active(self) -> bool:
        return bool(self.main_depth or (not self.saw_main and self.body_depth))

    def _flush(self) -> None:
        if self.current_tag:
            text = " ".join("".join(self.current_parts).split())
            if text:
                kind = "heading" if self.current_tag.startswith("h") else (
                    "list_item" if self.current_tag == "li" else
                    "table_cell" if self.current_tag in {"th", "td"} else "paragraph"
                )
                self.blocks.append((kind, text))
        self.current_tag = None
        self.current_parts = []


def extract_content(html_text: str) -> dict[str, object]:
    parser = MainContentParser()
    parser.feed(html_text)
    parser.close()
    chunks: list[str] = []
    blocks: list[dict[str, object]] = []
    cursor = 0
    section = 0
    for order, (kind, text) in enumerate(parser.blocks):
        if chunks:
            chunks.append("\n")
            cursor += 1
        start = cursor
        chunks.append(text)
        cursor += len(text)
        if kind == "heading":
            section += 1
        blocks.append({
            "id": f"block-{order + 1:03d}", "order": order, "section_order": section,
            "kind": kind, "text": text, "start": start, "end": cursor,
        })
    extracted_text = "".join(chunks)
    return {
        "extraction_revision": EXTRACTION_REVISION,
        "offset_basis": "Unicode code-point offsets into extracted_text after whitespace normalization",
        "extracted_text": extracted_text,
        "sha256_extract": sha256(extracted_text.encode("utf-8")).hexdigest(),
        "blocks": blocks,
    }


def capture_html(*, html_bytes: bytes, source_url: str, canonical_url: str,
                 locale: str, profile: str, retrieved_at_utc: str,
                 rights_note: str, raw_dir: str | Path | None,
                 fixture: bool = False) -> dict[str, object]:
    selected = get_profile(profile)
    source = normalize_url(source_url, selected)
    canonical = normalize_url(canonical_url, selected)
    html_digest = sha256(html_bytes).hexdigest()
    if raw_dir is not None:
        raw_path = Path(raw_dir) / "sha256" / html_digest[:2] / f"{html_digest}.html"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if raw_path.exists() and raw_path.read_bytes() != html_bytes:
            raise RuntimeError("content-address collision")
        if not raw_path.exists():
            raw_path.write_bytes(html_bytes)
    html_text = html_bytes.decode("utf-8", "strict")
    extracted = extract_content(html_text)
    return {
        "schema": SCHEMA, "artifact_kind": "fixture_capture" if fixture else "live_capture",
        "profile": selected.id, "source_url": source, "canonical_url": canonical,
        "locale": locale, "retrieved_at_utc": retrieved_at_utc,
        "sha256_html": html_digest, **extracted,
        "rights_note": rights_note, "fixture": fixture,
        "content_address": f"sha256:{html_digest}",
    }


def _tokens(text: str) -> list[str]:
    return TOKEN.findall(text.casefold())


def analyze_pair(left: dict[str, object], right: dict[str, object], *,
                 pair_status: str, pairing_evidence: list[dict[str, str]],
                 reviewer: str | None) -> dict[str, object]:
    if pair_status not in PAIR_STATES:
        raise ValueError(f"invalid pair status: {pair_status}")
    left_counts = Counter(_tokens(str(left["extracted_text"])))
    right_counts = Counter(_tokens(str(right["extracted_text"])))
    shared = set(left_counts) & set(right_counts)
    union = set(left_counts) | set(right_counts)
    overlap = len(shared) / len(union) if union else 1.0
    left_kinds = Counter(block["kind"] for block in left["blocks"])
    right_kinds = Counter(block["kind"] for block in right["blocks"])
    structural_delta = {kind: left_kinds[kind] - right_kinds[kind]
                        for kind in sorted(set(left_kinds) | set(right_kinds))}
    observations = [
        {"kind": "OBSERVED_SOURCE_FACT", "field": "left_block_count", "value": len(left["blocks"])},
        {"kind": "OBSERVED_SOURCE_FACT", "field": "right_block_count", "value": len(right["blocks"])},
        {"kind": "OBSERVED_SOURCE_FACT", "field": "structural_count_delta", "value": structural_delta},
    ]
    candidates = [{
        "kind": "INFERRED_CANDIDATE", "status": "UNRESOLVED",
        "signal": "cross_language_lexical_overlap", "value": round(overlap, 6),
        "interpretation": "Diagnostic only: lexical overlap across languages does not establish equivalence or discrepancy.",
        "review_decision": None,
    }]
    return {
        "schema": SCHEMA, "artifact_kind": "pair_analysis", "method": METHOD,
        "method_class": "deterministic explicitly non-Apertus lexical/structural baseline",
        "apertus_calls": 0, "gold_labels": False, "spearman_claim": False,
        "pair_status": pair_status, "pairing_evidence": pairing_evidence, "reviewer": reviewer,
        "left": {key: left[key] for key in ("source_url", "canonical_url", "locale", "retrieved_at_utc", "sha256_html", "sha256_extract", "fixture")},
        "right": {key: right[key] for key in ("source_url", "canonical_url", "locale", "retrieved_at_utc", "sha256_html", "sha256_extract", "fixture")},
        "observations": observations, "candidates": candidates,
        "caveat": "No live gold labels; no correctness, legal conclusion, discrepancy or Spearman claim.",
    }


def public_capture(capture: dict[str, object], excerpt_chars: int = 180) -> dict[str, object]:
    """Create a bounded distributable record, never a full third-party text copy."""
    blocks = []
    for block in capture["blocks"][:4]:
        text = str(block["text"])
        blocks.append({key: block[key] for key in ("id", "order", "section_order", "kind", "start", "end")} |
                      {"minimal_excerpt": text[:excerpt_chars], "excerpt_truncated": len(text) > excerpt_chars})
    return {key: capture[key] for key in (
        "schema", "artifact_kind", "profile", "source_url", "canonical_url", "locale",
        "retrieved_at_utc", "sha256_html", "sha256_extract", "extraction_revision", "offset_basis",
        "rights_note", "fixture", "content_address",
    )} | {"blocks": blocks}


def render_viewer(manifest: dict[str, object]) -> str:
    pair = manifest["pair"]
    analysis = manifest["analysis"]
    policy = manifest["policy"]
    def side(page: dict[str, object], label: str) -> str:
        source = normalize_url(str(page["source_url"]), str(manifest["profile"]))
        blocks = "".join(
            f'<article class="block"><span>{escape(str(item["kind"]))} · {item["start"]}:{item["end"]}</span>'
            f'<p>{escape(str(item.get("minimal_excerpt", "")))}</p></article>' for item in page["blocks"]
        )
        return f'''<section class="side"><div class="lang">{escape(label)}</div>
<h2>{escape(str(page["locale"]).upper())}</h2><p class="hash">{escape(str(page["sha256_extract"]))}</p>
<p class="hash">Captured {escape(str(page["retrieved_at_utc"]))} · {escape(source)}</p>
<a class="source" href="{escape(source, quote=True)}" rel="noopener noreferrer">Open source URL ↗</a>{blocks}</section>'''
    inferred = analysis["candidates"][0]
    blocked = escape(str(policy["decision"]))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lost in Switzerland · Evidence viewer</title><style>
:root{{--ink:#17231f;--paper:#f5f1e8;--accent:#c83c28;--line:#c8c0b1;font-family:Inter,ui-sans-serif,system-ui,sans-serif}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink)}}main{{max-width:1180px;margin:auto;padding:48px 24px 80px}}header{{border-bottom:2px solid var(--ink);padding-bottom:28px}}.eyebrow,.lang{{font-size:12px;text-transform:uppercase;letter-spacing:.14em;font-weight:800;color:var(--accent)}}h1{{font-size:clamp(48px,8vw,96px);line-height:.88;letter-spacing:-.055em;margin:14px 0}}.notice{{background:#fff4d7;border-left:5px solid #c28a00;padding:16px;margin:24px 0}}.meta{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin:28px 0}}.meta div{{background:#fff;padding:16px}}.meta b{{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px}}.columns{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}.side{{background:#fff;border:1px solid var(--line);padding:24px;min-width:0}}h2{{font-size:38px;margin:6px 0}}.hash{{font:11px ui-monospace,monospace;overflow-wrap:anywhere;color:#665}}.source{{display:inline-block;color:var(--ink);font-weight:750;margin:10px 0 20px}}.block{{border-top:1px solid var(--line);padding:14px 0}}.block span{{font-size:11px;text-transform:uppercase;color:#766}}.analysis{{margin-top:22px;background:var(--ink);color:white;padding:28px}}.analysis strong{{color:#ffb4a7}}footer{{margin-top:28px;border-top:1px solid var(--line);padding-top:20px}}@media(max-width:760px){{.columns{{grid-template-columns:1fr}}}}
</style></head><body><main><header><div class="eyebrow">Bilingual evidence · {escape(str(manifest["profile"]))}</div><h1>Same information?<br>Show the evidence.</h1><p>Read-only local inspector. The authoritative source remains the external government page.</p></header>
<div class="notice"><strong>Policy limitation.</strong> {blocked} This demonstration uses clearly marked synthetic fixture content; it is not a live BFE finding.</div>
<section class="meta"><div><b>Pair status</b>{escape(str(analysis["pair_status"]))}</div><div><b>Method</b>{escape(str(analysis["method"]))}</div><div><b>Model calls</b>0 (non-Apertus)</div><div><b>Gold / score</b>None · no Spearman</div><div><b>Reviewer</b>{escape(str(analysis.get("reviewer") or "pending"))}</div></section>
<div class="columns">{side(pair["left"], "Left source")}{side(pair["right"], "Right source")}</div>
<section class="analysis"><div class="eyebrow">Observed vs inferred</div><p><strong>Observed:</strong> captures, URLs, locales, timestamps, hashes, block order and offsets.</p><p><strong>Inferred · {escape(str(inferred["status"]))}:</strong> {escape(str(inferred["interpretation"]))}</p><p><strong>Decision placeholder:</strong> Reviewer must accept, reject or leave unresolved. No discrepancy is asserted.</p></section>
<footer><p>Legal-language caveat: authority and legal effect vary by publisher and language. This viewer makes no universal claim that one language controls.</p></footer></main></body></html>'''


def build_demo(output_dir: str | Path, fixture_dir: str | Path, policy_path: str | Path) -> dict[str, object]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    fixture = Path(fixture_dir)
    timestamp = "2026-10-13T20:00:00Z"
    rights = "Synthetic project-authored fixture; not government source content."
    left = capture_html(html_bytes=(fixture / "bfe-de.html").read_bytes(),
                        source_url="https://www.bfe.admin.ch/de/fixture-dunstabzugshauben",
                        canonical_url="https://www.bfe.admin.ch/de/fixture-dunstabzugshauben",
                        locale="de-CH", profile="bfe-federal", retrieved_at_utc=timestamp,
                        rights_note=rights, raw_dir=destination / "raw", fixture=True)
    right = capture_html(html_bytes=(fixture / "bfe-fr.html").read_bytes(),
                         source_url="https://www.bfe.admin.ch/fr/fixture-hottes-domestiques",
                         canonical_url="https://www.bfe.admin.ch/fr/fixture-hottes-domestiques",
                         locale="fr-CH", profile="bfe-federal", retrieved_at_utc=timestamp,
                         rights_note=rights, raw_dir=destination / "raw", fixture=True)
    evidence = [{"type": "explicit_fixture_review", "provenance": "tests/fixtures/live_government_pilot/PAIRING.md"}]
    analysis = analyze_pair(left, right, pair_status="HUMAN_VERIFIED", pairing_evidence=evidence,
                            reviewer="fixture-author (synthetic equivalence only)")
    policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))
    manifest = {
        "schema": SCHEMA, "artifact_kind": "demonstration_manifest", "profile": "bfe-federal",
        "fixture": True, "policy": policy, "pair": {"left": public_capture(left), "right": public_capture(right)},
        "analysis": analysis, "generated_at_utc": timestamp,
        "limitations": ["No BFE content page was fetched because applicable terms require prior written permission for reproduction.",
                        "Synthetic fixture equivalence is a pipeline demonstration, not a real government-page conclusion."],
    }
    (destination / "demonstration-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (destination / "viewer.html").write_text(render_viewer(manifest), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="replay the lawful synthetic fixture and build viewer")
    demo.add_argument("--fixtures", required=True)
    demo.add_argument("--policy", required=True)
    demo.add_argument("--out", required=True)
    live = sub.add_parser("live", help="explicit opt-in bounded live discovery")
    live.add_argument("--policy", required=True)
    live.add_argument("--out", required=True)
    live.add_argument("--confirm-live", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "demo":
        manifest = build_demo(args.out, args.fixtures, args.policy)
        print(json.dumps({"manifest": str(Path(args.out) / "demonstration-manifest.json"),
                          "fixture": manifest["fixture"], "apertus_calls": 0}))
        return 0
    policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
    if not args.confirm_live:
        raise SystemExit("BLOCKED: live network action requires --confirm-live")
    if not policy.get("content_collection_permitted", False):
        blocked = {"schema": SCHEMA, "artifact_kind": "live_run_manifest", "profile": "bfe-federal",
                   "status": "POLICY_BLOCKED", "request_count": policy.get("request_count", 0),
                   "content_page_request_count": 0, "captured_pages": [], "pairs": [],
                   "limitation": policy["decision"], "apertus_calls": 0}
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(blocked, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(blocked))
        return 3
    result = scout("bfe-federal", out=args.out)
    print(json.dumps({"captured": len(result["captured"]), "pairs": len(result["pairs"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
