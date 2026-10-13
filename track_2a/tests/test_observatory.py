"""Offline acceptance: network bounds, real evidence contracts and B2 boundary.

All model outputs here are synthetic fixtures, never city findings.
"""
import copy
from dataclasses import asdict
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
from urllib.error import HTTPError

from uzh_rsd.backends import Generation
from uzh_rsd.observatory import (accepted_pairs, analyze_pair, check_bundle, main, make_bundle,
                                  check_review_events, import_reviews, replay, review_event, seal)
from uzh_rsd.observatory_capture import extract, save_capture, verify_document, write_new
from uzh_rsd.observatory_viewer import render
from uzh_rsd.zurich_pilot import Captured, HOST, RobotsPolicy, scout

DE = f"https://{HOST}/de/service.html"
EN = f"https://{HOST}/en/service.html"
STAMP = "2026-10-13T20:00:00+00:00"


def html(lang, text, alternate=None):
    link = f'<link rel="alternate" hreflang="{alternate[0]}" href="{alternate[1]}">' if alternate else ""
    return f'<html lang="{lang}"><head><title>Service</title>{link}</head><body><nav><p>Noise</p></nav><main><h1>Service</h1><p>{text}</p></main><footer>Noise</footer></body></html>'.encode()


def captured(url, lang, body):
    return Captured(url=url, language=lang, retrieved_at_utc=STAMP, sha256_html=sha256(body).hexdigest(),
                    title="Service", depth=0, canonical=None, alternates={})


class Response:
    def __init__(self, data, url, mime="text/html"):
        self.data, self.url = data, url
        self.headers, self.status = {"Content-Type": mime}, 200
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, limit): return self.data[:limit]
    def geturl(self): return self.url


class Clock:
    def __init__(self): self.value, self.waits = 0.0, []
    def __call__(self): return self.value
    def sleep(self, value): self.waits.append(value); self.value += value


class Opener:
    def __init__(self, routes, robots=b"User-agent: *\nAllow: /\n"):
        self.routes, self.robots, self.calls = routes, robots, []
    def open(self, request, timeout):
        url = request.full_url
        self.calls.append(url)
        if url.endswith("robots.txt"):
            if isinstance(self.robots, Exception): raise self.robots
            return Response(self.robots, url, "text/plain")
        result = self.routes[url]
        if isinstance(result, Exception): raise result
        return Response(result, url)


class ScoutTests(unittest.TestCase):
    def test_alternate_is_enqueued_without_anchor(self):
        op = Opener({DE: html("de", "Hallo", ("en", EN)), EN: html("en", "Hello", ("de", DE))})
        clock = Clock()
        r = scout(DE, max_pages=2, opener=op, clock=clock, sleeper=clock.sleep)
        self.assertEqual(len(r["pairs"]), 1)
        self.assertEqual(op.calls, [f"https://{HOST}/robots.txt", DE, EN])
        self.assertEqual(clock.waits, [2, 2])
        self.assertEqual(r["model_calls"], 0)

    def test_robots_failure_keeps_audit_and_never_fetches_page(self):
        op = Opener({}, OSError("no robots"))
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "scout.json"
            with self.assertRaises(RuntimeError): scout(DE, opener=op, out=out)
            self.assertEqual(len(op.calls), 1)
            self.assertEqual(json.loads(out.read_text())["status"], "blocked")

    def test_longest_match_wildcard_and_allow_tie(self):
        p = RobotsPolicy("User-agent: *\nDisallow: /*.map.html$\nDisallow: /private\nAllow: /private/open\nDisallow: /tie\nAllow: /tie\n")
        self.assertFalse(p.can_fetch("", DE.replace("service.html", "x.map.html")))
        self.assertFalse(p.can_fetch("", f"https://{HOST}/private/x"))
        self.assertTrue(p.can_fetch("", f"https://{HOST}/private/open/x"))
        self.assertTrue(p.can_fetch("", f"https://{HOST}/tie"))

    def test_robots_rate_and_page_budget(self):
        op = Opener({DE: html("de", "Hallo", ("en", EN))}, b"User-agent: *\nCrawl-delay: 4\n")
        clock = Clock()
        r = scout(DE, max_pages=1, opener=op, clock=clock, sleeper=clock.sleep)
        self.assertEqual(len(op.calls), 2)
        self.assertEqual(clock.waits, [4])
        self.assertEqual(r["retrieval_policy"]["delay_seconds"], 4)

    def test_redirect_never_followed_and_overload_stops(self):
        for status in (301, 429, 503):
            op = Opener({DE: HTTPError(DE, status, "refused", {"Location": EN}, None), EN: html("en", "hello")})
            clock = Clock()
            r = scout(DE, additional_seeds=(EN,), max_pages=2, opener=op, clock=clock, sleeper=clock.sleep)
            self.assertEqual(r["failures"][0]["http_status"], status)
            self.assertEqual(len(op.calls), 3 if status == 301 else 2)

    def test_invalid_limits_refuse_before_network(self):
        for kw in ({"delay_seconds": float("nan")}, {"timeout": 0}, {"max_pages": True}, {"delay_seconds": float("inf")}):
            op = Opener({})
            with self.assertRaises(ValueError): scout(DE, opener=op, **kw)
            self.assertEqual(op.calls, [])

    def test_too_large_is_audited(self):
        op = Opener({DE: b"x" * 1000001})
        clock = Clock()
        r = scout(DE, max_pages=1, opener=op, clock=clock, sleeper=clock.sleep)
        self.assertEqual(r["failures"][0]["reason"], "too_large")
        self.assertEqual(r["requests"][-1]["status"], "too_large")


