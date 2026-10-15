"""Offline #36 tests: fixture family -> evidence bundle -> existing analysis/review validation."""
import json
import sqlite3
from datetime import datetime, timezone, timedelta
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from uzh_rsd import captures, discovery, federal_desk as desk
from uzh_rsd.campaign_center import Store
from uzh_rsd.government_scout import FetchResponse

H = "https://www.bfe.admin.ch"
DE, FR, IT = H + "/de/antrag", H + "/fr/demande", H + "/it/domanda"
BODY_DE = b"<main><h1>Antrag</h1><ul><li>Frist: 30 Tage</li></ul><table><tr><td>Gebuehr</td><td>0 CHF</td></tr></table><p>Es besteht kein Anspruch.</p></main>"
BODY_FR = "<main><h1>Demande</h1><ul><li>Délai: 20 jours</li></ul><p>Il n'existe aucun droit.</p></main>".encode()


def snapshot(status="one_directional", extra_fr=False):
    langs = {"de": [{"url": DE}], "fr": [{"url": FR}] + ([{"url": FR + "-b"}] if extra_fr else []), "it": [{"url": IT}], "en": []}
    return {"id": "a" * 32, "site_id": "bfe", "observed_at": "2026-10-14T00:00:00+00:00", "families": [{"family_id": "fam1", "status": status, "languages": langs,
            "edges": [{"from": DE, "to": FR, "language": "fr", "kind": "page_hreflang", "declared_by": DE}],
            "language_availability": {l: ("observed" if langs[l] else "not_observed") for l in langs}}]}


PAIRING = {"left_language": "de", "right_language": "fr", "certified": True, "reviewer": "r1",
           "pairing_rationale": "Source-declared hreflang, reviewer checked", "rights_basis": "Project-authored fixture"}


def fetcher_for(pages):
    calls = []

    def fetch(url, _p, **_k):
        calls.append(url)
        if url in pages:
            return FetchResponse(200, pages[url][1] if len(pages[url]) > 1 else url, {"Content-Type": "text/html; charset=utf-8", "ETag": "x"}, pages[url][0],
                                 ({"from": url, "to": pages[url][1], "status": 302},) if len(pages[url]) > 1 else ())
        return FetchResponse(404, url, {}, b"")
    return fetch, calls


def run(snap=None, pages=None, pairing=PAIRING, **kw):
    fetch, calls = fetcher_for(pages or {DE: (BODY_DE,), FR: (BODY_FR,)})
    with tempfile.TemporaryDirectory() as d, patch("uzh_rsd.discovery_transport.time.sleep"):
        res = captures.capture_family(snap or snapshot(), "fam1", pairing, fetcher=fetch, raw_dir=d, fixture=True, delay_seconds=0, **kw)
        res["calls"] = calls
        res["raw_files"] = sorted(str(p.relative_to(d)) for p in Path(d).rglob("*.html"))
    return res


