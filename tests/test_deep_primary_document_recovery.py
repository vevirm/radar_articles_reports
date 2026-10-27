"""Offline Deep V2 source-link recovery and identity mismatch tests."""
import os
import unittest
from unittest.mock import patch
from scripts import deep_read_works as D


class DeepPrimaryDocumentTests(unittest.TestCase):
    def test_same_publisher_pdf_link_detected_without_separate_discovery_request(self):
        html=b'''<html><head><meta name="citation_title" content="European research funding capacity assessment" />
          <meta name="citation_pdf_url" content="/download/full-report.pdf" /></head>
          <body><a href="https://evil.example.com/report.pdf">External paper</a>
          <a href="/files/supplement.pdf">Supplement</a></body></html>'''
        title,doi,links=D._document_metadata_and_links(html,'https://research.example.org/publications/work')
        self.assertEqual(title,'European research funding capacity assessment')
        self.assertEqual(links,('https://research.example.org/download/full-report.pdf',))
        self.assertEqual(doi,'')

    def test_landing_page_download_beats_thin_abstract(self):
        record={'title':'European research funding capacity assessment',
                'link':'https://research.example.org/publication/123'}
        landing=record['link']; pdf='https://research.example.org/download/full-report.pdf'
        calls=[]
        def fake_fetch(url,*,extra_headers=None):
            calls.append(url)
            if url==landing:
                return D.SourceRead('abstract_or_landing_page','Abstract of the study '*30,landing,'',
                    primary_links=(pdf,),document_title=record['title'])
            if url==pdf:
                return D.SourceRead('pdf_excerpt',('European research funding capacity assessment '+ 'analysis findings '*40),pdf,'')
            raise AssertionError(f'unexpected {url}')
        with patch.object(D,'fetch_source',side_effect=fake_fetch),patch.object(D,'_openalex_work_for_record',return_value=(None,'no DOI')):
            result=D.fetch_source_for_record(record)
        self.assertEqual(result.mode,'pdf_excerpt')
        self.assertEqual(result.final_url,pdf)
        self.assertIn('source-owned document link',result.note)
        self.assertEqual(result.identity_status,'plausible')
        self.assertEqual(calls,[landing,pdf])

    def test_document_redirect_to_unrelated_host_is_not_used(self):
        record={'title':'European research funding capacity assessment',
                'link':'https://research.example.org/publication/123'}
        lead='https://research.example.org/report.pdf'
        def fake_fetch(url,*,extra_headers=None):
            if url==record['link']:
                return D.SourceRead('abstract_or_landing_page','Abstract '*50,url,'',primary_links=(lead,))
            if url==lead:
                return D.SourceRead('pdf_excerpt','European research funding capacity assessment '*100,
                                    'https://unrelated.example.net/foreign.pdf')
            raise AssertionError(url)
        with patch.object(D,'fetch_source',side_effect=fake_fetch),patch.object(D,'_openalex_work_for_record',return_value=(None,'no DOI')):
            result=D.fetch_source_for_record(record)
        self.assertNotEqual(result.final_url,'https://unrelated.example.net/foreign.pdf')
        self.assertEqual(result.mode,'abstract_or_landing_page')

    def test_contradictory_doi_is_rejected_and_not_certified(self):
        record={'title':'European innovation capabilities', 'doi':'10.1111/expected', 'link':'https://journal.example.org/paper'}
        first=D.SourceRead('substantial_web_text','Text '*1200,record['link'],'',document_title='Different unrelated work',document_doi='10.1111/different')
        with patch.object(D,'fetch_source',return_value=first),patch.object(D,'_openalex_work_for_record',return_value=(None,'OpenAlex unavailable')):
            result=D.fetch_source_for_record(record)
        self.assertEqual(result.mode,'stored_only')
        self.assertIn('identity mismatch',result.note)

    def test_exact_doi_openalex_mismatch_fails_closed(self):
        class FakeResponse:
            def raise_for_status(self): pass
            def json(self): return {'results':[{'doi':'https://doi.org/10.5555/other','id':'https://openalex.org/W1'}]}
        with patch.dict(os.environ,{'OPENALEX_API_KEY':'local-only-test'}),patch.object(D.requests,'get',return_value=FakeResponse()):
            work,note=D._openalex_work_for_record({'doi':'10.5555/original'})
        self.assertIsNone(work)
        self.assertIn('different DOI',note)

    def test_uncertain_first_party_text_is_not_reported_as_verified(self):
        record={'link':'https://publications.europa.eu/resource/celex/32025R0001',
                'source_validation_url':'https://publications.europa.eu/resource/celex/32025R0001'}
        with patch.object(D,'fetch_source',return_value=D.SourceRead('substantial_web_text','First-party content '*150,record['link'])):
            src=D.fetch_source_for_record(record)
        self.assertEqual(src.identity_status,'unverified')
        self.assertIn('NOT independently identity verified',src.note)

if __name__=='__main__': unittest.main()
