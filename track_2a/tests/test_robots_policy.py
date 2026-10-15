"""No external I/O: exercise the real guarded transport against an authored HTTP opener."""
import io
import tempfile
import unittest
from unittest.mock import patch
from urllib.robotparser import RobotFileParser
from uzh_rsd import captures, discovery, government_scout as gs
from uzh_rsd.discovery_transport import Budgets, DiscoveryStore, GuardedTransport, Purpose, RequestLedger
from uzh_rsd.robots_policy import RobotsDenied, RobotsPolicy

H = 'https://www.bfe.admin.ch'
DE, FR = gs.PROFILES[0].seeds
ROBOT = H + '/robots.txt'
ALLOW = b'User-agent: *\nDisallow:\n'
HTML = b'<main><h1>Authored fixture</h1><p>30 days</p></main>'

class Response(io.BytesIO):
    def __init__(self, status, body, headers=None):
        super().__init__(body)
        self.status, self.headers = status, headers or {'Content-Type': 'text/html'}

class Opener:
    def __init__(self, pages):
        self.pages, self.urls = pages, []
    def open(self, request, timeout):
        self.urls.append(request.full_url)
        return Response(*self.pages[request.full_url])

def public(*args, **kwargs):
    return [(None, None, None, None, ('8.8.8.8', 443))]

def rule(body):
    result = RobotFileParser()
    result.parse(body.decode().splitlines())
    return result

def snapshot():
    return {'id':'a'*32, 'site_id':'bfe', 'families':[{'family_id':'f', 'status':'one_directional',
        'languages':{'de':[{'url':DE}], 'fr':[{'url':FR}], 'it':[], 'en':[]}, 'edges':[],
        'language_availability':{'de':'observed','fr':'observed','it':'not_observed','en':'not_observed'}}]}

PAIR = {'left_language':'de','right_language':'fr','certified':True,'reviewer':'Fixture',
        'pairing_rationale':'Authored test','rights_basis':'Project-authored content','content_use_permitted':True}

class RobotsPolicyTest(unittest.TestCase):
    def test_redirect_is_denied_before_dispatch_and_does_not_consume_attempt(self):
        opener = Opener({DE:(302,b'',{'Location':'/private'})})
        with DiscoveryStore() as store:
            ledger = RequestLedger(store,'r',Budgets(),delay_seconds=0)
            transport = GuardedTransport(ledger,gs._scope_check(gs.PROFILES[0]),resolver=public,opener_factory=lambda:opener)
            policy = RobotsPolicy({'www.bfe.admin.ch':rule(b'User-agent: *\nDisallow: /private\n')})
            transport.request_policy = policy
            with self.assertRaises(RobotsDenied) as cm:
                transport.fetch(DE)
            self.assertEqual(cm.exception.reason,'robots_disallow')
            self.assertEqual(opener.urls,[DE])
            self.assertEqual(ledger.total,1)
            self.assertEqual(policy.decisions[-1]['url'],H+'/private')
            self.assertFalse(policy.decisions[-1]['allowed'])

    def test_unknown_host_never_inherits_another_hosts_rules(self):
        policy=RobotsPolicy({'a.admin.ch':rule(ALLOW)})
        with self.assertRaises(RobotsDenied) as cm:
            policy('https://b.admin.ch/content',Purpose.HTML)
        self.assertEqual(cm.exception.reason,'robots_unavailable')
        policy('https://b.admin.ch/robots.txt',Purpose.ROBOTS)

    def test_scout_marks_redirect_policy_denial_as_blocked(self):
        opener=Opener({ROBOT:(200,b'User-agent: *\nDisallow: /private\n'),DE:(302,b'',{'Location':'/private'})})
        with patch.object(gs,'build_opener',return_value=opener), patch('uzh_rsd.discovery_transport.time.sleep'):
            result=gs.scout('bfe',seeds=[DE],resolver=public)
        self.assertEqual(opener.urls,[ROBOT,DE])
        self.assertEqual(result['frontier']['counts']['blocked'],1)
        self.assertEqual(result['frontier']['entries'][0]['reason'],'robots_disallow')
        self.assertFalse(result['policy_decisions'][-1]['allowed'])

    def test_inventory_checks_redirects_too(self):
        opener=Opener({ROBOT:(200,b'User-agent: *\nDisallow: /private\n'),DE:(302,b'',{'Location':'/private'}),FR:(200,HTML)})
        with patch('uzh_rsd.discovery_transport.build_guarded_opener',return_value=opener):
            result=discovery.discover('bfe',resolver=public,delay_seconds=0)
        self.assertNotIn(H+'/private',opener.urls)
        entry=next(c for c in result['candidates'] if c['url']==DE)
        self.assertEqual((entry['state'],entry['reason']),('blocked','robots_disallow'))

    def capture(self,pages):
        opener=Opener(pages)
        with tempfile.TemporaryDirectory() as d, patch('uzh_rsd.discovery_transport.build_guarded_opener',return_value=opener):
            result=captures.capture_family(snapshot(),'f',PAIR,raw_dir=d,fixture=False,resolver=public,delay_seconds=0)
        return result,opener.urls

    def test_capture_robots_failure_refuses_all_content(self):
        result,urls=self.capture({ROBOT:(503,b'Unavailable')})
        self.assertEqual(urls,[ROBOT])
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['blockers'],['robots_unavailable'])
        self.assertEqual(result['requests'],1)
        self.assertEqual(result['evidence']['robots'][0]['state'],'ROBOTS_UNAVAILABLE')

    def test_capture_checks_both_sides_before_fetching_either(self):
        result,urls=self.capture({ROBOT:(200,('User-agent: *\nDisallow: '+FR.removeprefix(H)+'\n').encode())})
        self.assertEqual(urls,[ROBOT])
        self.assertEqual(result['blockers'],['robots_disallow'])

    def test_capture_success_records_policy_and_shared_budget(self):
        result,urls=self.capture({ROBOT:(200,ALLOW),DE:(200,HTML),FR:(200,HTML)})
        self.assertEqual(result['status'],'captured')
        self.assertEqual(urls,[ROBOT,DE,FR])
        self.assertEqual(result['requests'],3)
        self.assertEqual(result['evidence']['accounting']['page_attempts'],2)
        self.assertEqual(result['evidence']['robots_mode'],'per_host_fail_closed')
        self.assertTrue(all(d['allowed'] for d in result['evidence']['policy_decisions']))

    def test_capture_redirect_cannot_bypass_policy(self):
        result,urls=self.capture({ROBOT:(200,b'User-agent: *\nDisallow: /private\n'),DE:(302,b'',{'Location':'/private'}),FR:(200,HTML)})
        self.assertNotIn(H+'/private',urls)
        self.assertEqual(result['status'],'failed')
        self.assertIn('robots_disallow:left',result['blockers'])
        self.assertEqual(result['evidence']['retrievals']['left']['state'],'blocked')

    def test_legacy_fetcher_cannot_be_used_as_live_capture_transport(self):
        with tempfile.TemporaryDirectory() as d, patch.object(captures,'LegacyFetcherTransport') as adapter:
            result=captures.capture_family(snapshot(),'f',PAIR,raw_dir=d,fixture=False,fetcher=lambda *_:None)
        self.assertEqual(result['blockers'],['legacy_fetcher_fixture_only'])
        adapter.assert_not_called()

if __name__=='__main__':unittest.main()
