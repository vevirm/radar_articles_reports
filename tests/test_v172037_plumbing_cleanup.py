import importlib.util
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / 'scripts' / 'scan_radar.py'
spec = importlib.util.spec_from_file_location('radar_scan_v172037', SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class _Resp:
    def __init__(self, status=200, text='', content=b'', content_type='text/html', url='https://example.org/x'):
        self.status_code = status
        self.text = text
        self.content = content
        self.headers = {'content-type': content_type}
        self.url = url


class PlumbingCleanupTests(unittest.TestCase):
    def setUp(self):
        self.old_ids = set(scan.KNOWN_AB_IDENTITIES)
        self.old_doi_titles = set(scan.KNOWN_AB_DOI_TITLES)
        self.old_links = set(scan.KNOWN_AB_LINKS)
        self.old_seen = dict(scan.INSTITUTION_SEEN_FINGERPRINTS)
        scan.KNOWN_AB_IDENTITIES = set()
        scan.KNOWN_AB_DOI_TITLES = set()
        scan.KNOWN_AB_LINKS = set()
        scan.INSTITUTION_SEEN_FINGERPRINTS = {}

    def tearDown(self):
        scan.KNOWN_AB_IDENTITIES = self.old_ids
        scan.KNOWN_AB_DOI_TITLES = self.old_doi_titles
        scan.KNOWN_AB_LINKS = self.old_links
        scan.INSTITUTION_SEEN_FINGERPRINTS = self.old_seen

    def test_issue_labelled_journal_name_keeps_tier(self):
        self.assertTrue(scan.journal_name_matches('Survival: August-September 2026', 'Survival'))
        tier, _, _ = scan.source_rank_for_journal('Survival: August-September 2026')
        # Survival is in the configured quality universe even when Crossref appends an issue label.
        self.assertIn(tier, {1, 2})
        self.assertFalse(scan.journal_name_matches('Science Advances', 'Science'))

    def test_same_title_different_doi_is_not_collapsed(self):
        previous = {
            'strand_a': [{
                'title': 'Annual report on research security',
                'link': 'https://doi.org/10.1000/first',
            }],
            'strand_b': [], 'strand_c': [],
        }
        ids, links, sigs, doi_titles = scan.known_sets_from_previous(previous)
        scan.KNOWN_AB_IDENTITIES = ids
        scan.KNOWN_AB_LINKS = links
        scan.KNOWN_AB_DOI_TITLES = doi_titles
        self.assertTrue(scan.known_ab_duplicate('Annual report on research security', 'https://doi.org/10.1000/first'))
        self.assertFalse(scan.known_ab_duplicate('Annual report on research security', 'https://doi.org/10.1000/second'))
        # A DOI-less publisher representation of the saved DOI record is still duplicate.
        self.assertTrue(scan.known_ab_duplicate('Annual report on research security', 'https://publisher.example/report'))

    def test_changed_sitemap_lastmod_can_revisit_known_url(self):
        url = 'https://oecd.org/publications/research-security-report'
        scan.KNOWN_AB_LINKS = {scan.normalized_link(url)}
        old_fp = scan.institution_fingerprint(url, scan.dt.date(2026, 8, 1))
        new_fp = scan.institution_fingerprint(url, scan.dt.date(2026, 9, 1))
        scan.INSTITUTION_SEEN_FINGERPRINTS = {old_fp: '2026-08-01T00:00Z'}
        self.assertTrue(scan._known_institution_url_should_skip(url, old_fp))
        self.assertFalse(scan._known_institution_url_should_skip(url, new_fp))

    def test_failed_no_date_page_does_not_poison_seen_cache(self):
        fp = scan.institution_fingerprint('https://oecd.org/report/no-date', None)
        html = '<html lang="en"><head><meta property="og:title" content="Research security in Europe"></head><body><main>' + ('research security Europe universities technology competition ' * 80) + '</main></body></html>'
        with mock.patch.object(scan, 'get', return_value=_Resp(text=html, url='https://oecd.org/report/no-date')):
            row = scan.parse_institution_page('https://oecd.org/report/no-date', 'OECD', 1, fingerprint=fp)
        self.assertIsNone(row)
        self.assertNotIn(fp, scan.INSTITUTION_SEEN_FINGERPRINTS)

    def test_direct_pdf_is_dispatched_to_pdf_parser(self):
        resp = _Resp(content_type='application/pdf', url='https://oecd.org/report.pdf', content=b'%PDF')
        sentinel = {'title': 'x', 'link': 'https://oecd.org/report.pdf'}
        with mock.patch.object(scan, 'get', return_value=resp), mock.patch.object(scan, 'parse_institution_pdf', return_value=sentinel) as pdf:
            row = scan.parse_institution_page('https://oecd.org/report.pdf', 'OECD', 1)
        self.assertIs(row, sentinel)
        pdf.assert_called_once()

    def test_direct_pdf_parser_can_admit_valid_document(self):
        body = ('European research organisations face technology access restrictions and external dependency under strategic competition. ' * 50)
        ev = {
            'a_pass': True, 'b_pass': False, 'eu_relevance': 'direct', 'a_route': 'explicit-geopolitics',
            'ri_evidence': ['research organisations'], 'geo_evidence': ['strategic competition'],
            'eu_evidence': ['European'], 'a_context_evidence': ['technology access restrictions'],
            'foresight_evidence': [], 'method_evidence': [], 'bridge_sentence': '', 'text_mode': 'body',
        }
        fp = scan.institution_fingerprint('https://oecd.org/reports/security.pdf', scan.dt.date(2026, 9, 1))
        with mock.patch.object(scan, '_pdf_payload', return_value=(body, len(body.split()), {'title': 'European research security under strategic competition', 'author': 'OECD', 'creation_date': '2026-09-01'})), \
             mock.patch.object(scan, 'gate_scope', return_value=ev), \
             mock.patch.object(scan, 'document_exclusion_reason', return_value=''):
            row = scan.parse_institution_pdf('https://oecd.org/reports/security.pdf', 'OECD', 1, fingerprint=fp)
        self.assertIsNotNone(row)
        self.assertEqual(row.get('source_integrity_basis'), 'institution_pdf')
        self.assertIn(fp, scan.INSTITUTION_SEEN_FINGERPRINTS)

    def test_institutional_doi_integrity_is_allowed_only_with_bibliographic_basis(self):
        base = {
            'title': 'OECD report on European research security',
            'source': 'OECD',
            'date': '2026-08-01',
            'link': 'https://doi.org/10.1787/example',
            'type': 'institutional report',
        }
        self.assertFalse(scan.record_source_integrity_ok(base))
        tagged = dict(base, source_integrity_basis='bibliographic_doi')
        self.assertTrue(scan.record_source_integrity_ok(tagged))

    def test_manual_doi_uses_scholarly_recovery_not_institution_parser(self):
        previous = {
            'manual_ingest': {
                'recovery_queue': [{
                    'manual_id': 'm1', 'manual_candidate_kind': 'substantive',
                    'title': 'European science policy under strategic competition',
                    'url': 'https://doi.org/10.1000/manual', 'source_kind': 'scholarly',
                }]
            }
        }
        sentinel = {
            'title': 'European science policy under strategic competition',
            'link': 'https://doi.org/10.1000/manual', 'strand': 'A', '_source_rank': 2.0,
            '_confidence': 3, '_preprint': False,
        }
        with mock.patch.object(scan, '_manual_scholarly_recovery', return_value=sentinel) as schol, \
             mock.patch.object(scan, 'parse_institution_page') as inst:
            rows = scan.collect_manual_recovery(previous, [], time.monotonic() + 30)
        self.assertEqual(len(rows), 1)
        schol.assert_called_once()
        inst.assert_not_called()

    def test_old_curator_rejection_is_retested_once_after_profile_change(self):
        batch = {
            'profile_version': 'p', 'batch_id': 'b', 'source_document': 'x',
            'candidates': [{'candidate_id': 'c1', 'title': 'European research security', 'doi': '10.1000/x'}],
        }
        previous = {'curator_candidate_testing': {'results': [{'candidate_id': 'c1', 'status': 'rejected_source_quality', 'decision_profile_version': 'old'}]}}
        with mock.patch.object(scan, 'load_curator_candidate_tests', return_value=batch), \
             mock.patch.object(scan, '_curator_candidate_known', return_value=False), \
             mock.patch.object(scan, '_curator_crossref_lookup', return_value=(None, 'unresolved')), \
             mock.patch.object(scan, '_snowball_resolve_seed', return_value=None):
            _rows, state = scan.collect_curator_candidate_tests(previous, [], time.monotonic() + 30)
        self.assertEqual(state.get('attempted_this_scan'), 1)
        self.assertEqual(state['results'][0].get('decision_profile_version'), scan.CURATOR_DECISION_PROFILE_VERSION)

    def test_curator_extended_window_uses_peer_reviewed_quality_rule(self):
        src = SCAN_PATH.read_text(encoding='utf-8')
        self.assertIn('extended_high_quality_merit(candidate)', src)
        self.assertNotIn('d >= EXTENDED_DATE_FLOOR and highest_source_merit(candidate)', src)

    def test_low_yield_target_counts_strand_a_not_b(self):
        fake = [
            {'title': 'A', 'strand': 'A'},
            {'title': 'B', 'strand': 'B'},
            {'title': 'Both', 'strand': 'both'},
        ]
        with mock.patch.object(scan, 'genuinely_new_ab_candidates', return_value=fake):
            rows = scan.genuinely_new_a_candidates([])
        self.assertEqual([x['strand'] for x in rows], ['A', 'both'])
        self.assertEqual(scan.CONFIG.get('target_new_a_per_scan'), 5)


if __name__ == '__main__':
    unittest.main()
