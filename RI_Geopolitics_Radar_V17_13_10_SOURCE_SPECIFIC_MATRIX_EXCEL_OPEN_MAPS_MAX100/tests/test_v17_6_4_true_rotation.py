import datetime as dt
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    sys.modules['feedparser'] = types.ModuleType('feedparser')

import scripts.scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


class V1764TrueRotationTests(unittest.TestCase):
    def test_exploration_plan_changes_topic_slice_on_next_scan(self):
        state = sr.initial_scan_state({})
        queries = list(dict.fromkeys(sr.CONFIG['queries_a'] + sr.CONFIG['queries_b_method']))
        first = sr.scholarly_exploration_plan(state, queries)
        second = sr.scholarly_exploration_plan(state, queries)
        self.assertTrue(first['openalex'])
        self.assertTrue(first['crossref'])
        self.assertNotEqual(first['openalex'], second['openalex'])
        self.assertNotEqual(first['crossref'], second['crossref'])
        self.assertFalse(set(first['openalex']) & set(second['openalex']))
        self.assertGreaterEqual(len(first['themes']), 4)

    def test_old_live_state_gets_exploration_cursors_without_resetting_main_cursors(self):
        prev = {
            'scan_state': {
                'version': sr.INCREMENTAL_STATE_VERSION,
                'source_expansion_version': sr.SOURCE_EXPANSION_VERSION,
                'openalex_cursor': 60,
                'crossref_broad_cursor': 0,
                'crossref_priority_cursor': 360,
                'institution_cursor': 18,
                'frontier_gap_cursor': 15,
                'strand_b_method_cursor': 18,
                'backfill': {'openalex': True, 'crossref_broad': True, 'crossref_priority': True, 'institutions': True},
                'completed_cycles': {'openalex': 2, 'crossref_broad': 2, 'crossref_priority': 1, 'institutions': 4},
                'cycle_failed': {'openalex': False, 'crossref_broad': False, 'crossref_priority': False, 'institutions': False},
                'institution_seen_fingerprints': {},
            }
        }
        state = sr.initial_scan_state(prev)
        queries = sr.CONFIG['queries_a'] + sr.CONFIG['queries_b_method']
        sr.scholarly_exploration_plan(state, queries)
        self.assertEqual(state['openalex_cursor'], 60)
        self.assertEqual(state['crossref_priority_cursor'], 360)
        self.assertIn('openalex_explore_cursor', state)
        self.assertIn('crossref_explore_cursor', state)

    def test_openalex_explore_lane_uses_full_corpus_floor_and_separate_depth(self):
        calls = []

        class Resp:
            status_code = 200
            headers = {}
            def json(self):
                n = int(sr.CONFIG.get('openalex_per_query', 60))
                return {'results': [{'title': f'x{i}', 'display_name': f'x{i}'} for i in range(n)]}

        def fake_get(url, params=None, timeout=None):
            calls.append(dict(params))
            return Resp()

        depth = {}
        q = 'European research security'
        with mock.patch.object(sr.SESSION, 'get', side_effect=fake_get), \
             mock.patch.object(sr, 'candidate_from_openalex', return_value=None), \
             mock.patch.object(sr, 'SCAN_DEADLINE_MONO', None):
            sr.collect_openalex(
                dt.date(2026, 8, 9), [], [q],
                query_dates_override={q: dt.date(2026, 4, 21)},
                depth_state=depth,
                depth_lane_overrides={q: 'explore'},
            )
        self.assertIn('from_publication_date:2026-04-21', calls[0]['filter'])
        self.assertEqual([int(c['page']) for c in calls[:2]], [1, 2])
        self.assertEqual(depth[f'explore::{q}'], 3)

    def test_crossref_explore_lane_uses_full_corpus_floor_and_separate_depth(self):
        calls = []

        class Resp:
            status_code = 200
            headers = {}
            def __init__(self, rows): self.rows = rows
            def json(self):
                return {'message': {'items': [{'title': [f'x{i}']} for i in range(self.rows)]}}

        def fake_get(url, params=None, timeout=None):
            calls.append(dict(params))
            return Resp(int(params['rows']))

        q = 'European research security'
        depth = {}
        with mock.patch.object(sr.SESSION, 'get', side_effect=fake_get), \
             mock.patch.object(sr, 'candidate_from_crossref', return_value=None), \
             mock.patch.object(sr, 'SCAN_DEADLINE_MONO', None), \
             mock.patch.object(sr.time, 'sleep', return_value=None):
            sr.collect_crossref(
                dt.date(2026, 8, 9), [], [q], [],
                query_dates_override={q: dt.date(2026, 4, 21)},
                broad_depth_state=depth,
                depth_lane_overrides={q: 'explore'},
            )
        self.assertIn('from-pub-date:2026-04-21', calls[0]['filter'])
        rows = int(sr.CONFIG.get('crossref_rows_per_query', 50))
        self.assertEqual([int(c.get('offset', 0)) for c in calls[:3]], [0, 0, rows])
        self.assertEqual(depth[f'explore::{q}'], 3)

    def test_rotation_config_reserves_real_historical_exploration_budget(self):
        self.assertGreaterEqual(int(sr.CONFIG['openalex_exploration_queries_per_scan']), 8)
        self.assertGreaterEqual(int(sr.CONFIG['crossref_exploration_queries_per_scan']), 6)
        self.assertIn(sr.CONFIG['rotation_profile_version'], {'v17.7.1-executed-work-rotation', 'v17.13.0-rotating-finding-context'})

    def test_quiet_rescue_takes_the_next_slice_not_the_same_slice(self):
        state = sr.initial_scan_state({})
        queries = list(dict.fromkeys(sr.CONFIG['queries_a'] + sr.CONFIG['queries_b_method']))
        first = sr.scholarly_exploration_plan(state, queries, oa_limit=4, cr_limit=4)
        rescue = sr.scholarly_exploration_plan(state, queries, oa_limit=4, cr_limit=4)
        self.assertFalse(set(first['openalex']) & set(rescue['openalex']))
        self.assertFalse(set(first['crossref']) & set(rescue['crossref']))

    def test_zero_limit_does_not_accidentally_scan_the_whole_bank(self):
        state = sr.initial_scan_state({})
        queries = sr.CONFIG['queries_a'] + sr.CONFIG['queries_b_method']
        plan = sr.scholarly_exploration_plan(state, queries, oa_limit=0, cr_limit=0)
        self.assertEqual(plan['openalex'], [])
        self.assertEqual(plan['crossref'], [])


if __name__ == '__main__':
    unittest.main()
