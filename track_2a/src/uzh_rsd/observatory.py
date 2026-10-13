"""Website-to-evidence pilot commands, separate from judge entrypoints.

No benchmark loader/evaluator is invoked. No scheduled WATCH is implemented.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from .observatory_capture import digest, save_capture, verify_document, write_new
from .zurich_pilot import Captured, normalize_url, scout


def now():
    return datetime.now(timezone.utc).isoformat()


def load_documents(root):
    root = Path(root)
    manifest = json.loads((root / "scout.json").read_text())
    if manifest.get("schema") != "lost-in-switzerland/zurich-scout/v1":
        raise ValueError("unsupported Scout manifest")
    documents = {}
    for ref in manifest["captures"]:
        capture_id = ref["capture_id"]
        if not re.fullmatch("[0-9a-f]{64}", capture_id):
            raise ValueError("invalid capture identity")
        doc = verify_document(json.loads((root / "documents" / (capture_id + ".json")).read_text()), root)
        if doc["url"] != ref["url"] or doc["record_digest"] != ref["record_digest"]:
            raise ValueError("capture manifest mismatch")
        normalize_url(doc["url"])
        if doc["url"] in documents:
            raise ValueError("multiple captures of same URL require explicit selection")
        documents[doc["url"]] = doc
    return manifest, documents


def accepted_pairs(documents, reviews):
    pairs = []
    seen = set()
    for review in reviews:
        if review.get("status") != "accepted":
            continue
        if review.get("pairing") not in {"reciprocal_hreflang", "reviewed_relationship"}:
            raise ValueError("pair needs explicit relationship evidence")
        for key in ("reviewer", "reviewer_type", "reviewed_at_utc", "rationale", "evidence_urls"):
            if not review.get(key):
                raise ValueError("incomplete pairing review")
        if review["reviewer_type"] not in {"human", "assistant"}:
            raise ValueError("invalid reviewer type")
        stamp = datetime.fromisoformat(review["reviewed_at_utc"])
        if stamp.tzinfo is None:
            raise ValueError("review timestamp needs timezone")
        de = documents[normalize_url(review["de"])]
        en = documents[normalize_url(review["en"])]
        if not (de.get("language") or "").startswith("de") or not (en.get("language") or "").startswith("en"):
            raise ValueError("pair language metadata does not match DE/EN")
        if de["status"] != "ok" or en["status"] != "ok":
            raise ValueError("pair requires usable extracted content")
        if review.get("de_record_digest") != de["record_digest"] or review.get("en_record_digest") != en["record_digest"]:
            raise ValueError("pair review is stale or unpinned")
        if not {de["url"], en["url"]}.issubset(set(review["evidence_urls"])):
            raise ValueError("pair review must cite both original sources")
        pair_id = digest([de["url"], en["url"]])
        if pair_id in seen:
            raise ValueError("duplicate pair review")
        seen.add(pair_id)
        pairs.append({"pair_id": pair_id, "revision": digest([de["record_digest"], en["record_digest"]]),
                      "de": de, "en": en, "pairing_review": review,
                      "analysis": {"status": "not_run", "candidates": [], "confidence": None}})
    return pairs


def make_bundle(root, reviews):
    manifest, documents = load_documents(root)
    pairs = accepted_pairs(documents, reviews)
    paired = {p[lang]["url"] for p in pairs for lang in ("de", "en")}
    bundle = {"schema": "lost-in-switzerland/evidence-bundle/v1", "source_kind": "live_city_pilot",
              "generated_at_utc": now(), "scout_digest": digest(manifest), "pairs": pairs,
              "unpaired": [doc for url, doc in documents.items() if url not in paired],
              "discovery": {"captured": len(documents), "pair_candidates": manifest["pairs"],
                            "failures": manifest["failures"], "policy": manifest["retrieval_policy"]},
              "watch": "not_implemented", "model_calls": 0,
              "publication": "private_personal_use_only"}
    seal(bundle)
    return bundle


def seal(bundle):
    bundle["bundle_digest"] = digest({k: v for k, v in bundle.items() if k != "bundle_digest"})


def check_bundle(bundle):
    if bundle.get("schema") != "lost-in-switzerland/evidence-bundle/v1" or bundle.get("source_kind") != "live_city_pilot":
        raise ValueError("not a pilot bundle")
    if digest({k: v for k, v in bundle.items() if k != "bundle_digest"}) != bundle.get("bundle_digest"):
        raise ValueError("bundle integrity mismatch")
    for p in bundle["pairs"]:
        for lang in ("de", "en"):
            verify_document(p[lang])
            normalize_url(p[lang]["url"])
        expected = accepted_pairs({p["de"]["url"]: p["de"], p["en"]["url"]: p["en"]}, [p["pairing_review"]])[0]
        if p["pair_id"] != expected["pair_id"] or p["revision"] != expected["revision"]:
            raise ValueError("pair identity mismatch")
    for doc in bundle["unpaired"]:
        verify_document(doc)
        normalize_url(doc["url"])
    return bundle


def localize(doc, excerpt):
    from .methods import locate
    from .tokens import tokenize
    tokens = tokenize(doc["text"])
    spans, mode = locate(tokens.tokens, excerpt)
    locations = []
    for span in spans:
        start, end = tokens.offsets[span.start][0], tokens.offsets[span.end - 1][1]
        locations.append({"start": start, "end": end,
                          "block_ids": [b["id"] for b in doc["blocks"] if b["start"] < end and b["end"] > start]})
    return {"status": "absent_side_claim" if not excerpt else "ambiguous" if len(spans) > 1 else mode,
            "locations": locations}


def method_provenance():
    from .prompts import B2_PROMPT_VERSION
    here = Path(__file__).parent
    return {"method": "b2", "prompt_version": B2_PROMPT_VERSION, "adapter_version": "lis-b2-evidence-v1",
            "tokenization": "str.split/character-offsets-v1", "projection_excerpt_limit": 40,
            "source_hashes": {name: sha256((here / name).read_bytes()).hexdigest() for name in
                              ("prompts.py", "methods.py", "tokens.py", "observatory.py")},
            "confidence": None, "production_validation": "not_established"}


def analyze_pair(pair, backend, runtime):
    """Single attempt, exact existing B2 input, preserved raw response.

    Model severity is not probability/confidence. Parser projection is retained
    as diagnostics only; the viewer consumes explicitly located evidence.
    """
    from .data_adapter import InferenceInput
    from .methods import parse_b2, load_json_object
    from .prompts import render_b2
    from .tokens import tokenize
    item = InferenceInput(id="zurich_de_" + str(int(pair["pair_id"][:12], 16)), language="de",
                          text_a=tokenize(pair["en"]["text"]), text_b=tokenize(pair["de"]["text"]),
                          page_en=pair["en"]["url"], page_other=pair["de"]["url"])
    provenance = {**method_provenance(), "runtime": runtime, "backend": backend.describe(),
                  "max_new_tokens": 1024, "max_attempts": 1}
    if len(item.text_a) + len(item.text_b) > 2500:
        return {"status": "unresolved", "reason": "input_budget_exceeded_no_truncation",
                "candidates": [], "model_calls": 0, "provenance": provenance}
    prompt = render_b2(item)
    generated = backend.generate(prompt, 1024)
    parsed = parse_b2(item, generated.text)
    data, mode = load_json_object(generated.text) if generated.text is not None else (None, "call_failed")
    candidates = []
    if parsed.status == "ok":
        for index, entry in enumerate(data["differences"]):
            issues = []
            if not isinstance(entry, dict):
                entry = {}
                issues.append("invalid_item")
            a, b = entry.get("a"), entry.get("b")
            kind, severity = entry.get("kind"), entry.get("severity")
            if not isinstance(a, str) or not isinstance(b, str):
                issues.append("invalid_excerpt_type")
            if kind not in {"CHANGE", "ADDITION", "OMISSION"}:
                issues.append("unknown_kind")
            if isinstance(severity, bool) or not isinstance(severity, (int, float)) or not math.isfinite(severity) or not 1 <= severity <= 5:
                issues.append("invalid_severity")
            loc_en = localize(pair["en"], a) if isinstance(a, str) else {"status": "invalid", "locations": []}
            loc_de = localize(pair["de"], b) if isinstance(b, str) else {"status": "invalid", "locations": []}
            if a == b == "":
                issues.append("no_source_evidence")
            if kind == "CHANGE" and (not a or not b):
                issues.append("relation_excerpt_mismatch")
            if kind == "OMISSION" and (not a or b):
                issues.append("relation_excerpt_mismatch")
            if kind == "ADDITION" and (a or not b):
                issues.append("relation_excerpt_mismatch")
            for loc in (loc_en, loc_de):
                if loc["status"] not in {"exact", "absent_side_claim"}:
                    issues.append("source_" + loc["status"])
            candidate = {"candidate_id": digest([pair["revision"], provenance, index, sha256((generated.text or "").encode()).hexdigest()]),
                         "kind": kind if isinstance(kind, str) else "UNKNOWN", "severity": severity if "invalid_severity" not in issues else None,
                         "excerpt_en": a if isinstance(a, str) else "", "excerpt_de": b if isinstance(b, str) else "",
                         "en": loc_en, "de": loc_de, "validation": "needs_review" if issues else "evidence_located",
                         "issues": sorted(set(issues)), "review_state": "unresolved" if issues else "candidate", "confidence": None}
            candidates.append(candidate)
    return {"status": parsed.status, "finish_reason": generated.finish_reason, "raw": generated.as_dict(),
            "raw_sha256": sha256((generated.text or "").encode()).hexdigest(), "prompt": prompt,
            "prompt_sha256": sha256(prompt.encode()).hexdigest(), "provenance": provenance,
            "diagnostics": parsed.diagnostics, "candidates": candidates, "model_calls": 1,
            "completed_at_utc": now(), "no_difference_claim_is_not_equivalence": True}


def review_event(bundle, pair_id, candidate_id, state, reviewer, rationale):
    check_bundle(bundle)
    if state not in {"human_confirmed", "rejected", "unresolved"} or not reviewer.strip() or not rationale.strip():
        raise ValueError("review requires legal state, reviewer and rationale")
    pair = next(p for p in bundle["pairs"] if p["pair_id"] == pair_id)
    candidate = next(c for c in pair["analysis"]["candidates"] if c["candidate_id"] == candidate_id)
    if state == "human_confirmed" and (candidate["validation"] != "evidence_located" or
                                       pair["analysis"].get("finish_reason") == "length"):
        raise ValueError("unresolved/truncated evidence cannot be confirmed")
    event = {"schema": "lost-in-switzerland/review-event/v1", "bundle_digest": bundle["bundle_digest"],
             "pair_id": pair_id, "pair_revision": pair["revision"], "candidate_id": candidate_id,
             "state": state, "reviewer": reviewer, "rationale": rationale, "reviewed_at_utc": now(),
             "identity_assurance": "operator_asserted_not_authenticated"}
    event["event_digest"] = digest(event)
    return event


def replay(bundle):
    """Re-derive candidate localisation from saved raw B2 output, zero calls."""
    from .backends import Generation
    check_bundle(bundle)
    for pair in bundle["pairs"]:
        analysis = pair["analysis"]
        if analysis["status"] == "not_run":
            continue
        for name, expected in analysis["provenance"]["source_hashes"].items():
            if name not in {"prompts.py", "methods.py", "tokens.py", "observatory.py"}:
                raise ValueError("unknown method source")
            if sha256((Path(__file__).parent / name).read_bytes()).hexdigest() != expected:
                raise ValueError("method revision changed; replay not comparable")
        class SavedBackend:
            def describe(self): return analysis["provenance"]["backend"]
            def generate(self, _prompt, _cap): return Generation(**analysis["raw"])
        repeated = analyze_pair(pair, SavedBackend(), analysis["provenance"]["runtime"])
        keys = ("status", "reason", "candidates", "diagnostics", "prompt_sha256", "raw_sha256", "provenance", "model_calls", "finish_reason")
        if any(repeated.get(key) != analysis.get(key) for key in keys):
            raise ValueError("saved analysis replay mismatch")
    return {"replayed_pairs": len(bundle["pairs"]), "new_model_calls": 0, "new_website_requests": 0}


def reextract(root, out):
    """New extraction revision over original dated bytes; never a new crawl."""
    root, out = Path(root), Path(out)
    manifest = json.loads((root / "scout.json").read_text())
    if manifest.get("schema") != "lost-in-switzerland/zurich-scout/v1":
        raise ValueError("unsupported Scout manifest")
    out.mkdir(parents=True, exist_ok=False)
    captures = []
    for page in manifest["captured"]:
        normalize_url(page["url"])
        if not re.fullmatch("[0-9a-f]{64}", page["sha256_html"]):
            raise ValueError("invalid source hash")
        original = root / "html" / (page["sha256_html"] + ".html")
        raw = original.read_bytes()
        if sha256(raw).hexdigest() != page["sha256_html"]:
            raise ValueError("original HTML digest mismatch")
        captures.append(save_capture(out, raw, Captured(**page)))
    revised = {**manifest, "captures": captures, "source_manifest_digest": digest(manifest),
               "operation": "offline_reextraction", "reextracted_at_utc": now(),
               "new_website_requests": 0, "model_calls": 0}
    write_new(out / "scout.json", revised)
    return revised


def import_reviews(bundle, drafts):
    check_bundle(bundle)
    if drafts.get("schema") != "lost-in-switzerland/review-drafts/v1" or drafts.get("bundle_digest") != bundle["bundle_digest"]:
        raise ValueError("review drafts target a different bundle")
    events = []
    for draft in drafts["drafts"]:
        pair = next(p for p in bundle["pairs"] if p["pair_id"] == draft["pair_id"])
        if pair["revision"] != draft["pair_revision"]:
            raise ValueError("stale review revision")
        events.append(review_event(bundle, draft["pair_id"], draft["candidate_id"],
                                   draft["state"], draft["reviewer"], draft["rationale"]))
    return {"schema": "lost-in-switzerland/review-events/v1", "bundle_digest": bundle["bundle_digest"],
            "events": events, "automatic_publication": False}


def check_review_events(bundle, events):
    check_bundle(bundle)
    if events.get("schema") != "lost-in-switzerland/review-events/v1" or events.get("bundle_digest") != bundle["bundle_digest"]:
        raise ValueError("review events target a different bundle")
    for event in events["events"]:
        if digest({k: v for k, v in event.items() if k != "event_digest"}) != event.get("event_digest"):
            raise ValueError("review event integrity mismatch")
        if event.get("bundle_digest") != bundle["bundle_digest"]:
            raise ValueError("review targets a different bundle")
        pair = next(p for p in bundle["pairs"] if p["pair_id"] == event["pair_id"])
        if pair["revision"] != event["pair_revision"]:
            raise ValueError("review targets a different capture revision")
        # Validate legal state and evidence gate; do not change the saved event.
        review_event(bundle, event["pair_id"], event["candidate_id"], event["state"], event["reviewer"], event["rationale"])
    return events["events"]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("capture")
    s.add_argument("--seed", action="append", required=True)
    s.add_argument("--out", type=Path, required=True)
    s.add_argument("--max-pages", type=int, default=15)
    s.add_argument("--confirm-live", action="store_true")
    s.add_argument("--personal-use-only", action="store_true")
    s = sub.add_parser("reextract")
    s.add_argument("--run", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("pair-template")
    s.add_argument("--run", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("bundle")
    s.add_argument("--run", type=Path, required=True)
    s.add_argument("--reviews", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("analyze")
    s.add_argument("--bundle", type=Path, required=True)
    s.add_argument("--runtime", type=Path, required=True, help="model digest and runtime revision JSON")
    s.add_argument("--endpoint", default="http://127.0.0.1:11436/v1")
    s.add_argument("--model", required=True)
    s.add_argument("--confirm-local-inference", action="store_true")
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("view")
    s.add_argument("--bundle", type=Path, required=True)
    s.add_argument("--reviews", type=Path, help="validated review-events JSON, optional")
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("verify")
    s.add_argument("--bundle", type=Path, required=True)
    s = sub.add_parser("replay")
    s.add_argument("--bundle", type=Path, required=True)
    s = sub.add_parser("review-import")
    s.add_argument("--bundle", type=Path, required=True)
    s.add_argument("--drafts", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("review")
    s.add_argument("--bundle", type=Path, required=True)
    s.add_argument("--pair", required=True)
    s.add_argument("--candidate", required=True)
    s.add_argument("--state", choices=["human_confirmed", "rejected", "unresolved"], required=True)
    s.add_argument("--reviewer", required=True)
    s.add_argument("--rationale", required=True)
    s.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        if getattr(args, "out", None) and args.out.exists():
            raise ValueError("output already exists; use a fresh path")
        if args.command == "capture":
            if not args.confirm_live or not args.personal_use_only:
                print("BLOCKED: capture needs --confirm-live --personal-use-only; zero requests")
                return 3
            # Failed runs retain their evidence and must not be reused as output.
            args.out.mkdir(parents=True, exist_ok=False)
            r = scout(args.seed[0], additional_seeds=tuple(args.seed[1:]), max_pages=args.max_pages,
                      capture_dir=args.out, out=args.out / "scout.json")
            print(json.dumps({"captured": len(r["captures"]), "pairs": len(r["pairs"]), "failures": len(r["failures"])}))
        elif args.command == "reextract":
            revised = reextract(args.run, args.out)
            print(json.dumps({"captures": len(revised["captures"]), "new_website_requests": 0}))
        elif args.command == "pair-template":
            manifest, docs = load_documents(args.run)
            template = [{**pair, "status": "pending", "reviewer": "", "reviewer_type": "human",
                         "reviewed_at_utc": "", "rationale": "", "evidence_urls": [pair["de"], pair["en"]],
                         "de_record_digest": docs[pair["de"]]["record_digest"],
                         "en_record_digest": docs[pair["en"]]["record_digest"]} for pair in manifest["pairs"]]
            write_new(args.out, template)
        elif args.command == "bundle":
            bundle = make_bundle(args.run, json.loads(args.reviews.read_text()))
            write_new(args.out, bundle)
            print(json.dumps({"accepted_pairs": len(bundle["pairs"]), "unpaired": len(bundle["unpaired"])}))
        else:
            bundle = check_bundle(json.loads(args.bundle.read_text()))
            if args.command == "analyze":
                parts = urlsplit(args.endpoint)
                if (not args.confirm_local_inference or parts.scheme != "http" or parts.hostname != "127.0.0.1" or
                        parts.port != 11436 or parts.username or parts.password or parts.query or parts.fragment or
                        parts.path not in ("", "/v1", "/v1/")):
                    print("BLOCKED: explicitly confirmed loopback Apertus endpoint required; zero calls")
                    return 3
                if not 1 <= len(bundle["pairs"]) <= 5:
                    raise ValueError("analysis budget: 1..5 accepted pairs")
                if any(pair["analysis"]["status"] != "not_run" for pair in bundle["pairs"]):
                    raise ValueError("analysis requires a fresh capture bundle; no automatic retry")
                runtime = json.loads(args.runtime.read_text())
                if (not re.fullmatch("[0-9a-f]{64}", runtime.get("model_sha256", "")) or
                        not runtime.get("runtime_revision") or runtime.get("model_family") != "Apertus"):
                    raise ValueError("runtime pin needs Apertus model SHA-256 and runtime revision")
                from .backends import OpenAICompatibleBackend
                backend = OpenAICompatibleBackend(args.endpoint, args.model, "local", timeout_s=90)
                # Reserve output BEFORE calls. Each pair checkpoint survives interruption.
                args.out.mkdir(parents=True, exist_ok=False)
                for pair in bundle["pairs"]:
                    pair["analysis"] = analyze_pair(pair, backend, runtime)
                    write_new(args.out / (pair["pair_id"] + ".json"), pair["analysis"])
                bundle["model_calls"] = sum(p["analysis"]["model_calls"] for p in bundle["pairs"])
                seal(bundle)
                write_new(args.out / "bundle.json", bundle)
            elif args.command == "view":
                from .observatory_viewer import render
                args.out.parent.mkdir(parents=True, exist_ok=True)
                with args.out.open("x", encoding="utf-8") as stream:
                    stream.write(render(bundle, json.loads(args.reviews.read_text()) if args.reviews else None))
            elif args.command == "review":
                write_new(args.out, review_event(bundle, args.pair, args.candidate, args.state, args.reviewer, args.rationale))
            elif args.command == "review-import":
                write_new(args.out, import_reviews(bundle, json.loads(args.drafts.read_text())))
            elif args.command == "replay":
                print(json.dumps(replay(bundle)))
            else:
                print(json.dumps({"verified": True, "pairs": len(bundle["pairs"]), "model_calls": bundle["model_calls"]}))
        return 0
    except (ValueError, KeyError, OSError, StopIteration, RuntimeError) as exc:
        print("BLOCKED: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
