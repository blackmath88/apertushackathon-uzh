"""Source-backed seed inventory, not a claim of crawled page coverage."""
from urllib.parse import urlsplit

VERSION = 'federal-directory-2026-10-14-v1'
SOURCE = 'https://www.stelle.admin.ch/en/organization-federal-administration'
DEPARTMENTS = (
    ('eda', 'FDFA · Foreign Affairs', 'www.eda.admin.ch'),
    ('edi', 'FDHA · Home Affairs', 'www.edi.admin.ch'),
    ('ejpd', 'FDJP · Justice and Police', 'www.ejpd.admin.ch'),
    ('vbs', 'DDPS · Defence, Civil Protection and Sport', 'www.vbs.admin.ch'),
    ('efd', 'FDF · Finance', 'www.efd.admin.ch'),
    ('wbf', 'EAER · Economic Affairs, Education and Research', 'www.wbf.admin.ch'),
    ('uvek', 'DETEC · Environment, Transport, Energy and Communications', 'www.uvek.admin.ch'),
    ('bk', 'FCh · Federal Chancellery', 'www.bk.admin.ch'),
)
# Selected units listed by the official directory. Domains are website identities;
# ownership of individual pages and availability of language versions remain unverified.
UNITS = (
    ('deza', 'eda', 'Swiss Agency for Development and Cooperation', 'www.deza.eda.admin.ch'),
    ('bag', 'edi', 'Federal Office of Public Health', 'www.bag.admin.ch'),
    ('bsv', 'edi', 'Federal Social Insurance Office', 'www.bsv.admin.ch'),
    ('bfs', 'edi', 'Federal Statistical Office', 'www.bfs.admin.ch'),
    ('blv', 'edi', 'Federal Food Safety and Veterinary Office', 'www.blv.admin.ch'),
    ('bak', 'edi', 'Federal Office of Culture', 'www.bak.admin.ch'),
    ('ebg', 'edi', 'Federal Office for Gender Equality', 'www.ebg.admin.ch'),
    ('bj', 'ejpd', 'Federal Office of Justice', 'www.bj.admin.ch'),
    ('fedpol', 'ejpd', 'Federal Office of Police', 'www.fedpol.admin.ch'),
    ('swisstopo', 'vbs', 'Federal Office of Topography', 'www.swisstopo.admin.ch'),
    ('babs', 'vbs', 'Federal Office for Civil Protection', 'www.babs.admin.ch'),
    ('baspo', 'vbs', 'Federal Office of Sport', 'www.baspo.admin.ch'),
    ('estv', 'efd', 'Federal Tax Administration', 'www.estv.admin.ch'),
    ('bazg', 'efd', 'Federal Office for Customs and Border Security', 'www.bazg.admin.ch'),
    ('efv', 'efd', 'Federal Finance Administration', 'www.efv.admin.ch'),
    ('bbl', 'efd', 'Federal Office for Buildings and Logistics', 'www.bbl.admin.ch'),
    ('sbfi', 'wbf', 'State Secretariat for Education, Research and Innovation', 'www.sbfi.admin.ch'),
    ('blw', 'wbf', 'Federal Office for Agriculture', 'www.blw.admin.ch'),
    ('bwo', 'wbf', 'Federal Office for Housing', 'www.bwo.admin.ch'),
    ('bwl', 'wbf', 'Federal Office for National Economic Supply', 'www.bwl.admin.ch'),
    ('bfe', 'uvek', 'Swiss Federal Office of Energy', 'www.bfe.admin.ch'),
    ('bafu', 'uvek', 'Federal Office for the Environment', 'www.bafu.admin.ch'),
    ('astra', 'uvek', 'Federal Roads Office', 'www.astra.admin.ch'),
    ('bazl', 'uvek', 'Federal Office of Civil Aviation', 'www.bazl.admin.ch'),
    ('are', 'uvek', 'Federal Office for Spatial Development', 'www.are.admin.ch'),
    ('bakom', 'uvek', 'Federal Office of Communications', 'www.bakom.admin.ch'),
)


def inventory():
    sites = [dict(id=i, parent=None, name=n, host=h, kind='chancellery' if i=='bk' else 'department')
             for i,n,h in DEPARTMENTS]
    sites += [dict(id=i, parent=p, name=n, host=h, kind='administrative_unit') for i,p,n,h in UNITS]
    for site in sites:
        site.update(url='https://' + site['host'] + '/', source_url=SOURCE,
                    indexed_on='2026-10-14', discovery_status='listed_not_crawled',
                    languages_observed=[], capture_supported=site['id']=='bfe')
    return dict(version=VERSION, source_url=SOURCE, scope='Selected executive administration websites; incomplete directory, not a page sitemap.', sites=sites)


def validate_selection(ids):
    if not isinstance(ids,list) or not all(isinstance(i,str) for i in ids) or len(ids)!=len(set(ids)):
        raise ValueError('Choose distinct catalogue site IDs')
    known={s['id'] for s in inventory()['sites']}
    if not set(ids)<=known: raise ValueError('Unknown catalogue site')
    return sorted(ids)


def site_for_url(url):
    host=urlsplit(url).hostname
    return next((s['id'] for s in inventory()['sites'] if s['host']==host), None)
