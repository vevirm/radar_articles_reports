import datetime as dt
import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    sys.modules["feedparser"] = types.ModuleType("feedparser")

import scripts.scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


class V1756RotationDepthTests(unittest.TestCase):
    def test_existing_v172_state_is_extended_without_resetting_cursors(self):
        prev = {
            'scan_state': {
                'version': sr.INCREMENTAL_STATE_VERSION,
                'source_expansion_version': sr.SOURCE_EXPANSION_VERSION,
                'openalex_cursor': 52, 'crossref_broad_cursor': 0,
                'crossref_priority_cursor': 360, 'institution_cursor': 0,
                'frontier_gap_cursor': 13,
                'backfill': {'openalex': True, 'crossref_broad': True, 'crossref_priority': False, 'institutions': True},
                'completed_cycles': {'openalex': 1, 'crossref_broad': 1, 'crossref_priority': 0, 'institutions': 2},
                'cycle_failed': {'openalex': False, 'crossref_broad': False, 'crossref_priority': False, 'institutions': False},
                'institution_seen_fingerprints': {'x|2026-08-01': '2026-08-22T00:00Z'},
            }
        }
        state = sr.initial_scan_state(prev)
        self.assertEqual(state['openalex_cursor'], 52)
        self.assertEqual(state['crossref_priority_cursor'], 360)
        self.assertTrue(state['backfill']['openalex'])
        self.assertEqual(state['institution_seen_fingerprints'], {'x|2026-08-01': '2026-08-22T00:00Z'})
        self.assertIn('frontier_gap_query_cursors', state)
        self.assertIn('frontier_gap_source_cursors', state)
        self.assertIn('result_depth', state)

    def test_gap_scholarly_variants_resume_per_cell(self):
        state = sr.initial_scan_state({})
        counts = {k: 3 for k in sr.FRONTIER_CELL_ORDER}
        counts['knowledge-A'] = 0
        with mock.patch.object(sr, 'frontier_matrix_coverage', return_value=(counts, 45, '')):
            p1 = sr.frontier_gap_plan({}, state)
            q1 = list(p1['scholarly_queries'])
            p2 = sr.frontier_gap_plan({}, state)
            q2 = list(p2['scholarly_queries'])
        self.assertTrue(q1)
        self.assertTrue(q2)
        self.assertNotEqual(q1[0], q2[0])
        self.assertIn('scholarly:knowledge-A', state['frontier_gap_query_cursors'])

    def test_openalex_checks_latest_and_next_depth_page(self):
        calls = []

        class Resp:
            status_code = 200
            headers = {}

            def json(self):
                n = int(sr.CONFIG.get('openalex_per_query', 80))
                return {'results': [{'title': f'x{i}', 'display_name': f'x{i}'} for i in range(n)]}

        def fake_get(url, params=None, timeout=None):
            calls.append(int(params['page']))
            return Resp()

        depth = {}
        with mock.patch.object(sr.SESSION, 'get', side_effect=fake_get), \
             mock.patch.object(sr, 'candidate_from_openalex', return_value=None), \
             mock.patch.object(sr, 'SCAN_DEADLINE_MONO', None):
            sr.collect_openalex(dt.date(2026, 4, 21), [], ['test query'], depth_state=depth)
        self.assertEqual(calls[:2], [1, 2])
        self.assertEqual(depth['test query'], 3)

    def test_crossref_checks_latest_and_rotating_offset(self):
        calls = []

        class Resp:
            status_code = 200
            headers = {}

            def __init__(self, rows):
                self.rows = rows

            def json(self):
                return {'message': {'items': [{'title': [f'x{i}']} for i in range(self.rows)]}}

        def fake_get(url, params=None, timeout=None):
            calls.append(int(params.get('offset', 0)))
            return Resp(int(params['rows']))

        depth = {}
        with mock.patch.object(sr.SESSION, 'get', side_effect=fake_get), \
             mock.patch.object(sr, 'candidate_from_crossref', return_value=None), \
             mock.patch.object(sr, 'SCAN_DEADLINE_MONO', None), \
             mock.patch.object(sr.time, 'sleep', return_value=None):
            sr.collect_crossref(dt.date(2026, 4, 21), [], ['test query'], [], broad_depth_state=depth)
        rows = int(sr.CONFIG.get('crossref_rows_per_query', 50))
        self.assertEqual(calls[:3], [0, 0, rows])
        self.assertEqual(depth['test query'], 3)

    def test_quality_and_incremental_versions_are_not_bumped(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text())
        self.assertEqual(cfg['incremental_state_version'], 'v17.2-persistent-source-cursors')
        self.assertEqual(cfg['source_expansion_version'], 'v17.5.2-gap-report-recall')
        self.assertEqual(cfg['quality_profile_version'], 'v17.6.2-B-futures-method-as-such')


if __name__ == '__main__':
    unittest.main()
