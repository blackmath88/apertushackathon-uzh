import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from io import BytesIO

from uzh_rsd import federal_desk as d


class FederalDeskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        d.demo(self.root / 'demo')
        self.b = json.loads((self.root / 'demo/bundle.json').read_text())

    def draft(self):
        return {'bundle_digest': self.b['digest'], 'reviews': [{
            'candidate_id': self.b['analysis']['candidates'][0]['id'],
            'state': 'confirmed', 'reviewer': 'test reviewer', 'reason': 'Checked both excerpts',
            'full_source_checked': True}]}

    def test_round_trip_review_without_mutating_capture(self):
        original = copy.deepcopy(self.b)
        result = d.review(self.b, self.draft())
        self.assertEqual(result['reviews'][0]['state'], 'confirmed')
        self.assertTrue(result['fixture'])
        self.assertEqual(self.b, original)

    def test_stale_review_rejected(self):
        draft = self.draft(); draft['bundle_digest'] = 'old'
        with self.assertRaises(ValueError): d.review(self.b, draft)

    def test_duplicate_reviews_rejected(self):
        draft = self.draft(); draft['reviews'] *= 2
        with self.assertRaises(ValueError): d.review(self.b, draft)

    def test_forged_locations_rejected_even_after_reseal(self):
        self.b['analysis']['candidates'][0]['locations']['left'][0]['start'] = 0
        d.seal(self.b)
        with self.assertRaises(ValueError): d.validate(self.b)

    def test_ambiguous_excerpt_cannot_be_confirmed(self):
        entry = {'left': 'e', 'right': 'e', 'kind': 'CHANGE'}
        self.b['analysis']['parsed'] = [entry]
        self.b['analysis']['candidates'] = d.candidates(self.b, [entry]); d.seal(self.b)
        with self.assertRaises(ValueError): d.review(self.b, self.draft())

    def test_omission_requires_full_source_review(self):
        entry = {'left': '30 Tage', 'right': '', 'kind': 'LEFT_ONLY'}
        self.b['analysis']['parsed'] = [entry]
        self.b['analysis']['candidates'] = d.candidates(self.b, [entry]);d.seal(self.b)
        draft=self.draft();draft['reviews'][0]['full_source_checked']=False
        with self.assertRaises(ValueError):d.review(self.b,draft)

    def test_live_import_needs_permission_record(self):
        with self.assertRaises(ValueError):
            d.prepare(b'<main><p>A</p></main>',b'<main><p>B</p></main>',self.b['provenance'])

    def test_different_languages_and_host_enforced(self):
        self.b['right']['locale']='de';d.seal(self.b)
        with self.assertRaises(ValueError):d.validate(self.b)

    def fresh(self):
        b=copy.deepcopy(self.b);b['analysis']={'status':'not_run','candidates':[],'model_calls':0}
        return d.seal(b)

    def test_analysis_checkpoints_and_no_retry(self):
        calls=[]
        def transport(body):
            self.assertTrue((self.root/'run/intent.json').exists())
            calls.append(body)
            return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'differences':self.b['analysis']['parsed']})}}]}
        result=d.analyze(self.fresh(),'Apertus','a'*64,'test-runtime',self.root/'run',transport)
        self.assertEqual(result['analysis']['status'],'complete')
        self.assertEqual(len(calls),1)
        self.assertTrue((self.root/'run/raw.json').exists())
        with self.assertRaises(FileExistsError):d.analyze(self.fresh(),'Apertus','a'*64,'test-runtime',self.root/'run',transport)
        self.assertEqual(len(calls),1)

    def test_truncation_preserves_raw_and_reading_desk(self):
        response={'choices':[{'finish_reason':'length','message':{'content':'{"differences":['}}]}
        result=d.analyze(self.fresh(),'Apertus','a'*64,'test',self.root/'run',lambda _:response)
        self.assertEqual(result['analysis']['status'],'failed')
        self.assertEqual(result['analysis']['candidates'],[])
        self.assertTrue((self.root/'run/index.html').exists())
        self.assertEqual(json.loads((self.root/'run/raw.json').read_text()),response)

    def test_interrupt_leaves_intent_and_refuses_reuse(self):
        def interrupted(_):raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):d.analyze(self.fresh(),'Apertus','a'*64,'test',self.root/'run',interrupted)
        self.assertTrue((self.root/'run/intent.json').exists())
        self.assertFalse((self.root/'run/bundle.json').exists())

    def test_payload_cannot_close_script(self):
        b=self.fresh();b['provenance']['reviewer']='</script><script>alert(1)</script>';d.seal(b)
        html=d.render(b)
        self.assertNotIn('</script><script>alert(1)',html)
        self.assertIn('\\u003c/script>',html)

    def test_endpoint_model_mismatch_prevents_generation(self):
        class Opener:
            def __init__(self):self.calls=[]
            def open(self, request, timeout):
                self.calls.append(request)
                return BytesIO(b'{"data":[{"id":"other-model"}]}')
        opener=Opener()
        with patch.object(d,'build_opener',return_value=opener):
            with self.assertRaises(ValueError):d.local_transport({'model':'Apertus'})
        self.assertEqual(opener.calls,['http://127.0.0.1:11436/v1/models'])

    def test_transport_failure_is_preserved_not_retried(self):
        calls=[]
        def failed(body):calls.append(body);raise TimeoutError()
        result=d.analyze(self.fresh(),'Apertus','a'*64,'test',self.root/'run',failed)
        self.assertEqual(len(calls),1)
        self.assertEqual(result['analysis']['failure'],'TimeoutError')
        self.assertIsNone(result['analysis']['model_calls'])

if __name__=='__main__':unittest.main()
