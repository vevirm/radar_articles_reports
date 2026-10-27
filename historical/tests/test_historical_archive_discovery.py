"""Offline checks for bounded historical archive navigation and honest publication dates."""
import unittest
from unittest.mock import Mock, patch
from test_historical_scanner import H


class HistoricalArchiveTests(unittest.TestCase):
    def setUp(self):
        H.DIAG.clear(); H.HIST_OFFICIAL_LISTING_HINTS.clear()

    def test_two_hop_archive_reaches_old_study_and_keeps_verified_full_date(self):
        domain='archive.example.org'
        index='https://archive.example.org/publications'
        year='https://archive.example.org/publications/2019'
        study='https://archive.example.org/publications/2019/european-research-capacity-assessment'
        pages={
            index:'<a href="/publications/2019">2019 research publications archive</a>'
                  '<a href="/publications/2027/recent">2027 research report</a>'
                  '<a href="https://other.example.org/publications/2019/study">2019 report at another publisher</a>',
            year:'<article><a href="/publications/2019/european-research-capacity-assessment">'
                 'European research capacity assessment study</a>'
                 '<time datetime="2019-04-16">16 April 2019</time></article>',
            study:'<p>Publication landing page</p>',
        }
        def get(url,**kwargs):
            return Mock(ok=True,url=url,text=pages[url],headers={'Content-Type':'text/html'})
        with patch.dict(H.CONFIG['historical_archive_hubs'],{domain:['/publications']}), \
             patch.object(H,'budget_ok',return_value=True), patch.object(H.SESSION,'get',side_effect=get) as call:
            candidates=H.historical_archive_candidates({'domain':domain},[{'url_terms':['research','capacity']}],[])
        self.assertIn(study,candidates)
        # Future-looking URL years are clues, never evidence of publication age.
        self.assertIsNone(H.historical_date_from_text('2027 research report'))
        self.assertTrue(all('other.example.org' not in u for u in candidates))
        self.assertLessEqual(call.call_count,6)
        self.assertEqual(H._historical_verified_listing_date(study,study,'European research capacity assessment study').isoformat(),'2019-04-16')

    def test_bare_year_archive_does_not_manufacture_publication_day(self):
        domain='archive.example.org'; hub='https://archive.example.org/publications'
        response=Mock(ok=True,url=hub,headers={'Content-Type':'text/html'},text='<a href="/publications/2017/research-paper">European research policy study 2017</a>')
        with patch.dict(H.CONFIG['historical_archive_hubs'],{domain:['/publications']}), \
             patch.object(H,'budget_ok',return_value=True), patch.object(H.SESSION,'get',return_value=response):
            candidates=H.historical_archive_candidates({'domain':domain},[{'url_terms':['research']}],[])
        self.assertTrue(candidates)
        self.assertEqual(H.HIST_OFFICIAL_LISTING_HINTS,{})
        self.assertIsNone(H.historical_date_from_text('European research policy study 2017'))

    def test_archive_does_not_replace_same_main_admission_gate(self):
        import inspect
        code=inspect.getsource(H.collect_direct_sources)
        self.assertIn('historical_archive_candidates',code)
        self.assertIn('fetch_page_candidate',code)
        self.assertIn('sitemap_candidates',code)

if __name__=='__main__': unittest.main()
