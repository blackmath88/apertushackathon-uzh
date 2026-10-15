"""Normal app demo configuration exercises discovery/capture with all external sockets refused."""
import tempfile
import unittest
from unittest.mock import patch
from uzh_rsd.campaign_center import Store
from uzh_rsd import federal_demo as demo

class FederalDemoTest(unittest.TestCase):
    def test_demo_discovery_to_capture_uses_only_authored_content(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(d);self.addCleanup(store.lease.close)
            demo.configure(store)
            c=store.create('Offline walkthrough',site_ids=['bfe'])
            with patch('socket.create_connection',side_effect=AssertionError('External network forbidden')):
                run=store.discovery_start(c['id'],'bfe',True)
                for thread in store.threads:
                    thread.join(timeout=5)
                    self.assertFalse(thread.is_alive())
                saved=store.read(c['id'])
                finished=saved['discovery_runs'][0]
                self.assertEqual(finished['state'],'complete')
                self.assertTrue(finished['fixture'])
                snap=store.snapshot(c['id'],finished['snapshot_id'])
                self.assertTrue(snap['fixture'])
                fam=next(f for f in snap['families'] if all(f['languages'][lang] for lang in demo.MEMBERS))
                store.page_scope(c['id'],[{'snapshot_id':snap['id'],'family_id':fam['family_id']}])
                result=store.capture(c['id'],snap['id'],fam['family_id'],{
                    'left_language':'de','right_language':'fr','certified':True,'reviewer':'Fixture reviewer',
                    'pairing_rationale':'Authored four-language family','rights_basis':'Project-authored demo'})
                self.assertEqual(result['status'],'captured')
                b=store.read(c['id'])['pairs'][0]['bundle']
                self.assertTrue(b['fixture'])
                self.assertIn('30 Tage',b['left']['extracted_text'])
                self.assertIn('20 jours',b['right']['extracted_text'])
                self.assertEqual(b['analysis']['model_calls'],0)
                self.assertEqual(store.evidence(c['id'],result['pair_id'],'left')[0],demo.html('de'))
                self.assertEqual(demo.fetch('https://unknown.invalid/',None).status,404)
            self.assertIsNone(store.inference)
            self.assertTrue(store.demo_discovery)
            self.assertEqual(run['site_id'],'bfe')

    def test_demo_does_not_relabel_preexisting_discovery_as_authored(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(d);self.addCleanup(store.lease.close)
            c=store.create('Existing work',site_ids=['bfe'])
            c['discovery_runs']=[{'id':'old','state':'complete'}]
            store.write(c)
            with self.assertRaisesRegex(ValueError,'separate data directory'):
                demo.configure(store)
            self.assertFalse(store.demo_discovery)

    def test_discovery_runs_are_serialised_across_campaigns(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(d);self.addCleanup(store.lease.close)
            demo.configure(store)
            first=store.create('First',site_ids=['bfe'])
            second=store.create('Second',site_ids=['bfe'])
            with patch('threading.Thread.start'):
                store.discovery_start(first['id'],'bfe',True)
                with self.assertRaisesRegex(ValueError,'already running'):
                    store.discovery_start(second['id'],'bfe',True)
            self.assertEqual(store.read(second['id']).get('discovery_runs', []),[])

    def test_demo_refuses_enabled_inference(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(d,inference={'model':'Apertus'});self.addCleanup(store.lease.close)
            with self.assertRaisesRegex(ValueError,'inference disabled'):
                demo.configure(store)
            self.assertIsNone(store.discovery_fetcher)

if __name__=='__main__':unittest.main()
