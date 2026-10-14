"""Local, durable federal campaign workspace. Inference is explicitly opt-in."""
import argparse
import fcntl
import json
import re
import secrets
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import federal_desk as desk


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, root, inference=None):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self.lease = (self.root / 'owner.lock').open('a')
        try:
            fcntl.flock(self.lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lease.close(); raise
        self.lock = threading.RLock(); self.inference = inference
        self.guard = self.root / 'unsettled-attempt.json'
        # A process restart never silently retries an interrupted model request.
        for path in self.root.glob('campaign-*.json'):
            c = json.loads(path.read_text())
            changed = False
            for p in c['pairs']:
                if p['status'] == 'running':
                    p['status'] = 'interrupted'; changed = True
            if changed: self.write(c)

    def write(self, c):
        path = self.root / ('campaign-' + c['id'] + '.json')
        tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(c, ensure_ascii=False))
        tmp.replace(path)

    def read(self, cid):
        if not re.fullmatch('[a-f0-9]{32}', cid): raise ValueError('Unknown campaign')
        return json.loads((self.root / ('campaign-' + cid + '.json')).read_text())

    def list(self):
        with self.lock:
            return [json.loads(p.read_text()) for p in sorted(self.root.glob('campaign-*.json'))]

    def event(self, c, message):
        c['events'].append({'at': now(), 'message': message}); c['updated_at'] = now()

    def create(self, name, demonstration=False):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120: raise ValueError('Enter a campaign name (1–120 characters)')
        with self.lock:
            c = {'schema': 'lost-in-switzerland/campaign/v1', 'id': uuid.uuid4().hex,
                 'name': name.strip(), 'created_at': now(), 'updated_at': now(), 'pairs': [], 'events': []}
            self.event(c, 'Campaign created')
            if demonstration:
                path = self.root / ('fixture-' + c['id']); desk.demo(path)
                b = json.loads((path / 'bundle.json').read_text())
                c['pairs'].append({'id': uuid.uuid4().hex, 'title': 'Application guidance · authored DE/FR example',
                    'bundle': b, 'status': 'complete', 'review': None})
                self.event(c, 'Authored demonstration loaded · zero model calls')
            self.write(c); return c

    def pair(self, c, pid):
        return next(p for p in c['pairs'] if p['id'] == pid)

    def add(self, cid, data):
        if not isinstance(data, dict) or not all(isinstance(data.get(k), str) for k in ('left_html', 'right_html', 'title')) or not isinstance(data.get('metadata'), dict):
            raise ValueError('HTML, title and source metadata are required')
        b = desk.prepare(data['left_html'].encode(), data['right_html'].encode(), data['metadata'])
        with self.lock:
            c = self.read(cid)
            if len(c['pairs']) >= 20: raise ValueError('Campaign limit: 20 page pairs')
            if any(p['bundle']['digest'] == b['digest'] for p in c['pairs']): raise ValueError('This capture already belongs to the campaign')
            title = data.get('title', '').strip()
            if not 1 <= len(title) <= 150: raise ValueError('Enter a page title (1–150 characters)')
            c['pairs'].append({'id': uuid.uuid4().hex, 'title': title, 'bundle': b, 'status': 'ready', 'review': None})
            self.event(c, 'Page pair imported: ' + title); self.write(c); return c

    def review(self, cid, pid, draft):
        with self.lock:
            c = self.read(cid); p = self.pair(c, pid)
            result = desk.review(p['bundle'], draft)
            # Keep each accepted review revision as an immutable artifact.
            artifact = self.root / ('review-' + uuid.uuid4().hex + '.json'); desk.save(artifact, result)
            p['review'] = result
            self.event(c, 'Review saved: ' + p['title']); self.write(c); return c

    def run(self, cid, pid):
        with self.lock:
            if not self.inference: raise ValueError('Inference disabled. Start the server with the explicit local inference configuration after the baseline has settled.')
            if self.guard.exists(): raise ValueError('An active or unsettled attempt owns local inference. Inspect its record before any further request.')
            c = self.read(cid); p = self.pair(c, pid)
            if p['status'] != 'ready': raise ValueError('This pair is not eligible for a new attempt')
            run_id = uuid.uuid4().hex
            desk.save(self.guard, {'campaign': cid, 'pair': pid, 'run': run_id, 'started_at': now()})
            p['status'] = 'running'; p['run_id'] = run_id
            self.event(c, 'Comparison started: ' + p['title']); self.write(c)
            threading.Thread(target=self.execute, args=(cid,pid,run_id), daemon=True).start()
            return c

    def execute(self, cid, pid, run_id):
        result = None
        try:
            with self.lock: b = self.pair(self.read(cid),pid)['bundle']
            result = desk.analyze(b, **self.inference, out=self.root / ('run-' + run_id))
        except Exception:
            pass  # Keep guard and explicit unsettled state; never retry uncertain delivery.
        with self.lock:
            c = self.read(cid); p = self.pair(c,pid)
            if result:
                p['bundle'] = result
                p['status'] = result['analysis']['status']
                if result['analysis'].get('model_calls') == 1:
                    self.guard.unlink()
                else:
                    p['status'] = 'unsettled'
            else: p['status'] = 'unsettled'
            self.event(c, 'Comparison ' + p['status'] + ': ' + p['title']); self.write(c)


