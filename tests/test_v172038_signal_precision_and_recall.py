import importlib.util
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / 'scripts' / 'scan_radar.py'
spec = importlib.util.spec_from_file_location('radar_scan_v172038', SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class _CRResp:
    status_code = 200
    headers = {}
    def __init__(self):
        self.url = 'https://api.crossref.org/works'
    def json(self):
        return {'message': {'items': []}}


class SignalPrecisionRecallTests(unittest.TestCase):
    def test_engaging_does_not_create_aging_demographic_theme(self):
        text = "The exercise offered a practical and engaging forum for space policy experts."
        self.assertNotIn('demographic change / research workforce', scan.themes_for(text))

    def test_lunar_governance_without_ri_mechanism_fails_c_bridge(self):
        headline = 'Surface tensions: what a lunar coordination tabletop revealed about governance'
        desc = "The exercise offered a practical and engaging forum for space policy experts to discuss lunar governance."
        self.assertFalse(scan.weak_signal_ri_strategic_bridge_ok(headline, desc, scan.themes_for(headline + ' ' + desc)))

    def test_real_external_research_talent_signal_still_passes_c_bridge(self):
        headline = 'India launches programme to lure scientists back from overseas'
        desc = 'The new funding and return fellowships seek to recruit researchers working abroad into Indian universities.'
        self.assertTrue(scan.weak_signal_ri_strategic_bridge_ok(headline, desc, scan.themes_for(headline + ' ' + desc)))

    def test_month_only_institution_url_is_usable_date_hint(self):
        d, basis = scan._url_publication_date_hint('https://example.org/publications/2026/08/research-security-report')
        self.assertEqual(d, scan.dt.date(2026, 8, 1))
        self.assertEqual(basis, 'url_publication_month')

    def test_linked_pdf_visible_month_can_expose_stale_wrapper(self):
        body = 'ALLEA STATEMENT ON THREATS TO ACADEMIC FREEDOM AND INTERNATIONAL RESEARCH COLLABORATION IN THE UNITED STATES February 2025 ' + ('research collaboration ' * 30)
        d, basis = scan._pdf_visible_date_hint(body, 'https://allea.org/wp-content/uploads/2025/02/statement.pdf')
        self.assertEqual(d, scan.dt.date(2025, 2, 1))
        self.assertIn('pdf_', basis)


    def test_current_wrapper_cannot_launder_old_linked_pdf_into_main_window(self):
        class Resp:
            status_code = 200
            headers = {'content-type': 'text/html'}
            url = 'https://allea.org/news/2026/06/research-collaboration'
            text = '<html lang="en"><head><meta property="og:title" content="ALLEA Calls for Global Defence of International Research Collaboration and Academic Freedom"><meta property="article:published_time" content="2026-06-29"></head><body><main><p>European academies discuss international research collaboration and threats to academic freedom.</p></main></body></html>'
        pdf_body = 'ALLEA STATEMENT ON THREATS TO ACADEMIC FREEDOM AND INTERNATIONAL RESEARCH COLLABORATION IN THE UNITED STATES February 2025 ' + ('European research collaboration United States funding ' * 80)
        with mock.patch.object(scan, 'get', return_value=Resp()),              mock.patch.object(scan, '_primary_pdf_link', return_value='https://allea.org/wp-content/uploads/2025/02/ALLEA-Statement.pdf'),              mock.patch.object(scan, 'pdf_text', return_value=(pdf_body, len(pdf_body.split()))),              mock.patch.object(scan, '_pdf_text_matches_document', return_value=True):
            row = scan.parse_institution_page(
                Resp.url, 'ALLEA', 1, publication_floor=scan.dt.date(2026, 5, 1)
            )
        self.assertIsNone(row)

    def test_low_yield_crossref_depth_uses_bibliographic_query(self):
        calls = []
        def fake_get(url, params=None, timeout=None, **kwargs):
            calls.append(dict(params or {}))
            return _CRResp()
        stats = {}
        with mock.patch.object(scan.SESSION, 'get', side_effect=fake_get), \
             mock.patch.object(scan.time, 'sleep', return_value=None):
            scan.collect_crossref(
                scan.dt.date(2026, 5, 1), [],
                queries_override=['European research security competition'],
                priority_tasks_override=[], source_sweep_journals_override=[],
                stage_deadline=time.monotonic() + 30,
                query_dates_override={'European research security competition': scan.dt.date(2026, 5, 1)},
                broad_depth_state={}, priority_depth_state={},
                depth_lane_overrides={'European research security competition': 'low-yield-depth'},
                execution_stats=stats, depth_only=True,
            )
        self.assertTrue(calls)
        self.assertIn('query.bibliographic', calls[0])
        self.assertNotIn('query.title', calls[0])

    def test_normal_crossref_stays_title_first(self):
        calls = []
        def fake_get(url, params=None, timeout=None, **kwargs):
            calls.append(dict(params or {}))
            return _CRResp()
        with mock.patch.object(scan.SESSION, 'get', side_effect=fake_get), \
             mock.patch.object(scan.time, 'sleep', return_value=None):
            scan.collect_crossref(
                scan.dt.date(2026, 5, 1), [],
                queries_override=['European research security competition'],
                priority_tasks_override=[], source_sweep_journals_override=[],
                stage_deadline=time.monotonic() + 30,
                broad_depth_state={}, priority_depth_state={},
                depth_lane_overrides={}, execution_stats={}, depth_only=False,
            )
        self.assertTrue(calls)
        self.assertIn('query.title', calls[0])


if __name__ == '__main__':
    unittest.main()
