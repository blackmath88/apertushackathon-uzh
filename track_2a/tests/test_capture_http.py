"""Real local HTTP acceptance flow; every discovery/capture response is authored in this file."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from uzh_rsd.campaign_center import Store, handler
from uzh_rsd.government_scout import FetchResponse, PROFILES
from http.server import ThreadingHTTPServer

H = 'https://www.bfe.admin.ch'
DE, FR = PROFILES[0].seeds
PAGES = {
    DE: f'<html><head><link rel="alternate" hreflang="fr" href="{FR}"></head><body><main><h1>Antrag</h1><p>Frist: 30 Tage</p></main></body></html>'.encode(),
    FR: f'<html><head><link rel="alternate" hreflang="de" href="{DE}"></head><body><main><h1>Demande</h1><p>Délai: 20 jours</p></main></body></html>'.encode(),
}


class CaptureHTTPTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.calls = []
        def fetch(url, _profile, **_kwargs):
            self.calls.append(url)
            if url == H + '/robots.txt':
                return FetchResponse(200, url, {'Content-Type': 'text/plain'}, b'User-agent: *\nDisallow:\n')
            return FetchResponse(200, url, {'Content-Type': 'text/html'}, PAGES[url])
        self.store = Store(self.tmp.name, discovery_fetcher=fetch, capture_fetcher=fetch)
        self.addCleanup(self.store.lease.close)
        self.store.capture_fixture = True
        self.store.capture_delay = 0
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), handler(self.store, 'fixture-token'))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        for thread in self.store.threads:
            thread.join(timeout=5)

    def request(self, path, data=None, token='fixture-token'):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        try:
            headers = {'X-Campaign-Token': token}
            conn.request('GET' if data is None else 'POST', path, json.dumps(data) if data is not None else None, headers)
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def api(self, path, data=None):
        status, _, body = self.request(path, data)
        self.assertIn(status, (200, 201), body)
        return json.loads(body)

    def captured_pair(self):
        campaign = self.api('/api/campaigns', {'name': 'HTTP fixture acceptance', 'site_ids': ['bfe']})
        cid = campaign['id']; base = '/api/campaigns/' + cid
        run = self.api(base + '/discovery-start', {'site_id': 'bfe', 'confirm': True})
        for thread in self.store.threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        saved = self.store.read(cid)
        discovery_run = saved['discovery_runs'][-1]
        self.assertEqual(discovery_run['state'], 'complete')
        snap = self.api(base + '/snapshots/' + discovery_run['snapshot_id'])
        family = next(f for f in snap['families'] if f['languages']['de'] and f['languages']['fr'])
        selection = {'snapshot_id': snap['id'], 'family_id': family['family_id']}
        self.api(base + '/page-scope', {'families': [selection]})
        pairing = {'left_language': 'de', 'right_language': 'fr', 'certified': True,
                   'reviewer': 'Fixture reviewer', 'pairing_rationale': 'Authored reciprocal hreflang',
                   'rights_basis': 'Project-authored fixture'}
        before = len(self.calls)
        blocked = self.api(base + '/capture', {**selection, 'pairing': {**pairing, 'certified': False}})
        self.assertEqual(blocked['status'], 'blocked')
        self.assertEqual(len(self.calls), before)
        result = self.api(base + '/capture', {**selection, 'pairing': pairing})
        self.assertEqual(result['status'], 'captured')
        self.assertEqual(result['model_calls'], 0)
        prep = self.api(base + '/preparation')['families'][0]
        self.assertEqual(prep['capture_status'], 'captured')
        self.assertEqual(prep['pair_id'], result['pair_id'])
        return cid, result['pair_id']

    def test_discover_select_capture_download_and_disabled_inference(self):
        cid, pid = self.captured_pair()
        prefix = f'/api/campaigns/{cid}/pairs/{pid}/evidence/'
        for side, url in [('left', DE), ('right', FR)]:
            status, headers, body = self.request(prefix + side)
            self.assertEqual(status, 200)
            self.assertEqual(body, PAGES[url])
            self.assertEqual(headers['Content-Type'], 'application/octet-stream')
            self.assertTrue(headers['Content-Disposition'].startswith('attachment;'))
            self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
            self.assertIn('sandbox', headers['Content-Security-Policy'])
        status, _, _ = self.request(f'/api/campaigns/{cid}/run', {'pair': pid})
        self.assertEqual(status, 400)  # baseline stays protected
        self.assertEqual(self.store.read(cid)['pairs'][0]['status'], 'ready')
        state = self.api('/api/campaigns')
        self.assertFalse(state['inference_enabled'])
        self.assertEqual(state['campaigns'][0]['pairs'][0]['id'], pid)
        self.assertEqual(self.request('/api/campaigns', {'name': 'unauthorised'}, token='bad')[0], 403)

    def test_download_rejects_tampering_foreign_pair_and_path_traversal(self):
        cid, pid = self.captured_pair()
        prefix = f'/api/campaigns/{cid}/pairs/{pid}/evidence/'
        other = self.api('/api/campaigns', {'name': 'Unrelated campaign'})
        self.assertEqual(self.request(f'/api/campaigns/{other["id"]}/pairs/{pid}/evidence/left')[0], 404)
        self.assertEqual(self.request(prefix + '../../owner.lock')[0], 404)
        bundle = self.store.read(cid)['pairs'][0]['bundle']
        digest = bundle['left']['sha256_html']
        path = Path(self.tmp.name) / 'raw' / 'sha256' / digest[:2] / (digest + '.html')
        path.write_bytes(b'tampered')
        self.assertEqual(self.request(prefix + 'left')[0], 404)
        path.unlink()
        path.symlink_to(Path(self.tmp.name) / 'owner.lock')
        self.assertEqual(self.request(prefix + 'left')[0], 404)


if __name__ == '__main__':
    unittest.main()
