"""Regression and workflow checks; all generation data is synthetic."""
import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest import mock

import test_observatory as fixtures
from uzh_rsd.backends import Generation
from uzh_rsd.observatory import accepted_pairs, check_bundle, main, replay, seal
from uzh_rsd.observatory_capture import digest, save_capture, verify_document
from uzh_rsd.observatory_facts import observe, compare_values
from uzh_rsd.observatory_run import preflight, run_local, validate_endpoint, validate_runtime
from uzh_rsd.observatory_viewer import render


class RoundTwoTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.WorkflowTests();self.fixture.setUp()
        self.root,self.bundle=self.fixture.root,self.fixture.bundle
        self.runtime={'model_family':'Apertus','model_sha256':'a'*64,'runtime_revision':'synthetic-test'}
        self.backend=self.fixture.backend(json.dumps({'differences':[{'a':'14 days.','b':'30 Tagen.','kind':'CHANGE','severity':3}]}))
        self.factory=mock.Mock(return_value=self.backend)
        self.probe=mock.Mock(return_value={'status':'ready','reported_model_id':'fixture'})
    def tearDown(self): self.fixture.tearDown()
    def execute(self, **kwargs):
        return run_local(self.bundle,self.root/'local','http://127.0.0.1:11436/v1','fixture',self.runtime,
                         probe=self.probe,backend_factory=self.factory,**kwargs)

    def test_removed_block_with_resealed_record_is_rejected(self):
        doc=copy.deepcopy(self.fixture.docs[next(iter(self.fixture.docs))]);doc['blocks'].pop()
        doc['record_digest']=digest({k:v for k,v in doc.items() if k!='record_digest'})
        with self.assertRaises(ValueError):verify_document(doc)

    def test_duplicate_pair_and_model_authority_are_rejected(self):
        b=copy.deepcopy(self.bundle);b['pairs'].append(copy.deepcopy(b['pairs'][0]));seal(b)
        with self.assertRaises(ValueError):check_bundle(b)
        p=self.bundle['pairs'][0];p['analysis']=self.fixture.analysis([{'a':'14 days.','b':'30 Tagen.','kind':'CHANGE','severity':3}])
        p['analysis']['candidates'][0]['review_state']='human_confirmed';seal(self.bundle)
        with self.assertRaises(ValueError):check_bundle(self.bundle)

    def test_forged_language_prefix_is_rejected(self):
        from uzh_rsd.observatory import accepted_pairs
        d=copy.deepcopy(self.fixture.docs);en=self.fixture.review['en'];d[en]['language']='english';d[en]['record_digest']=digest({k:v for k,v in d[en].items() if k!='record_digest'})
        r={**self.fixture.review,'en_record_digest':d[en]['record_digest']}
        with self.assertRaises(ValueError):accepted_pairs(d,[r])

    def test_observations_are_exact_not_semantic_differences(self):
        values=compare_values(self.bundle['pairs'][0])
        fourteen=next(v for v in values if v['value']=='14')
        self.assertEqual((len(fourteen['de']),len(fourteen['en'])),(0,1))
        doc=self.bundle['pairs'][0]['en'];o=fourteen['en'][0]
        self.assertEqual(doc['text'][o['start']:o['end']],o['value'])
        self.assertFalse(observe(doc)['semantic_analysis'])
        self.assertNotIn('discrepancy',fourteen)

    def test_preflight_mismatch_blocks_without_generation(self):
        op=mock.Mock();op.open.return_value=fixtures.Response(json.dumps({'data':[{'id':'wrong'}]}).encode(),'http://127.0.0.1:11436/v1/models','application/json')
        result=preflight('http://127.0.0.1:11436/v1','fixture',self.runtime,opener=op)
        self.assertEqual(result['reason'],'expected_model_not_reported');self.assertEqual(result['model_calls'],0)
        self.assertEqual(op.open.call_count,1)

    def test_preflight_ready_and_transport_failure_are_observed(self):
        op=mock.Mock();op.open.return_value=fixtures.Response(b'{"data":[{"id":"fixture"}]}','http://127.0.0.1:11436/v1/models','application/json')
        self.assertEqual(preflight('http://127.0.0.1:11436/v1','fixture',self.runtime,opener=op)['status'],'ready')
        op.open.side_effect=OSError('offline')
        self.assertEqual(preflight('http://127.0.0.1:11436/v1','fixture',self.runtime,opener=op)['status'],'blocked')

    def test_cloud_endpoint_and_wrong_gguf_refuse_before_probe(self):
        with self.assertRaises(ValueError):validate_endpoint('https://paid.example/v1')
        f=self.root/'weights.gguf';f.write_bytes(b'fixture')
        with self.assertRaises(ValueError):self.execute(gguf=f)
        self.probe.assert_not_called();self.assertFalse((self.root/'local').exists())
        self.assertTrue(validate_runtime({**self.runtime,'model_sha256':sha256(b'fixture').hexdigest()},f)['local_file_hash_verified'])

    def test_blocked_run_still_produces_reading_desk_with_no_generation(self):
        self.probe.return_value={'status':'blocked','reason':'offline'}
        meta=self.execute()
        self.assertEqual(meta['state'],'blocked');self.factory.assert_not_called()
        self.assertTrue((self.root/'local/index.html').exists())
        self.assertEqual(json.loads((self.root/'local/bundle.json').read_text())['model_calls'],0)

    def test_success_has_checkpointed_raw_replay_and_html(self):
        meta=self.execute()
        self.assertEqual(meta['state'],'attempts_completed');self.assertEqual(meta['model_calls'],1)
        saved=check_bundle(json.loads((self.root/'local/bundle.json').read_text()))
        self.assertEqual(replay(saved)['replayed_pairs'],1)
        self.assertTrue((self.root/'local/attempts'/ (saved['pairs'][0]['pair_id']+'.json')).exists())
        self.assertTrue((self.root/'local/events/002-intent.json').exists())

    def test_unparseable_response_is_not_usable_coverage(self):
        self.backend.generate.return_value=Generation('not-json',finish_reason='stop')
        meta=self.execute()
        self.assertEqual(meta['state'],'attempts_completed')
        self.assertEqual(meta['model_output_coverage'],'partial_or_unresolved')
        self.assertEqual(meta['semantic_coverage'],'not_established')

    def test_transport_failure_stops_before_next_pair(self):
        docs={};review=copy.deepcopy(self.fixture.review)
        for lang in ('de','en'):
            url=review[lang].replace('.html','-two.html');body=fixtures.html(lang,'Second service')
            ref=save_capture(self.root,body,fixtures.captured(url,lang,body))
            doc=json.loads((self.root/'documents'/(ref['capture_id']+'.json')).read_text());docs[url]=doc
            review[lang]=url;review[lang+'_record_digest']=doc['record_digest']
        review['evidence_urls']=[review['de'],review['en']]
        self.bundle['pairs']+=accepted_pairs(docs,[review]);self.bundle['discovery']['captured']=4;seal(self.bundle)
        self.backend.generate.return_value=Generation(None,error='timeout')
        meta=self.execute()
        self.assertEqual(meta['state'],'incomplete');self.assertEqual(meta['processed_pairs'],1)
        self.assertEqual(self.backend.generate.call_count,1)

    def test_interruption_is_saved_as_unsettled_and_not_retried(self):
        self.backend.generate.side_effect=KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):self.execute()
        meta=json.loads((self.root/'local/run.json').read_text());saved=json.loads((self.root/'local/bundle.json').read_text())
        self.assertEqual(meta['state'],'incomplete');self.assertEqual(meta['model_calls'],1)
        self.assertEqual(saved['pairs'][0]['analysis']['attempt_settlement'],'unknown')
        self.assertEqual(replay(saved)['unresolved_attempts'],1)

    def test_exception_accounting_uses_observed_request_count(self):
        with mock.patch('uzh_rsd.observatory_run.analyze_pair',side_effect=ValueError('before generation')):
            meta=self.execute()
        self.assertEqual(meta['model_calls'],0);self.backend.generate.assert_not_called()

    def test_output_reuse_is_refused_and_cli_confirmation_precedes_io(self):
        self.execute()
        with self.assertRaises(FileExistsError):self.execute()
        with mock.patch('uzh_rsd.observatory_run.run_local') as run:
            code=main(['local-run','--bundle','absent','--runtime','absent','--model','fixture','--out',str(self.root/'fresh')])
        self.assertEqual(code,3);run.assert_not_called()

    def test_export_serialization_retains_numeric_digest(self):
        p=self.bundle['pairs'][0];p['analysis']=self.fixture.analysis([])
        p['analysis']['raw']['latency_s']=1.0;seal(self.bundle)
        page=render(self.bundle)
        payload=json.loads(page.split('<script type="application/json" id="desk-data">',1)[1].split('</script>',1)[0])
        self.assertEqual(json.loads(payload['bundle_export'])['bundle_digest'],self.bundle['bundle_digest'])
        check_bundle(json.loads(payload['bundle_export']))
        self.assertIn('"latency_s": 1.0',payload['bundle_export'])


if __name__=='__main__':unittest.main()
