import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uzh_rsd.campaign_center import Store

class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store=Store(self.tmp.name); self.addCleanup(self.store.lease.close)
    def test_persistence_and_review(self):
        c=self.store.create('Federal demo',True);p=c['pairs'][0]
        draft={'bundle_digest':p['bundle']['digest'],'reviews':[{'candidate_id':f['id'],'state':'unresolved','reviewer':'Editor','reason':'Needs review','full_source_checked':False} for f in p['bundle']['analysis']['candidates']]}
        self.store.review(c['id'],p['id'],draft)
        saved=self.store.read(c['id']);self.assertEqual(len(saved['pairs'][0]['review']['reviews']),2)
        self.assertEqual(len(list(Path(self.tmp.name).glob('review-*.json'))),1)
        draft['bundle_digest']='stale'
        with self.assertRaises(ValueError):self.store.review(c['id'],p['id'],draft)
        self.assertEqual(len(list(Path(self.tmp.name).glob('review-*.json'))),1)
    def test_disabled_inference(self):
        c=self.store.create('Demo',True)
        with self.assertRaises(ValueError):self.store.run(c['id'],c['pairs'][0]['id'])
    def test_second_store_refused(self):
        with self.assertRaises(BlockingIOError): Store(self.tmp.name)
    def test_unsettled_guard_survives_restart(self):
        c=self.store.create('Demo',True);c['pairs'][0]['status']='running';self.store.write(c)
        self.store.guard.write_text('{}'); self.store.lease.close()
        s=Store(self.tmp.name);self.addCleanup(s.lease.close)
        self.assertEqual(s.read(c['id'])['pairs'][0]['status'],'interrupted')
        self.assertTrue(s.guard.exists())
    def test_guard_blocks_other_campaigns(self):
        self.store.inference={'model':'Apertus'};self.store.guard.write_text('{}')
        c=self.store.create('Other',True)
        with self.assertRaises(ValueError):self.store.run(c['id'],c['pairs'][0]['id'])
    def test_run_completes_once_and_unknown_delivery_stays_reserved(self):
        from uzh_rsd import federal_desk
        c=self.store.create('Run',True);p=c['pairs'][0]
        p['bundle']['analysis']={'status':'not_run','candidates':[],'model_calls':0}
        federal_desk.seal(p['bundle']);p['status']='ready';self.store.write(c)
        self.store.inference={'model':'Apertus','weight_hash':'a'*64,'runtime_revision':'test'}
        with patch('threading.Thread.start'):
            started=self.store.run(c['id'],p['id'])
        self.assertTrue(self.store.guard.exists())
        response={'choices':[{'finish_reason':'stop','message':{'content':'{"differences":[]}'}}]}
        with patch.object(federal_desk,'local_transport',return_value=response) as transport:
            self.store.execute(c['id'],p['id'],started['pairs'][0]['run_id'])
            transport.assert_called_once()
        self.assertEqual(self.store.read(c['id'])['pairs'][0]['status'],'complete')
        self.assertFalse(self.store.guard.exists())
        with self.assertRaises(ValueError):self.store.run(c['id'],p['id'])
        c['pairs'][0]['status']='ready';self.store.write(c)
        with patch('threading.Thread.start'):
            started=self.store.run(c['id'],p['id'])
        with patch.object(federal_desk,'local_transport',side_effect=TimeoutError):
            self.store.execute(c['id'],p['id'],started['pairs'][0]['run_id'])
        self.assertEqual(self.store.read(c['id'])['pairs'][0]['status'],'unsettled')
        self.assertTrue(self.store.guard.exists())

    def test_unknown_campaign_path_rejected(self):
        with self.assertRaises(ValueError):self.store.read('../escape')

if __name__=='__main__':unittest.main()