class CaptureTests(unittest.TestCase):
    def test_blocks_preserve_inline_lists_tables_and_free_hours(self):
        body = b'<html lang="de"><main><h1>Titel</h1><p>Vor <b>14</b> Tagen.</p><ul><li><p>Liste</p></li></ul><table><tr><th>Tag</th><td>14</td></tr></table><stzh-richtext><h4>Mo</h4>13.00-17.00 Uhr<h4>Fr</h4>geschlossen</stzh-richtext><script>bad()</script></main></html>'
        d = extract(body)
        self.assertIn("Vor 14 Tagen.", d["text"])
        self.assertEqual(d["text"].count("Liste"), 1)
        self.assertIn("Tag | 14", d["text"])
        self.assertIn("13.00-17.00 Uhr", d["text"])
        self.assertNotIn("bad()", d["text"])
        for b in d["blocks"]: self.assertEqual(d["text"][b["start"]:b["end"]], b["text"])

    def test_contact_attributes_have_explicit_locations(self):
        d = extract(b'<main><stzh-contact heading="Desk" street="[&quot;Street 17&quot;]" postal-code="8001"></stzh-contact></main>')
        self.assertIn("Street 17", d["text"])
        self.assertIn("street", [b["source_attribute"] for b in d["blocks"]])

    def test_no_main_or_multiple_main_is_unresolved(self):
        for data in (b"<p>Hello</p>", b"<main>Hello</main><main>World</main>"):
            self.assertEqual(extract(data)["status"], "unresolved")

    def test_round_trip_hash_tampering_and_immutable_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td);body = html("en", "Hello")
            ref = save_capture(root, body, captured(EN, "en", body))
            doc = json.loads((root / "documents" / (ref["capture_id"] + ".json")).read_text())
            verify_document(doc, root)
            with self.assertRaises(FileExistsError): save_capture(root, body, captured(EN, "en", body))
            bad = copy.deepcopy(doc);bad["text"] += "fake"
            with self.assertRaises(ValueError): verify_document(bad)
            (root / "html" / (doc["html_sha256"] + ".html")).write_bytes(b"fake")
            with self.assertRaises(ValueError): verify_document(doc, root)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.root = Path(self.tmp.name)
        self.docs, refs = {}, []
        for url, lang, text in ((EN,"en","Register within 14 days."),(DE,"de","Anmelden innert 30 Tagen.")):
            body = html(lang, text);ref = save_capture(self.root, body, captured(url, lang, body));refs.append(ref)
            self.docs[url] = json.loads((self.root / "documents" / (ref["capture_id"] + ".json")).read_text())
        write_new(self.root / "scout.json", {"schema":"lost-in-switzerland/zurich-scout/v1","captures":refs,"pairs":[],"failures":[],"retrieval_policy":{"max_pages":2}})
        self.review = {"de":DE,"en":EN,"status":"accepted","pairing":"reviewed_relationship",
                       "reviewer":"test operator","reviewer_type":"human","reviewed_at_utc":STAMP,
                       "rationale":"synthetic fixture relationship","evidence_urls":[DE,EN],
                       "de_record_digest":self.docs[DE]["record_digest"],"en_record_digest":self.docs[EN]["record_digest"]}
        self.bundle = make_bundle(self.root, [self.review])

    def tearDown(self): self.tmp.cleanup()

    def backend(self, text, finish="stop"):
        b = mock.Mock();b.describe.return_value={"model":"synthetic-fixture"};b.generate.return_value=Generation(text, finish_reason=finish)
        return b

    def analysis(self, entries):
        return analyze_pair(self.bundle["pairs"][0],self.backend(json.dumps({"differences":entries})),{"model_family":"synthetic"})

    def test_pair_requires_pinned_review_and_language_metadata(self):
        for change in ({"de_record_digest":"bad"},{"reviewer":""},{"evidence_urls":[DE]}):
            review={**self.review,**change}
            with self.assertRaises(ValueError): accepted_pairs(self.docs,[review])
        docs=copy.deepcopy(self.docs);docs[EN]["language"]="de"
        with self.assertRaises(ValueError): accepted_pairs(docs,[self.review])

    def test_unpaired_sources_are_explorable_without_model(self):
        bundle=make_bundle(self.root,[])
        self.assertEqual(len(bundle["unpaired"]),2)
        self.assertEqual(bundle["model_calls"],0)
        self.assertIn("Lost in Switzerland",render(bundle))

    def test_b2_uses_existing_prompt_and_exact_character_evidence(self):
        a=self.analysis([{"a":"14 days.","b":"30 Tagen.","kind":"CHANGE","severity":3}])
        c=a["candidates"][0]
        self.assertEqual(c["validation"],"evidence_located")
        self.assertIsNone(c["confidence"])
        loc=c["en"]["locations"][0]
        self.assertEqual(self.docs[EN]["text"][loc["start"]:loc["end"]],"14 days.")
        self.assertEqual(a["provenance"]["prompt_version"],"b2-spans-v1")
        self.assertEqual(a["model_calls"],1)

    def test_bad_excerpt_is_preserved_as_unresolved_not_dropped(self):
        a=self.analysis([{"a":"invented deadline","b":"30 Tagen.","kind":"CHANGE","severity":3}])
        self.assertEqual(a["candidates"][0]["review_state"],"unresolved")
        self.assertIn("source_not_found",a["candidates"][0]["issues"])

    def test_empty_prediction_is_not_equivalence_and_failure_has_no_zero_fill(self):
        empty=self.analysis([])
        self.assertTrue(empty["no_difference_claim_is_not_equivalence"])
        a=analyze_pair(self.bundle["pairs"][0],self.backend("broken"),{})
        self.assertEqual(a["status"],"unparseable")
        self.assertEqual(a["candidates"],[])
        self.assertNotIn("diff_a",a)

    def test_oversized_input_refuses_model_without_truncation(self):
        pair=copy.deepcopy(self.bundle["pairs"][0]);pair["en"]["text"]="token "*2501
        b=self.backend("{}");a=analyze_pair(pair,b,{})
        b.generate.assert_not_called()
        self.assertEqual(a["model_calls"],0)

    def test_confirm_is_only_review_event_and_bad_evidence_cannot_confirm(self):
        pair=self.bundle["pairs"][0];pair["analysis"]=self.analysis([{"a":"14 days.","b":"30 Tagen.","kind":"CHANGE","severity":3}]);seal(self.bundle)
        c=pair["analysis"]["candidates"][0]
        event=review_event(self.bundle,pair["pair_id"],c["candidate_id"],"human_confirmed","reviewer","checked original sources")
        self.assertEqual(event["state"],"human_confirmed")
        self.assertEqual(c["review_state"],"candidate")
        c["validation"]="needs_review";seal(self.bundle)
        with self.assertRaises(ValueError): review_event(self.bundle,pair["pair_id"],c["candidate_id"],"human_confirmed","reviewer","reason")

    def test_viewer_cannot_execute_source_or_model_markup(self):
        doc=self.bundle["pairs"][0]["en"]
        # Re-seal a record to model lawful but hostile source text.
        doc["title"]='</script><script>window.PWNED=true</script>'
        from uzh_rsd.observatory_capture import digest
        doc["record_digest"]=digest({k:v for k,v in doc.items() if k!='record_digest'})
        pair=self.bundle["pairs"][0];pair['pairing_review']['en_record_digest']=doc['record_digest'];pair['revision']=digest([pair['de']['record_digest'],doc['record_digest']]);seal(self.bundle)
        page=render(self.bundle)
        self.assertNotIn('</script><script>window.PWNED',page)
        self.assertIn('\\u003c/script',page)
        self.assertIn("connect-src 'none'",page)
        self.assertNotIn('innerHTML',page)

    def test_capture_cli_blocks_before_network(self):
        with mock.patch('uzh_rsd.observatory.scout') as network:
            code=main(['capture','--seed',DE,'--out',str(self.root/'new')])
        self.assertEqual(code,3);network.assert_not_called()

    def test_analyze_cli_refuses_cloud_endpoint_before_backend(self):
        path=self.root/'bundle.json';write_new(path,self.bundle)
        with mock.patch('uzh_rsd.backends.OpenAICompatibleBackend') as backend:
            code=main(['analyze','--bundle',str(path),'--runtime',str(self.root/'absent'),
                       '--endpoint','https://paid.example/v1','--model','Apertus',
                       '--confirm-local-inference','--out',str(self.root/'out')])
        self.assertEqual(code,3);backend.assert_not_called()

    def test_replay_uses_saved_output_without_backend_or_network(self):
        pair=self.bundle['pairs'][0];pair['analysis']=self.analysis([{'a':'14 days.','b':'30 Tagen.','kind':'CHANGE','severity':3}]);seal(self.bundle)
        with mock.patch('urllib.request.urlopen',side_effect=AssertionError('network')):
            result=replay(self.bundle)
        self.assertEqual(result['new_model_calls'],0)
        pair['analysis']['candidates'][0]['excerpt_en']='fake';seal(self.bundle)
        with self.assertRaises(ValueError): replay(self.bundle)

    def test_review_import_checks_revision_and_retains_separate_events(self):
        pair=self.bundle['pairs'][0];pair['analysis']=self.analysis([{'a':'14 days.','b':'30 Tagen.','kind':'CHANGE','severity':3}]);seal(self.bundle)
        c=pair['analysis']['candidates'][0]
        draft={'pair_id':pair['pair_id'],'pair_revision':pair['revision'],'candidate_id':c['candidate_id'],'state':'rejected','reviewer':'Reviewer','rationale':'False positive'}
        packet={'schema':'lost-in-switzerland/review-drafts/v1','bundle_digest':self.bundle['bundle_digest'],'drafts':[draft]}
        events=import_reviews(self.bundle,packet)
        self.assertEqual(check_review_events(self.bundle,events)[0]['state'],'rejected')
        self.assertEqual(c['review_state'],'candidate')
        self.assertIn('"state": "rejected"',render(self.bundle,events))
        packet['bundle_digest']='stale'
        with self.assertRaises(ValueError): import_reviews(self.bundle,packet)

    def test_nonfinite_model_severity_is_unresolved_not_exception(self):
        a=self.analysis([{'a':'14 days.','b':'30 Tagen.','kind':'CHANGE','severity':float('nan')}])
        self.assertIsNone(a['candidates'][0]['severity'])
        self.assertIn('invalid_severity',a['candidates'][0]['issues'])


if __name__ == '__main__': unittest.main()
