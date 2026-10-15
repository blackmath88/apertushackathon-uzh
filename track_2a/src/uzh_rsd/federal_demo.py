"""Offline discovery walkthrough. Every body is authored here; no network fallback exists."""
from .government_scout import FetchResponse, PROFILES

HOST = 'https://www.bfe.admin.ch'
DE, FR = PROFILES[0].seeds
IT, EN = HOST + '/it/esempio', HOST + '/en/example'
MEMBERS = {'de': DE, 'fr': FR, 'it': IT, 'en': EN}
COPY = {
    'de': ('Beispiel: Antrag', 'Die Frist beträgt 30 Tage.', 'Die Beratung ist kostenlos.'),
    'fr': ('Exemple : demande', 'Le délai est de 20 jours.', 'Les conseils sont gratuits.'),
    'it': ('Esempio: domanda', 'Il termine è di 30 giorni.', 'La consulenza è gratuita.'),
    'en': ('Example: application', 'The deadline is 30 days.', 'Advice is free.'),
}


def html(language):
    title, deadline, fee = COPY[language]
    alternates = ''.join(f'<link rel="alternate" hreflang="{lang}" href="{url}">' for lang, url in MEMBERS.items())
    return (f'<!doctype html><html lang="{language}"><head><meta charset="utf-8"><title>{title}</title>{alternates}</head>'
            f'<body><main><h1>{title}</h1><p>{deadline}</p><p>{fee}</p>'
            '<p>Project-authored demonstration. Not government content.</p></main></body></html>').encode()


def fetch(url, _profile, **_kwargs):
    """Return only this fixed fixture map. Unknown URLs cannot trigger external I/O."""
    if url == HOST + '/robots.txt':
        return FetchResponse(200, url, {'Content-Type': 'text/plain'},
                             ('User-agent: *\nDisallow:\nSitemap: ' + HOST + '/demo-sitemap.xml\n').encode())
    if url == HOST + '/demo-sitemap.xml':
        entries = ''.join(f'<url><loc>{u}</loc></url>' for u in MEMBERS.values())
        return FetchResponse(200, url, {'Content-Type': 'application/xml'}, ('<urlset>' + entries + '</urlset>').encode())
    for lang, member in MEMBERS.items():
        if url == member:
            return FetchResponse(200, url, {'Content-Type': 'text/html; charset=utf-8'}, html(lang))
    return FetchResponse(404, url, {'Content-Type': 'text/plain'}, b'Unknown authored fixture URL')


def configure(store):
    if store.inference:
        raise ValueError('Offline discovery demo requires inference disabled')
    for campaign in store.list():
        if any(not p['bundle'].get('fixture') for p in campaign['pairs']) or any(not r.get('fixture') for r in campaign.get('discovery_runs', [])):
            raise ValueError('Use a separate data directory for the offline discovery demo')
    store.discovery_fetcher = store.capture_fetcher = fetch
    store.capture_fixture = True
    store.discovery_delay = store.capture_delay = 0
    store.demo_discovery = True
