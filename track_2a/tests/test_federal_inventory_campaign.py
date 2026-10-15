import copy
import tempfile
import unittest
from unittest.mock import patch

from uzh_rsd import federal_inventory as inventory, federal_desk as desk
from uzh_rsd.campaign_center import Store


class InventoryCampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(self.tmp.name, {'model':'fixture','weight_hash':'a'*64,'runtime_revision':'test'})
        self.addCleanup(self.store.lease.close)

    def ready_campaign(self):
        c=self.store.create('Batch fixture',True)
        p=c['pairs'][0];p['status']='ready'
        p['bundle']['analysis']={'status':'not_run','candidates':[],'model_calls':0};desk.seal(p['bundle'])
        other=copy.deepcopy(p);other['id']='b'*32;other['title']='Second fixture'
        c['pairs'].append(other);self.store.write(c)
        return c

    def test_inventory_has_sourced_hierarchy_without_claiming_page_coverage(self):
        cat=inventory.inventory();sites=cat['sites'];ids={s['id'] for s in sites}
        self.assertEqual(len(sites),34);self.assertEqual(len(ids),34)
        self.assertEqual(sum(s['parent'] is None for s in sites),8)
        self.assertTrue(all(s['parent'] is None or s['parent'] in ids for s in sites))
        self.assertTrue(all(s['discovery_status']=='listed_not_crawled' and not s['languages_observed'] for s in sites))
        self.assertEqual(inventory.site_for_url('https://www.bfe.admin.ch/de/x'),'bfe')
        self.assertIsNone(inventory.site_for_url('https://www.bfe.admin.ch.evil.example/x'))

    def test_selection_validated_and_persistent(self):
        c=self.store.create('Energy',site_ids=['bfe','uvek'])
        self.store.scope(c['id'],['bfe','bafu'])
        self.assertEqual(self.store.read(c['id'])['scope']['site_ids'],['bafu','bfe'])
        for ids in [['unknown'],['bfe','bfe'],0,{'bfe':True}]:
            with self.assertRaises(ValueError):self.store.scope(c['id'],ids)

    def test_batch_is_serial_pinned_and_does_not_retry(self):
        c=self.ready_campaign();ids=[p['id'] for p in c['pairs']]
        with patch('threading.Thread.start'):
            started=self.store.batch(c['id'],ids)
        batch=started['batches'][0]
        self.assertTrue(self.store.batch_guard.exists())
        with self.assertRaises(ValueError):self.store.run(c['id'],ids[0])
        self.store.scope(c['id'],['bag'])  # Existing run scope must remain frozen.
        response={'choices':[{'finish_reason':'stop','message':{'content':'{"differences":[]}'}}]}
        with patch.object(desk,'local_transport',return_value=response) as transport:
            self.store.execute_batch(c['id'],batch['id'])
            self.assertEqual(transport.call_count,2)
        saved=self.store.read(c['id']);b=saved['batches'][0]
        self.assertEqual(b['scope']['site_ids'],['bfe']);self.assertEqual(b['status'],'complete')
        self.assertEqual(b['completed_pair_ids'],ids);self.assertIn('finished_at',b)
        self.assertTrue(all(p.get('started_at') and p.get('finished_at') for p in saved['pairs']))
        self.assertFalse(self.store.batch_guard.exists());self.assertFalse(self.store.guard.exists())
        with self.assertRaises(ValueError):self.store.batch(c['id'],ids)

    def test_batch_stops_on_uncertain_delivery_and_reserves_runtime(self):
        c=self.ready_campaign();ids=[p['id'] for p in c['pairs']]
        with patch('threading.Thread.start'):b=self.store.batch(c['id'],ids)['batches'][0]
        with patch.object(desk,'local_transport',side_effect=TimeoutError) as transport:
            self.store.execute_batch(c['id'],b['id']);transport.assert_called_once()
        saved=self.store.read(c['id'])
        self.assertEqual(saved['pairs'][0]['status'],'unsettled')
        self.assertEqual(saved['pairs'][1]['status'],'ready')
        self.assertEqual(saved['batches'][0]['status'],'stopped')
        self.assertTrue(self.store.guard.exists());self.assertTrue(self.store.batch_guard.exists())

    def test_batch_requires_scope_and_does_not_partially_start_invalid_selection(self):
        c=self.ready_campaign();ids=[p['id'] for p in c['pairs']]
        self.store.scope(c['id'],['bag'])
        with self.assertRaises(ValueError):self.store.batch(c['id'],ids)
        self.assertFalse(self.store.batch_guard.exists())
        self.assertFalse(self.store.read(c['id'])['batches'])

    def test_pattern_keeps_review_snapshot_without_activation(self):
        c=self.store.create('Pattern example',True);p=c['pairs'][0]
        data=dict(name='Deadlines',query='Frist délai termine deadline',rationale='Check numerical deadlines',author='Editor')
        with self.assertRaises(ValueError):self.store.pattern(c['id'],data)
        draft={'bundle_digest':p['bundle']['digest'],'reviews':[dict(candidate_id=p['bundle']['analysis']['candidates'][0]['id'],state='confirmed',reviewer='Editor',reason='Different numbers')]}
        self.store.review(c['id'],p['id'],draft)
        saved=self.store.pattern(c['id'],data);proposal=saved['patterns'][0]
        self.assertEqual(proposal['state'],'proposed_not_evaluated');self.assertTrue(proposal['detector_unchanged'])
        draft['reviews'][0]['state']='rejected';self.store.review(c['id'],p['id'],draft)
        saved=self.store.read(c['id']);self.assertEqual(saved['patterns'][0]['examples'][0]['review']['state'],'confirmed')
        self.assertTrue(saved['patterns'][0]['examples'][0]['fixture'])

    def test_restart_marks_batch_interrupted_without_replaying(self):
        c=self.ready_campaign()
        with patch('threading.Thread.start'):self.store.batch(c['id'],[c['pairs'][0]['id']])
        self.store.lease.close();other=Store(self.tmp.name);self.addCleanup(other.lease.close)
        self.assertEqual(other.read(c['id'])['batches'][0]['status'],'interrupted')
        self.assertTrue(other.batch_guard.exists())


if __name__=='__main__':unittest.main()
