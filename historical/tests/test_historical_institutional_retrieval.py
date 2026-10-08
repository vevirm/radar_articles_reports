"""Offline tests for conservative official-publication-list recovery in Historical."""
import io
import unittest
from unittest.mock import Mock, patch

from bs4 import BeautifulSoup
from pypdf import PdfWriter

from test_historical_scanner import H


class OfficialHistoricalListingTests(unittest.TestCase):
    def setUp(self):
        H.HIST_OFFICIAL_LISTING_HINTS.clear()
        H.DIAG.clear()

    def test_official_card_supplies_full_historical_date(self):
        doc = BeautifulSoup('''<section><div class="card">
          <h3><a href="/publications/report-2020">European research infrastructure landscape assessment</a></h3>
          <time datetime="2020-05-19">19 May 2020</time>
          </div></section>''', 'html.parser')
        anchor=doc.find('a')
        hint=H._historical_listing_hint(anchor,'https://esfri.eu/library',
                                       'https://esfri.eu/publications/report-2020')
        self.assertEqual(hint['published'], '2020-05-19')
        H.HIST_OFFICIAL_LISTING_HINTS['https://esfri.eu/publications/report-2020']=hint
        d=H._historical_verified_listing_date(
            'https://esfri.eu/publications/report-2020',
            'https://www.esfri.eu/publications/report-2020',
            'European research infrastructure landscape assessment')
        self.assertEqual(str(d),'2020-05-19')
        self.assertEqual(H.DIAG['historical_official_listing_date_verified'],1)

    def test_unrelated_title_cannot_borrow_date(self):
        url='https://esfri.eu/publications/report-2020'
        H.HIST_OFFICIAL_LISTING_HINTS[url]={'title':'European research infrastructure landscape assessment',
                                            'published':'2020-05-19','hub':'https://esfri.eu/library'}
        self.assertIsNone(H._historical_verified_listing_date(
            url, url, 'Transatlantic science cooperation annual overview'))

    def test_other_publisher_cannot_borrow_date(self):
        url='https://esfri.eu/publications/report-2020'
        H.HIST_OFFICIAL_LISTING_HINTS[url]={'title':'European research infrastructure landscape assessment',
                                            'published':'2020-05-19','hub':'https://another-publisher.org/publications'}
        self.assertIsNone(H._historical_verified_listing_date(
            url,url,'European research infrastructure landscape assessment'))

    def test_multi_report_list_never_transfers_date(self):
        doc=BeautifulSoup('''<ul><li><a href="/a">European research infrastructure landscape assessment</a>
          <a href="/b">European science collaboration assessment report</a>
          <time datetime="2020-05-19">19 May 2020</time></li></ul>''','html.parser')
        self.assertIsNone(H._historical_listing_hint(
            doc.find('a'),'https://esfri.eu/library','https://esfri.eu/a'))

    def test_update_not_mistaken_for_publication(self):
        doc=BeautifulSoup('''<article><a href="/a">European research infrastructure landscape assessment</a>
        Last updated: 2020-05-19</article>''','html.parser')
        self.assertIsNone(H._historical_listing_hint(
            doc.find('a'),'https://esfri.eu/library','https://esfri.eu/a'))

    def test_unambiguous_european_parliament_date(self):
        self.assertEqual(str(H._historical_listing_date_value('Study 23-02-2020')),'2020-02-23')
        self.assertIsNone(H._historical_listing_date_value('Study 05-06-2020'))
        self.assertEqual(str(H._historical_listing_date_value('Report 19.05.2019')),'2019-05-19')

    def test_unrelated_year_does_not_create_fake_publication_date(self):
        self.assertIsNone(H.historical_date_from_text(
            'Our report discusses European innovation policy between 2015 and 2023.'))
        self.assertIsNone(H.historical_date_from_text('Latest study from 2019'))
        self.assertEqual(str(H.historical_date_from_text(
            "Published on 19 May 2019. Europe's research systems were assessed.")),'2019-05-19')

    def test_html_document_uses_matching_publisher_listing_date(self):
        url='https://esfri.eu/publications/report-2020'
        H.HIST_OFFICIAL_LISTING_HINTS[url]={'title':'European research infrastructure landscape assessment',
                                            'published':'2020-05-19','hub':'https://esfri.eu/library'}
        html='''<html><head><meta property="og:title" content="European research infrastructure landscape assessment"/></head>
        <body><article>Analysis of European research infrastructure scientific capacity and international networks.
        This work reviews developments from 2015 to 2020.</article></body></html>'''
        response=Mock(ok=True,url=url,text=html,headers={'Content-Type':'text/html'})
        with patch.object(H,'budget_ok',return_value=True), patch.object(H.SESSION,'get',return_value=response), \
             patch.object(H,'admit',side_effect=lambda raw,lane:raw):
            result=H.fetch_page_candidate(url,{'name':'ESFRI'},[])
        self.assertEqual(str(result['date']),'2020-05-19')
        self.assertEqual(result['landing_page_url'],url)

    def test_scanner_collects_and_passes_official_listing_evidence(self):
        hub='https://esfri.eu/library'
        landing='https://esfri.eu/publications/report-2020'
        hub_html='''<div class="card"><h3><a href="/publications/report-2020">European research infrastructure landscape assessment</a></h3>
          <time datetime="2020-05-19">19 May 2020</time></div>'''
        report_html='''<html><head><meta property="og:title" content="European research infrastructure landscape assessment"/></head>
          <body><article>European research infrastructures contribute scientific evidence on the innovation
          capacities of European universities and research institutions.</article></body></html>'''
        def get(url, **kwargs):
            return Mock(ok=True,url=url,text=hub_html if url==hub else report_html,
                        headers={'Content-Type':'text/html'})
        with patch.object(H,'budget_ok',return_value=True), patch.object(H.SESSION,'get',side_effect=get),\
             patch.object(H,'admit',side_effect=lambda raw,lane:raw),\
             patch.object(H,'sitemap_candidates',return_value=[]):
            H.CONFIG['source_adapters']['esfri.eu']=['/library']
            results=H.collect_direct_sources([{'name':'ESFRI','domain':'esfri.eu'}],
                                             [{'url_terms':['research','infrastructure']}],[],1)
        self.assertEqual(len(results),1)
        self.assertEqual(str(results[0]['date']),'2020-05-19')
        self.assertGreaterEqual(H.DIAG['historical_official_listing_dates_discovered'],1)

    def test_pdf_creation_date_not_accepted_as_publication(self):
        writer=PdfWriter()
        writer.add_blank_page(width=180,height=200)
        writer.add_metadata({'/Title':'European research infrastructure landscape assessment',
                             '/CreationDate':'D:20200519000000'})
        out=io.BytesIO();writer.write(out)
        url='https://esfri.eu/report.pdf'
        response=Mock(ok=True,url=url,content=out.getvalue(),headers={'Content-Type':'application/pdf'})
        with patch.object(H,'budget_ok',return_value=True),patch.object(H.SESSION,'get',return_value=response),\
             patch.object(H,'admit',side_effect=lambda raw,lane:raw):
            result=H.fetch_page_candidate(url,{'name':'ESFRI'},[])
        self.assertIsNone(result['date'])


if __name__=='__main__':
    unittest.main()
