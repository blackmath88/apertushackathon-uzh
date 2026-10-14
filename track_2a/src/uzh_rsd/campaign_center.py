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

from . import captures, discovery
from . import federal_desk as desk
from . import federal_inventory as inventory


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, root, inference=None, discovery_fetcher=None, capture_fetcher=None):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self.lease = (self.root / 'owner.lock').open('a')
        try:
            fcntl.flock(self.lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lease.close(); raise
        self.lock = threading.RLock(); self.inference = inference
        # No fetcher means no live discovery: reviewed-profile network use needs explicit authorisation.
        self.discovery_fetcher = discovery_fetcher; self.capture_fetcher = capture_fetcher; self.capture_fixture = False; self.capture_delay = 2.0; self.threads = []
        self.guard = self.root / 'unsettled-attempt.json'
        self.batch_guard = self.root / 'active-batch.json'
        # A process restart never silently retries an interrupted model request.
        for path in self.root.glob('campaign-*.json'):
            c = json.loads(path.read_text())
            changed = False
            for p in c['pairs']:
                if p['status'] == 'running':
                    p['status'] = 'interrupted'; changed = True
            for batch in c.get('batches', []):
                if batch['status'] == 'running':
                    batch['status'] = 'interrupted'; changed = True
            for run in c.get('discovery_runs', []):
                if run['state'] == 'running':
                    run['state'] = 'interrupted'; run['finished_at'] = now(); changed = True
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

    def create(self, name, demonstration=False, site_ids=None):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120: raise ValueError('Enter a campaign name (1–120 characters)')
        selected = inventory.validate_selection([] if site_ids is None else site_ids)
        with self.lock:
            c = {'schema': 'lost-in-switzerland/campaign/v1', 'id': uuid.uuid4().hex,
                 'name': name.strip(), 'created_at': now(), 'updated_at': now(), 'pairs': [], 'events': [],
                 'scope': {'catalogue_version': inventory.VERSION, 'site_ids': selected}, 'batches': []}
            self.event(c, 'Campaign created')
            if demonstration:
                c['scope']['site_ids'] = ['bfe']
                path = self.root / ('fixture-' + c['id']); desk.demo(path)
                b = json.loads((path / 'bundle.json').read_text())
                c['pairs'].append({'id': uuid.uuid4().hex, 'title': 'Application guidance · authored DE/FR example',
                    'bundle': b, 'status': 'complete', 'review': None})
                self.event(c, 'Authored demonstration loaded · zero model calls')
            self.write(c); return c

    def scope(self, cid, site_ids):
        selected = inventory.validate_selection(site_ids)
        with self.lock:
            c = self.read(cid)
            kept = [f for f in c['scope'].get('page_families', []) if f['site_id'] in selected]
            c['scope'] = {'catalogue_version': inventory.VERSION, 'site_ids': selected}
            if kept: c['scope']['page_families'] = kept
            self.event(c, 'Campaign scope saved: ' + str(len(selected)) + ' websites; no crawl started')
            self.write(c); return c

    # --- discovery (#35): preview -> explicit start -> progress -> selectable families -> saved scope ---
    def _site(self, c, site_id):
        if site_id not in c['scope']['site_ids']: raise ValueError('Site is not in this campaign scope')
        return site_id

    def discovery_preview(self, cid, site_id):
        with self.lock:
            return discovery.preview(self._site(self.read(cid), site_id))

    def discovery_start(self, cid, site_id, confirm):
        if confirm is not True: raise ValueError('Discovery starts only after explicit confirmation')
        with self.lock:
            c = self.read(cid); self._site(c, site_id)
            plan = discovery.preview(site_id)
            run = {'id': uuid.uuid4().hex, 'site_id': site_id, 'started_at': now(), 'progress': {}, 'snapshot_id': None, 'plan': plan}
            if not plan['eligible']:
                run.update(state='blocked', reason=plan['reason'], finished_at=now())
            elif not self.discovery_fetcher:
                run.update(state='blocked', reason='live_discovery_not_authorised', finished_at=now(),
                           detail='No authorised transport is connected; BFE content restrictions are preserved. Nothing was requested.')
            else:
                run['state'] = 'running'
            c.setdefault('discovery_runs', []).append(run)
            self.event(c, 'Discovery ' + run['state'] + ': ' + site_id); self.write(c)
            if run['state'] == 'running':
                t = threading.Thread(target=self._discover, args=(cid, run['id'], site_id), daemon=True)
                self.threads.append(t); t.start()
            return run

    def _update_run(self, cid, rid, **fields):
        with self.lock:
            c = self.read(cid)
            run = next(r for r in c['discovery_runs'] if r['id'] == rid)
            run.update(fields); c['updated_at'] = now(); self.write(c)

    def _discover(self, cid, rid, site_id):
        try:
            snap = discovery.discover(site_id, fetcher=self.discovery_fetcher, delay_seconds=self.discovery_delay,
                                      progress=lambda p: self._update_run(cid, rid, progress=p))
            (self.root / ('snapshot-' + snap['id'] + '.json')).write_text(json.dumps(snap, ensure_ascii=False))
            self._update_run(cid, rid, state='complete', snapshot_id=snap['id'], finished_at=now(),
                             stop_reason=snap['stop_reason'], summary={'families': len(snap['families']),
                             'candidates': len(snap['candidates']), 'unvisited': snap['unvisited_count']})
        except Exception as exc:
            self._update_run(cid, rid, state='failed', reason=type(exc).__name__, finished_at=now())

    discovery_delay = 2.0

    def snapshot(self, cid, sid):
        if not re.fullmatch('[a-f0-9]{32}', sid): raise ValueError('Unknown snapshot')
        with self.lock:
            c = self.read(cid)
            if not any(r.get('snapshot_id') == sid for r in c.get('discovery_runs', [])): raise ValueError('Unknown snapshot')
            return json.loads((self.root / ('snapshot-' + sid + '.json')).read_text())

    def page_scope(self, cid, selections):
        if not isinstance(selections, list) or len(selections) > 500: raise ValueError('Select page families as a list')
        saved = []
        with self.lock:
            c = self.read(cid)
            for item in selections:
                if not isinstance(item, dict): raise ValueError('Invalid page-family selection')
                snap = self.snapshot(cid, item.get('snapshot_id', ''))
                fam = next((f for f in snap['families'] if f['family_id'] == item.get('family_id')), None)
                if not fam: raise ValueError('Unknown page family')
                saved.append({'snapshot_id': snap['id'], 'site_id': snap['site_id'], 'family_id': fam['family_id'],
                              'observed_at': snap['observed_at'], 'status': fam['status'],
                              'language_availability': fam['language_availability']})
            if len({(x['snapshot_id'], x['family_id']) for x in saved}) != len(saved): raise ValueError('Duplicate page family')
            c['scope']['page_families'] = saved
            self.event(c, 'Page-family scope saved: ' + str(len(saved)) + ' families; no capture started')
            self.write(c); return c

    # --- captures (#36): selected family + certified pairing -> evidence bundle -> existing review flow ---
    def capture(self, cid, snapshot_id, family_id, pairing):
        if not isinstance(pairing, dict): raise ValueError('Pairing certification is required')
        with self.lock:
            c = self.read(cid)
            if not any(f['snapshot_id'] == snapshot_id and f['family_id'] == family_id for f in c['scope'].get('page_families', [])):
                raise ValueError('Page family is not in the saved campaign scope')
            snap = self.snapshot(cid, snapshot_id)
            if self.capture_fetcher is None and not self.capture_fixture:
                result = captures._blocked(['live_capture_not_authorised'], family_id=family_id, snapshot_id=snapshot_id, site_id=snap['site_id'])
            else:
                result = captures.capture_family(snap, family_id, pairing, fetcher=self.capture_fetcher, raw_dir=self.root / 'raw',
                                                 fixture=self.capture_fixture, delay_seconds=self.capture_delay)
            record = {'id': uuid.uuid4().hex, 'at': now(), 'snapshot_id': snapshot_id, 'family_id': family_id, 'status': result['status'],
                      'blockers': result['blockers'], 'requests': result['requests'], 'pair_id': None,
                      'evidence': result.get('evidence'), 'model_calls': 0}
            if result['status'] == 'captured':
                b = result['bundle']
                if any(p['bundle']['digest'] == b['digest'] for p in c['pairs']): raise ValueError('This capture already belongs to the campaign')
                if len(c['pairs']) >= 20: raise ValueError('Campaign limit: 20 page pairs')
                pid = uuid.uuid4().hex
                c['pairs'].append({'id': pid, 'title': 'Captured family ' + family_id, 'bundle': b, 'status': 'ready', 'review': None})
                record['pair_id'] = pid
            c.setdefault('captures', []).append(record)
            self.event(c, 'Capture ' + result['status'] + ': family ' + family_id + '; zero model calls'); self.write(c)
            return record

    def preparation(self, cid):
        """Per saved family: state, blockers, completeness and the two kinds of links (live vs captured)."""
        with self.lock:
            c = self.read(cid); out = []
            for f in c['scope'].get('page_families', []):
                last = next((r for r in reversed(c.get('captures', [])) if r['family_id'] == f['family_id'] and r['snapshot_id'] == f['snapshot_id']), None)
                ev = (last or {}).get('evidence') or {}
                out.append({**f, 'capture_status': last['status'] if last else 'not_captured', 'blockers': last['blockers'] if last else [],
                            'pair_id': last['pair_id'] if last else None,
                            'omission_confirmation': ev.get('omission_confirmation'),
                            'live_originals': {k: v['live_original'] for k, v in ev.get('links', {}).items()},
                            'captured_evidence': {k: {'content_address': v['captured_evidence'], 'retrieved_at_utc': v['retrieved_at_utc']}
                                                  for k, v in ev.get('links', {}).items()},
                            'completeness': {k: v.get('completeness') for k, v in ev.get('extraction', {}).items()}})
            return out

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

    def pattern(self, cid, data):
        """Save a review-backed search hypothesis; never activate or tune a detector."""
        for key in ('name','query','rationale','author'):
            if not isinstance(data.get(key),str) or not 1<=len(data[key].strip())<=1000:
                raise ValueError('Pattern name, query, rationale and author are required (max 1000 characters each)')
        with self.lock:
            c=self.read(cid); examples=[]
            for p in c['pairs']:
                for r in (p.get('review') or {}).get('reviews',[]):
                    if r['state'] in {'confirmed','rejected'}:
                        examples.append({'pair':p['id'],'candidate':r['candidate_id'],
                                         'bundle_digest':p['bundle']['digest'], 'review':r,
                                         'reviewed_at':p['review']['reviewed_at'], 'fixture':p['bundle']['fixture']})
            if not examples: raise ValueError('Save at least one confirmed or rejected review first')
            proposal={k:data[k].strip() for k in ('name','query','rationale','author')}
            proposal.update(id=uuid.uuid4().hex,created_at=now(),state='proposed_not_evaluated',
                            version=1,examples=examples,detector_unchanged=True)
            c.setdefault('patterns',[]).append(proposal)
            self.event(c,'Search hypothesis saved, not activated: '+proposal['name']);self.write(c);return c

    def run(self, cid, pid, batch_id=None):
        with self.lock:
            if not self.inference: raise ValueError('Inference disabled. Start the server with the explicit local inference configuration after the baseline has settled.')
            if self.batch_guard.exists() and (batch_id is None or json.loads(self.batch_guard.read_text())['id'] != batch_id):
                raise ValueError('A batch owns local inference. Inspect its dated run record before starting another.')
            if self.guard.exists(): raise ValueError('An active or unsettled attempt owns local inference. Inspect its record before any further request.')
            c = self.read(cid); p = self.pair(c, pid)
            if p['status'] != 'ready': raise ValueError('This pair is not eligible for a new attempt')
            run_id = uuid.uuid4().hex
            desk.save(self.guard, {'campaign': cid, 'pair': pid, 'run': run_id, 'started_at': now()})
            p['status'] = 'running'; p['run_id'] = run_id; p['started_at'] = now()
            self.event(c, 'Comparison started: ' + p['title']); self.write(c)
            if batch_id is None:
                threading.Thread(target=self.execute, args=(cid,pid,run_id), daemon=True).start()
            return c

    def batch(self, cid, pair_ids):
        with self.lock:
            if not self.inference: raise ValueError('Local inference is disabled')
            if self.guard.exists() or self.batch_guard.exists(): raise ValueError('Inference already reserved')
            if not isinstance(pair_ids,list) or not pair_ids or not all(isinstance(i,str) for i in pair_ids) or len(set(pair_ids))!=len(pair_ids):
                raise ValueError('Select distinct ready page pairs')
            c=self.read(cid); pairs=[self.pair(c,pid) for pid in pair_ids]
            if any(p['status']!='ready' for p in pairs): raise ValueError('Every selected pair must be ready')
            selected=c.get('scope',{}).get('site_ids',[])
            if any(inventory.site_for_url(p['bundle']['left']['source_url']) not in selected for p in pairs):
                raise ValueError('Add the source website to campaign scope before running a batch')
            batch={'id':uuid.uuid4().hex,'started_at':now(),'status':'running','pair_ids':pair_ids,
                   'capture_digests':{p['id']:p['bundle']['digest'] for p in pairs},
                   'scope':c['scope'].copy(),'method':desk.METHOD,'runtime':self.inference.copy(),
                   'completed_pair_ids':[], 'max_model_calls':len(pairs)}
            desk.save(self.batch_guard, {'id':batch['id'],'campaign':cid})
            c.setdefault('batches',[]).append(batch)
            self.event(c,'Batch started: '+str(len(pairs))+' selected page pairs');self.write(c)
            threading.Thread(target=self.execute_batch,args=(cid,batch['id']),daemon=True).start()
            return c

    def execute_batch(self,cid,bid):
        status='complete'
        try:
            with self.lock:
                batch=next(b for b in self.read(cid)['batches'] if b['id']==bid)
            for pid in batch['pair_ids']:
                c=self.run(cid,pid,batch_id=bid)
                self.execute(cid,pid,self.pair(c,pid)['run_id'])
                with self.lock:
                    c=self.read(cid); current=next(b for b in c['batches'] if b['id']==bid)
                    current['completed_pair_ids'].append(pid);self.write(c)
                    if self.pair(c,pid)['status']!='complete':
                        status='stopped';break
        except Exception:
            status='stopped'
        finally:
            with self.lock:
                c=self.read(cid); current=next(b for b in c['batches'] if b['id']==bid)
                current['status']=status;current['finished_at']=now()
                self.event(c,'Batch '+status+'; no automatic retry');self.write(c)
                if not self.guard.exists(): self.batch_guard.unlink(missing_ok=True)

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
            p['finished_at'] = now()
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
                    return self.send({'campaigns':store.list(),'catalogue':inventory.inventory(),
                                      'inference_enabled':bool(store.inference), 'unsettled':store.guard.exists() or store.batch_guard.exists()})
                match=re.fullmatch('/api/campaigns/([a-f0-9]{32})/snapshots/([a-f0-9]{32})',path)
                if match: return self.send(store.snapshot(match[1],match[2]))
                match=re.fullmatch('/api/campaigns/([a-f0-9]{32})/preparation',path)
                if match: return self.send({'families':store.preparation(match[1])})
                match=re.fullmatch('/desk/([a-f0-9]{32})/([a-f0-9]{32})',path)
                if match:
                    with store.lock:
                        p=store.pair(store.read(match[1]),match[2]); html=desk.render(p['bundle'])
                    bridge="""<script>
try{if(!localStorage.getItem(key)){for(const r of SAVED_REVIEWS)drafts[r.candidate_id]=r;render();updateProgress()}}catch(e){}
const save=document.createElement('button');save.textContent='Save review to campaign';save.className='primary';document.querySelector('.buttons').prepend(save);
save.onclick=()=>parent.postMessage({type:'federal-review',campaign:'CID',pair:'PID',draft:{bundle_digest:b.digest,reviews:Object.values(drafts).filter(r=>r.reviewer.trim()||r.reason.trim()||r.state!=='unresolved')}},location.origin);
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
                if not isinstance(data,dict): raise ValueError('Request must be a JSON object')
                if self.path=='/api/campaigns': return self.send(store.create(data['name'],data.get('demo') is True,data.get('site_ids')),201)
                match=re.fullmatch('/api/campaigns/([a-f0-9]{32})/(pairs|run|review|scope|batch|pattern|discovery-preview|discovery-start|page-scope|capture)',self.path)
                if not match: return self.send({'error':'Not found'},404)
                cid,action=match.groups()
                if action=='pairs': result=store.add(cid,data)
                elif action=='run': result=store.run(cid,data['pair'])
                elif action=='scope': result=store.scope(cid,data['site_ids'])
                elif action=='discovery-preview': result=store.discovery_preview(cid,data['site_id'])
                elif action=='discovery-start': result=store.discovery_start(cid,data['site_id'],data.get('confirm'))
                elif action=='page-scope': result=store.page_scope(cid,data['families'])
                elif action=='capture': result=store.capture(cid,data['snapshot_id'],data['family_id'],data.get('pairing'))
                elif action=='batch': result=store.batch(cid,data['pairs'])
                elif action=='pattern': result=store.pattern(cid,data)
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
