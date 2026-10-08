"""Fail-closed regression tests for first-party institutional publication-list discovery.

No network. A listing carries documentary metadata, not an automatic Strand-A admission.
"""
import datetime as dt
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('scanner_official_listing_dates', ROOT / 'scripts/scan_radar.py')
scan = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)

TITLE = 'European research infrastructure access and innovation performance'
HUB = 'https://www.esfri.eu/library'
DOC = 'https://www.esfri.eu/publications/european-research-infrastructure-access-and-innovation-performance'
LISTING = f'''<html><body><main><article class="publication-card">
  <span class="date">15.09.2026</span><a href="{DOC}">{TITLE}</a>
</article></main></body></html>'''
REPORT = f'''<html lang="en"><main><h1>{TITLE}</h1>
<p>{"Research and innovation across Europe: substantial empirical analysis of research infrastructure, access, innovation outcomes and EU capabilities. " * 18}</p>
</main></html>'''

class Response:
    def __init__(self, url, html):
        self.url = url
        self.text = html
        self.content = html.encode()
        self.headers = {'content-type':'text/html'}
    def __bool__(self):return True


class OfficialListingDates(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT/'radar_config.json').read_text())
        self.profile = self.config['institution_source_adapters']['esfri.eu']
        scan.INSTITUTION_OFFICIAL_LISTING_METADATA.clear()

    def test_official_list_date_parses_european_day_month_correctly(self):
        soup = BeautifulSoup(LISTING, 'html.parser')
        hint = scan._official_publication_listing_hint(soup.a, HUB, DOC, self.profile)
        self.assertEqual(hint['published'], '2026-09-15')
        self.assertEqual(hint['title'], TITLE)

    def test_unrelated_dates_and_updated_date_are_not_publication_dates(self):
        variants = [
            f'<html><main><div><a href="{DOC}">{TITLE}</a></div><time datetime="2026-09-15">15 Sept</time></main></html>',
            f'<div><span class="updated">15.09.2026</span><a href="{DOC}">{TITLE}</a></div>',
            f'<div><span class="date">01.07.2026</span><span class="published">15.09.2026</span><a href="{DOC}">{TITLE}</a></div>',
            f'<div><a href="{DOC}">{TITLE}</a><a href="/reports/other-eu-study">Another important European report</a><time>15.09.2026</time></div>',
        ]
        for html in variants:
            with self.subTest(html=html[:70]):
                hint = scan._official_publication_listing_hint(BeautifulSoup(html,'html.parser').a, HUB, DOC, self.profile)
                self.assertIsNone(hint)

    def test_external_host_or_unconfigured_listing_cannot_supply_date(self):
        soup = BeautifulSoup(LISTING,'html.parser')
        self.assertIsNone(scan._official_publication_listing_hint(soup.a, 'https://www.esfri.eu/news', DOC, self.profile))
        self.assertIsNone(scan._official_publication_listing_hint(soup.a, HUB, 'https://example.com/study.pdf', self.profile))
        self.assertIsNone(scan._official_publication_listing_hint(soup.a, HUB, DOC, {}))

    def test_listing_date_requires_matching_document_title_and_official_host(self):
        scan.INSTITUTION_OFFICIAL_LISTING_METADATA[scan.normalized_link(DOC)] = {
            'published':'2026-09-15','title':TITLE,'hub':HUB,
        }
        self.assertEqual(scan._official_listing_publication_date(DOC,DOC,TITLE),
                         (dt.date(2026,9,15),'official_publication_listing_date'))
        self.assertEqual(scan._official_listing_publication_date(DOC,DOC,'European transport discussion report')[0],None)
        self.assertEqual(scan._official_listing_publication_date(DOC,'https://unrelated.com/page',TITLE)[0],None)

    def test_adapter_carries_date_to_normal_parser_without_bypassing_gate(self):
        src = next(x for x in self.config['institution_sources'] if x['domain']=='esfri.eu')
        def get(url,**kw):
            return Response(url,LISTING) if url.rstrip('/').endswith('esfri.eu/library') else Response(url,REPORT) if url==DOC else None
        with mock.patch.object(scan,'get',side_effect=get), \
             mock.patch.object(scan,'CONFIG',self.config), \
             mock.patch.object(scan,'_op_publications_catalogue_jobs',return_value=[]), \
             mock.patch.object(scan,'_known_institution_url_should_skip',return_value=False), \
             mock.patch.object(scan,'INSTITUTION_SEEN_FINGERPRINTS',set()):
            rows = scan._source_adapter_domain_jobs(src,dt.date(2026,7,1))
            self.assertTrue(any(x[0]==DOC for x in rows))
            with mock.patch.object(scan,'gate_scope', return_value={'a_pass':True,'b_pass':False,'eu_relevance':True}), \
                 mock.patch.object(scan,'build_item',side_effect=lambda **kw: kw), \
                 mock.patch.object(scan,'english_record_ok',return_value=True), \
                 mock.patch.object(scan,'document_exclusion_reason',return_value=''):
                result=scan.parse_institution_page(DOC,src['name'],1,publication_floor=dt.date(2026,7,1))
            self.assertIsNotNone(result)
            self.assertEqual(result['date'],dt.date(2026,9,15))
            self.assertEqual(result['date_basis'],'official_publication_listing_date')
            with mock.patch.object(scan,'gate_scope',return_value={'a_pass':False,'b_pass':False,'eu_relevance':True}), \
                 mock.patch.object(scan,'english_record_ok',return_value=True), \
                 mock.patch.object(scan,'document_exclusion_reason',return_value=''):
                self.assertIsNone(scan.parse_institution_page(DOC,src['name'],1,publication_floor=dt.date(2026,7,1)))

    def test_verified_publication_feed_carries_published_not_updated_time(self):
        from types import SimpleNamespace
        src = next(x for x in self.config['institution_sources'] if x['domain']=='europarl.europa.eu')
        url = 'https://www.europarl.europa.eu/thinktank/en/document/EPRS_STU(2026)123456'
        title = 'European research and innovation system evaluation and comparative evidence'
        feed = SimpleNamespace(
            link=url, title=title, published_parsed=(2026,9,20,0,0,0,0,0,0),
            updated_parsed=(2026,10,8,0,0,0,0,0,0),
        )
        payload = SimpleNamespace(entries=[feed])
        with mock.patch.object(scan,'get',return_value=Response(src['feeds'][0],'<rss/>')), \
             mock.patch.object(scan.feedparser,'parse',return_value=payload), \
             mock.patch.object(scan,'CONFIG',self.config), \
             mock.patch.object(scan,'_known_institution_url_should_skip',return_value=False), \
             mock.patch.object(scan,'INSTITUTION_SEEN_FINGERPRINTS',set()):
            jobs = scan._institution_feed_jobs(src, dt.date(2026,8,1))
            self.assertEqual(jobs[0][0],url)
            self.assertEqual(scan._official_listing_publication_date(url,url,title)[0],dt.date(2026,9,20))
            scan.INSTITUTION_OFFICIAL_LISTING_METADATA.clear()
            feed.published_parsed = None
            scan._institution_feed_jobs(src,dt.date(2026,8,1))
            self.assertFalse(scan.INSTITUTION_OFFICIAL_LISTING_METADATA)

    def test_official_source_routes_include_real_publication_surfaces(self):
        a=self.config['institution_source_adapters']
        self.assertIn('/ideas.html',a['espas.eu']['hub_paths'])
        self.assertIn('/horizon.html',a['espas.eu']['hub_paths'])
        self.assertIn('/library',a['esfri.eu']['hub_paths'])
        self.assertIn('/en/publications/reports.html',a['oecd.org']['hub_paths'])
        self.assertIn('/en/publications/briefs.html',a['oecd.org']['hub_paths'])
        p=next(x for x in self.config['institution_sources'] if x['domain']=='europarl.europa.eu')
        self.assertTrue(any('thinktank/en/rss/search.html' in x for x in p['feeds']))

if __name__=='__main__':unittest.main()
