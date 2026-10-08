"""Deterministic regression tests for Strand A official-document recovery.

No live HTTP; these tests deliberately exercise both successful and unsafe paths.
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
spec = importlib.util.spec_from_file_location('institution_undated_report_scan', ROOT / 'scripts' / 'scan_radar.py')
scan = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)

TITLE = 'European research infrastructure access and its impact on innovation'
PAGE = 'https://www.esfri.eu/publications/report-access-innovation'
PDF = 'https://www.esfri.eu/sites/default/files/downloads/european-research-infrastructure-access-innovation.pdf'
WORDS = (' European research infrastructure access and its impact on innovation'
         ' Evidence from European public research facilities and knowledge transfer.') * 20
DATED = 'Publication date: 12 September 2026. ' + WORDS
HTML = f'''<html lang="en"><head><title>{TITLE}</title></head><body>
<main><h1>{TITLE}</h1><div>Independent analytical report on research facilities and Europe.</div>
<a href="{PDF}">Download the full report: {TITLE} (PDF)</a></main></body></html>'''


class FakeResponse:
    def __init__(self, url=PAGE, html=HTML):
        self.url = url
        self.text = html
        self.headers = {'content-type': 'text/html'}
        self.content = html.encode()
    def __bool__(self):
        return True


class InstitutionalUndatedRecovery(unittest.TestCase):
    def setUp(self):
        self.soup = BeautifulSoup(HTML, 'html.parser')

    def test_matching_official_pdf_recovers_only_visible_date(self):
        with mock.patch.object(scan, '_pdf_payload', return_value=(DATED, len(DATED.split()), {})) as pdf:
            url, text, words, when, basis = scan._recover_undated_institution_pdf(self.soup, PAGE, TITLE)
        self.assertEqual(url, PDF)
        self.assertEqual(when, dt.date(2026, 9, 12))
        self.assertEqual(basis, 'pdf_visible_publication_date')
        self.assertIn('European research infrastructure', text)
        self.assertEqual(pdf.call_count, 1)

    def test_unrelated_pdf_or_creation_timestamp_cannot_supply_date(self):
        for body, meta in [
            ('Publication date: 12 September 2026. ' + ('Unrelated transport analysis. ' * 80), {}),
            (WORDS, {'creation_date': '2026-09-12'}),
            ('Revised project forecast: 12 September 2026. ' + WORDS, {}),
        ]:
            with self.subTest(body=body[:32]), mock.patch.object(scan, '_pdf_payload', return_value=(body, len(body.split()), meta)):
                self.assertIsNone(scan._recover_undated_institution_pdf(self.soup, PAGE, TITLE)[3])

    def test_explicit_publication_month_is_approximate(self):
        body = 'Published: September 2026. ' + WORDS
        with mock.patch.object(scan, '_pdf_payload', return_value=(body, len(body.split()), {})):
            result = scan._recover_undated_institution_pdf(self.soup, PAGE, TITLE)
        self.assertEqual(result[3], dt.date(2026, 9, 1))
        self.assertEqual(result[4], 'pdf_visible_publication_month')

    def test_bare_month_year_does_not_freshen_a_report(self):
        body = 'Forecast baseline: September 2026. ' + WORDS
        with mock.patch.object(scan, '_pdf_payload', return_value=(body, len(body.split()), {})):
            result = scan._recover_undated_institution_pdf(self.soup, PAGE, TITLE)
        self.assertIsNone(result[3])

    def test_external_citation_is_not_used_to_establish_date(self):
        html = f'<html><h1>{TITLE}</h1><a href="https://other.org/study.pdf">Download full report: {TITLE}</a></html>'
        with mock.patch.object(scan, '_pdf_payload') as fetch:
            res = scan._recover_undated_institution_pdf(BeautifulSoup(html, 'html.parser'), PAGE, TITLE)
        self.assertIsNone(res[3])
        fetch.assert_not_called()

    def test_config_switch_disables_rescue_without_network(self):
        conf = dict(scan.CONFIG, institution_undated_pdf_recovery_enabled=False)
        with mock.patch.object(scan, 'CONFIG', conf), mock.patch.object(scan, '_pdf_payload') as fetch:
            self.assertIsNone(scan._recover_undated_institution_pdf(self.soup, PAGE, TITLE)[3])
        fetch.assert_not_called()

    def test_full_page_uses_pdf_body_once_and_passes_original_gate(self):
        # Execute the real parser path; mock only network and eligibility constructor.
        with mock.patch.object(scan, 'get', return_value=FakeResponse()), \
             mock.patch.object(scan, '_known_institution_url_should_skip', return_value=False), \
             mock.patch.object(scan, '_pdf_payload', return_value=(DATED, len(DATED.split()), {})) as fetch, \
             mock.patch.object(scan, 'document_exclusion_reason', return_value=''), \
             mock.patch.object(scan, 'institutional_container_page', return_value=False), \
             mock.patch.object(scan, 'english_record_ok', return_value=True), \
             mock.patch.object(scan, 'gate_scope', return_value={'a_pass': True, 'b_pass': False, 'eu_relevance': True}), \
             mock.patch.object(scan, 'build_item', side_effect=lambda **kw: kw) as builder, \
             mock.patch.object(scan, '_mark_institution_seen'):
            row = scan.parse_institution_page(PAGE, 'ESFRI', 1, publication_floor=dt.date(2026, 7, 1))
        self.assertIsNotNone(row)
        self.assertEqual(row['date'], dt.date(2026, 9, 12))
        self.assertEqual(row['date_basis'], 'pdf_visible_publication_date')
        self.assertIn(WORDS[:70], row['text'])
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(builder.call_count, 1)

    def test_old_verified_pdf_cannot_be_freshened_by_undated_hub(self):
        old = 'Publication date: 12 May 2025. ' + WORDS
        with mock.patch.object(scan, 'get', return_value=FakeResponse()), \
             mock.patch.object(scan, '_known_institution_url_should_skip', return_value=False), \
             mock.patch.object(scan, '_pdf_payload', return_value=(old, len(old.split()), {})), \
             mock.patch.object(scan, 'document_exclusion_reason', return_value=''), \
             mock.patch.object(scan, 'institutional_container_page', return_value=False), \
             mock.patch.object(scan, 'english_record_ok', return_value=True), \
             mock.patch.object(scan, 'build_item') as builder:
            row = scan.parse_institution_page(PAGE, 'ESFRI', 1, publication_floor=dt.date(2026, 7, 1))
        self.assertIsNone(row)
        builder.assert_not_called()

    def test_pdf_absence_never_admits_without_verified_date(self):
        with mock.patch.object(scan, 'get', return_value=FakeResponse()), \
             mock.patch.object(scan, '_known_institution_url_should_skip', return_value=False), \
             mock.patch.object(scan, '_pdf_payload', return_value=('', 0, {})), \
             mock.patch.object(scan, 'document_exclusion_reason', return_value=''), \
             mock.patch.object(scan, 'institutional_container_page', return_value=False), \
             mock.patch.object(scan, 'build_item') as builder:
            row = scan.parse_institution_page(PAGE, 'ESFRI', 1, publication_floor=dt.date(2026, 7, 1))
        self.assertIsNone(row)
        builder.assert_not_called()

    def test_previous_hub_routes_remain_available(self):
        config = json.loads((ROOT/'radar_config.json').read_text())
        self.assertEqual(config['institution_undated_pdf_recovery_max_links'], 2)
        self.assertIn('/stoa/en/publications/search', config['institution_source_adapters']['europarl.europa.eu']['hub_paths'])


if __name__ == '__main__':
    unittest.main()