def handler(store, token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def send(self, value, status=200, kind='application/json'):
            raw = (json.dumps(value, ensure_ascii=False) if kind=='application/json' else value).encode()
            self.send_response(status); self.send_header('Content-Type',kind+'; charset=utf-8')
            self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store')
            self.send_header('X-Frame-Options','SAMEORIGIN'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer')
            self.end_headers(); self.wfile.write(raw)
        def allowed(self):
            return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        def do_GET(self):
            if not self.allowed(): return self.send({'error':'Local host required'},403)
            try:
                path = urlparse(self.path).path
                if path == '/':
                    html=Path(__file__).with_name('campaign_center.html').read_text().replace('__SESSION_TOKEN__',token)
                    return self.send(html,kind='text/html')
                if path == '/api/campaigns':
                    return self.send({'campaigns':store.list(),'inference_enabled':bool(store.inference), 'unsettled':store.guard.exists()})
                match=re.fullmatch('/desk/([a-f0-9]{32})/([a-f0-9]{32})',path)
                if match:
                    with store.lock:
                        p=store.pair(store.read(match[1]),match[2]); html=desk.render(p['bundle'])
                    bridge="""<script>
try{if(!localStorage.getItem(key)){for(const r of SAVED_REVIEWS)drafts[r.candidate_id]=r;render();updateProgress()}}catch(e){}
const save=document.createElement('button');save.textContent='Save review to campaign';save.className='primary';document.querySelector('.buttons').prepend(save);
save.onclick=()=>parent.postMessage({type:'federal-review',campaign:'CID',pair:'PID',draft:{bundle_digest:b.digest,reviews:Object.values(drafts)}},location.origin);
addEventListener('message',e=>{if(e.origin===location.origin&&e.source===parent&&e.data.type==='review-result')document.querySelector('#export-status').textContent=e.data.message});
</script>""".replace('CID',match[1]).replace('PID',match[2]).replace('SAVED_REVIEWS', json.dumps((p.get('review') or {}).get('reviews',[]), ensure_ascii=False).replace('<', '\\u003c'))
                    return self.send(html.replace('</body>',bridge+'</body>'),kind='text/html')
                return self.send({'error':'Not found'},404)
            except (ValueError,KeyError,StopIteration,FileNotFoundError): return self.send({'error':'Campaign or pair unavailable'},404)
        def do_POST(self):
            origin=self.headers.get('Origin')
            if not self.allowed() or self.headers.get('X-Campaign-Token') != token or (origin and origin != 'http://'+self.headers['Host']):
                return self.send({'error':'Local session required'},403)
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 3_000_000: raise ValueError('Request size must be below 3 MB')
                data=json.loads(self.rfile.read(length))
                if self.path=='/api/campaigns': return self.send(store.create(data['name'],data.get('demo') is True),201)
                match=re.fullmatch('/api/campaigns/([a-f0-9]{32})/(pairs|run|review)',self.path)
                if not match: return self.send({'error':'Not found'},404)
                cid,action=match.groups()
                if action=='pairs': result=store.add(cid,data)
                elif action=='run': result=store.run(cid,data['pair'])
                else: result=store.review(cid,data['pair'],data['draft'])
                self.send(result)
            except (ValueError,KeyError,TypeError,StopIteration,FileNotFoundError) as exc:
                self.send({'error':str(exc) if isinstance(exc,ValueError) else 'Invalid campaign input'},400)
    return Handler


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',required=True);p.add_argument('--port',type=int,default=8766)
    p.add_argument('--enable-inference',action='store_true');p.add_argument('--model');p.add_argument('--weight-hash');p.add_argument('--runtime-revision')
    a=p.parse_args(); config=None
    if a.enable_inference:
        if not a.model or not a.runtime_revision or not re.fullmatch('[a-f0-9]{64}',a.weight_hash or ''): p.error('Explicit model, weight hash and runtime revision required')
        config={'model':a.model,'weight_hash':a.weight_hash,'runtime_revision':a.runtime_revision}
    store=Store(a.data,config); server=ThreadingHTTPServer(('127.0.0.1',a.port),handler(store,secrets.token_urlsafe(32)))
    print(f'Federal campaign center: http://127.0.0.1:{server.server_port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close();store.lease.close()

if __name__=='__main__': main()