class CaptureTest(unittest.TestCase):
    def test_family_capture_flows_into_existing_analysis_and_review(self):
        res = run()
        self.assertEqual(res["status"], "captured")
        b = res["bundle"]
        desk.validate(b)
        self.assertEqual(b["analysis"]["model_calls"], 0)
        entries = [{"left": "30 Tage", "right": "20 jours", "kind": "CHANGE"}]
        b["analysis"] = {"status": "complete", "parsed": entries, "candidates": desk.candidates(b, entries), "model_calls": 0, "method": "authored-fixture"}
        desk.seal(b); desk.validate(b)
        out = desk.review(b, {"bundle_digest": b["digest"], "reviews": [{"candidate_id": b["analysis"]["candidates"][0]["id"],
                              "state": "confirmed", "reviewer": "r", "reason": "differs"}]})
        self.assertEqual(out["reviews"][0]["state"], "confirmed")
        ev = res["evidence"]
        self.assertEqual(ev["pairing"]["status"], "CANDIDATE")
        self.assertIn("family_status:one_directional", ev["pairing"]["uncertainty"])
        self.assertEqual(ev["links"]["left"]["live_original"], DE)
        self.assertTrue(ev["links"]["left"]["captured_evidence"].startswith("sha256:"))
        # table, list and numbers/negation survive in the extraction
        text = b["left"]["extracted_text"]
        for needle in ("30 Tage", "0 CHF", "kein Anspruch"):
            self.assertIn(needle, text)

    def test_reproducible_hashes_extraction_and_offsets(self):
        a, b = run(), run()
        self.assertEqual(a["bundle"]["left"]["sha256_extract"], b["bundle"]["left"]["sha256_extract"])
        self.assertEqual(a["evidence"]["retrievals"]["left"]["sha256_raw"], b["evidence"]["retrievals"]["left"]["sha256_raw"])
        info = a["evidence"]["extraction"]["left"]
        self.assertEqual((info["revision"], info["status"], info["completeness"]["status"]), ("lis-main-content-v1", "ok", "complete"))
        self.assertIn("Unicode code-point", info["offset_basis"])
        doc = a["bundle"]["left"]
        for blk in doc["blocks"]:
            self.assertEqual(doc["extracted_text"][blk["start"]:blk["end"]], blk["text"])
        self.assertEqual(len(a["raw_files"]), 2)

    def test_identical_bodies_share_address_but_keep_distinct_retrieval_provenance(self):
        snap = snapshot()
        res = run(snap, {DE: (BODY_FR, H + "/de/final"), FR: (BODY_FR,)}, )
        r = res["evidence"]["retrievals"]
        self.assertEqual(r["left"]["content_address"], r["right"]["content_address"])
        self.assertNotEqual(r["left"]["retrieval_id"], r["right"]["retrieval_id"])
        self.assertEqual(r["left"]["final_url"], H + "/de/final")
        self.assertEqual(r["left"]["redirects"][0]["status"], 302)
        self.assertEqual(len(res["raw_files"]), 1)  # content-addressed: stored once

    def test_unmatched_content_makes_extraction_partial_and_blocks_omission_confirmation(self):
        odd = b"<main><h1>Antrag</h1><div>Frist 30 Tage ohne Verlaengerung</div><p>Text.</p></main>"
        res = run(pages={DE: (odd,), FR: (BODY_FR,)})
        self.assertEqual(res["status"], "captured")
        gate = res["evidence"]["omission_confirmation"]
        self.assertFalse(gate["allowed"]); self.assertEqual(gate["blockers"], ["extraction_partial:left"])
        self.assertIn("verlaengerung", res["evidence"]["extraction"]["left"]["completeness"]["unmatched_words"])
        b = res["bundle"]
        entries = [{"left": "Text.", "right": "", "kind": "LEFT_ONLY"}]
        b["analysis"] = {"status": "complete", "parsed": entries, "candidates": desk.candidates(b, entries), "model_calls": 0, "method": "authored"}
        desk.seal(b)
        review = {"bundle_digest": b["digest"], "reviews": [{"candidate_id": b["analysis"]["candidates"][0]["id"], "state": "confirmed",
                  "reviewer": "r", "reason": "x", "full_source_checked": True}]}
        with self.assertRaisesRegex(ValueError, "omission confirmation blocked"):
            desk.review(b, review)
        review["reviews"][0]["state"] = "unresolved"
        desk.review(b, review)  # uncertainty remains reviewable

    def test_extraction_failure_produces_no_bundle_and_retains_evidence(self):
        res = run(pages={DE: (b"<main><h1>Antrag</h1>\xff\xfe</main>",), FR: (BODY_FR,)})
        self.assertEqual(res["status"], "extraction_failed")
        self.assertIsNone(res["bundle"])
        self.assertFalse(res["evidence"]["omission_confirmation"]["allowed"])
        self.assertIn("sha256_raw", res["evidence"]["retrievals"]["left"])

    def test_blocked_without_requests(self):
        cases = [
            (snapshot(), {**PAIRING, "certified": False}, "uncertified_pair"),
            (snapshot("contradictory"), PAIRING, "contradictory_family"),
            (snapshot(extra_fr=True), PAIRING, "right_language_not_single_observed:fr"),
            (snapshot(), {**PAIRING, "right_language": "en"}, "right_language_not_single_observed:en"),
            ({**snapshot(), "site_id": "bafu"}, PAIRING, "unsupported_site"),
        ]
        for snap, pairing, expected in cases:
            res = run(snap, pairing=pairing)
            with self.subTest(expected=expected):
                self.assertEqual(res["status"], "blocked"); self.assertIn(expected, res["blockers"])
                self.assertEqual((res["requests"], res["calls"]), (0, []))
        snap = snapshot(); snap["families"][0]["languages"]["fr"] = [{"url": "https://evil.test/fr/x"}]
        self.assertTrue(any(b.startswith("unsupported_host") for b in run(snap)["blockers"]))

    def test_live_capture_needs_recorded_permission(self):
        fetch, calls = fetcher_for({DE: (BODY_DE,), FR: (BODY_FR,)})
        with tempfile.TemporaryDirectory() as d:
            res = captures.capture_family(snapshot(), "fam1", PAIRING, fetcher=fetch, raw_dir=d, fixture=False)
        self.assertIn("content_use_not_permitted", res["blockers"]); self.assertEqual(calls, [])

    def test_capture_owns_and_closes_store_on_success_and_failure(self):
        for pages in (None, {DE: (BODY_DE,)}):
            store = captures.DiscoveryStore()
            with patch.object(captures, "DiscoveryStore", return_value=store):
                run(pages=pages)
            with self.assertRaises(sqlite3.ProgrammingError):
                store.db.execute("SELECT 1")
        store = captures.DiscoveryStore()
        with patch.object(captures, "DiscoveryStore", return_value=store), patch.object(captures, "_capture", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                run()
        with self.assertRaises(sqlite3.ProgrammingError):
            store.db.execute("SELECT 1")

    def test_fixture_without_injected_fetcher_never_uses_network(self):
        with tempfile.TemporaryDirectory() as d, patch.object(captures, "GuardedTransport") as transport:
            res = captures.capture_family(snapshot(), "fam1", PAIRING, raw_dir=d, fixture=True)
        self.assertEqual(res["blockers"], ["fixture_fetcher_required"])
        transport.assert_not_called()

    def test_bundle_keeps_individual_retrieval_times_and_final_urls(self):
        start = datetime(2026, 10, 15, tzinfo=timezone.utc)
        times = iter([start, start + timedelta(seconds=3)])
        res = run(pages={DE: (BODY_DE, H + "/de/final"), FR: (BODY_FR,)}, clock=lambda: next(times))
        b = res["bundle"]
        self.assertEqual(b["left"]["canonical_url"], H + "/de/final")
        self.assertEqual(b["left"]["retrieved_at_utc"], start.isoformat())
        self.assertNotEqual(b["left"]["retrieved_at_utc"], b["right"]["retrieved_at_utc"])
        desk.validate(b)

    def test_fetch_failure_is_recorded_not_bundled(self):
        res = run(pages={DE: (BODY_DE,)})
        self.assertEqual(res["status"], "failed"); self.assertIsNone(res["bundle"])
        self.assertEqual(len(res["raw_files"]), 1)  # successful side remains inspectable


class CampaignCaptureTest(unittest.TestCase):
    def test_preparation_blockers_actions_and_old_campaign_readable(self):
        with tempfile.TemporaryDirectory() as d:
            fetch, _ = fetcher_for({DE: (BODY_DE,), FR: (BODY_FR,)})
            s = Store(d, capture_fetcher=fetch); self.addCleanup(s.lease.close)
            s.capture_fixture = True; s.capture_delay = 0
            c = s.create("x", site_ids=["bfe"])
            snap = snapshot(); (Path(d) / ("snapshot-" + snap["id"] + ".json")).write_text(json.dumps(snap))
            cc = s.read(c["id"]); cc["discovery_runs"] = [{"id": "r", "state": "complete", "snapshot_id": snap["id"], "site_id": "bfe"}]; s.write(cc)
            s.page_scope(c["id"], [{"snapshot_id": snap["id"], "family_id": "fam1"}])
            self.assertEqual(s.preparation(c["id"])[0]["capture_status"], "not_captured")
            bad = s.capture(c["id"], snap["id"], "fam1", {**PAIRING, "certified": False})
            self.assertEqual(bad["status"], "blocked")
            with patch("uzh_rsd.discovery_transport.time.sleep"):
                ok = s.capture(c["id"], snap["id"], "fam1", PAIRING)
            self.assertEqual(ok["status"], "captured")
            prep = s.preparation(c["id"])[0]
            self.assertEqual(prep["live_originals"]["left"], DE)
            self.assertTrue(prep["captured_evidence"]["left"]["content_address"].startswith("sha256:"))
            self.assertTrue(prep["omission_confirmation"]["allowed"])
            pair = s.read(c["id"])["pairs"][0]
            desk.validate(pair["bundle"]); self.assertEqual(pair["status"], "ready")
            full = s.read(c["id"])
            full["pairs"] *= 20
            s.write(full)
            with patch.object(captures, "capture_family") as capture, self.assertRaisesRegex(ValueError, "Campaign limit"):
                s.capture(c["id"], snap["id"], "fam1", PAIRING)
            capture.assert_not_called()
            full["pairs"] = full["pairs"][:1]
            s.write(full)
            with self.assertRaises(ValueError):
                s.capture(c["id"], "b" * 32, "fam1", PAIRING)  # not in saved scope
            s.lease.close()
            s2 = Store(d); self.addCleanup(s2.lease.close)
            self.assertEqual(s2.capture(c["id"], snap["id"], "fam1", PAIRING)["blockers"], ["live_capture_not_authorised"])

    def test_old_bundle_without_capture_evidence_still_valid(self):
        with tempfile.TemporaryDirectory() as d:
            desk.demo(Path(d) / "x")
            b = json.loads((Path(d) / "x" / "bundle.json").read_text())
            self.assertNotIn("capture_evidence", b); desk.validate(b)


if __name__ == "__main__":
    unittest.main()
