import json
import sys, types
import unittest
from unittest import mock
from pathlib import Path

try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    mod = types.ModuleType('feedparser')
    mod.parse = lambda *a, **k: types.SimpleNamespace(entries=[])
    sys.modules['feedparser'] = mod

from scripts import scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


class MatrixFirstDepthTests(unittest.TestCase):
    def test_gap_plan_targets_empty_cells_or_sparse_cells_when_matrix_is_full(self):
        prev = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
        state = sr.initial_scan_state(prev)
        focus = sr.frontier_gap_plan(prev, state)
        self.assertEqual(
            len(focus['scholarly_queries']),
            sum(len(v) for v in focus['scholarly_query_cells'].values()),
        )
        self.assertGreater(len(focus['scholarly_queries']), 0)
        used_cells = set(focus['scholarly_query_cells'])
        self.assertTrue(set(focus['targets']).issubset(used_cells))
        if focus['empty_targets']:
            self.assertTrue(set(focus['empty_targets']).issubset(used_cells))
            self.assertTrue(all(len(focus['scholarly_query_cells'].get(c, [])) >= 2 for c in focus['empty_targets']))
        else:
            self.assertEqual(focus['empty_cells'], 0)
            self.assertTrue(focus['targets'])
            self.assertTrue(all(focus['deficits'].get(c, 0) > 0 for c in focus['targets']))
        # Current-state targets may legitimately omit A cells when all A cells already
        # meet the configured depth target. Direction is not itself a priority gate.
        sparse = [c for c in sr.FRONTIER_CELL_ORDER if focus['deficits'].get(c, 0) > 0]
        self.assertTrue(set(focus['targets']).issubset(set(sparse)))


    def test_matrix_balance_target_tracks_current_coverage(self):
        counts = {
            'knowledge-A': 7, 'knowledge-B': 16, 'knowledge-C': 1, 'knowledge-D': 0,
            'infrastructure-A': 5, 'infrastructure-B': 6, 'infrastructure-C': 6, 'infrastructure-D': 18,
            'conversion-A': 11, 'conversion-B': 6, 'conversion-C': 10, 'conversion-D': 6,
            'rules-A': 1, 'rules-B': 8, 'rules-C': 4, 'rules-D': 6,
        }
        with mock.patch.object(sr, 'frontier_matrix_coverage', return_value=(counts, 111, '')):
            focus = sr.frontier_gap_plan({}, sr.initial_scan_state({}))
        self.assertEqual(focus['median_count'], 6)
        self.assertEqual(focus['target_count'], 12)
        self.assertGreaterEqual(focus['upper_quartile'], 8)
        self.assertIn('knowledge-D', focus['targets'])
        self.assertIn('knowledge-C', focus['targets'])
        self.assertIn('rules-A', focus['targets'])
        self.assertIn('rules-C', focus['targets'])
        self.assertNotIn('infrastructure-D', focus['targets'])
        self.assertGreaterEqual(focus['undercovered_cells'], 10)

    def test_matrix_balance_target_is_bounded(self):
        counts = {c: 20 for c in sr.FRONTIER_CELL_ORDER}
        counts['knowledge-D'] = 0
        snap = sr.frontier_balance_snapshot(counts, {}, advance_cursor=False)
        self.assertEqual(snap['target_count'], 12)
        self.assertEqual(snap['targets'], ['knowledge-D'])
        self.assertEqual(sr.CONFIG['matrix_balance_rotation_profile_version'], 'v17.13.6-semantic-matrix-catchup')

    def test_equal_scarcity_does_not_bias_against_opening_cells(self):
        counts = {c: 2 for c in sr.FRONTIER_CELL_ORDER}
        with mock.patch.object(sr, 'frontier_matrix_coverage', return_value=(counts, [], '')):
            focus = sr.frontier_gap_plan({}, sr.initial_scan_state({}))
        self.assertTrue(any(c.endswith('-A') for c in focus['targets']))
        self.assertTrue(any(not c.endswith('-A') for c in focus['targets']))

    def test_gap_depth_bank_uses_zero_cells_first_then_sparse_targets(self):
        prev = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
        state = sr.initial_scan_state(prev)
        focus = sr.frontier_gap_plan(prev, state)
        bank = sr.frontier_gap_depth_bank(focus)
        profiles = sr.CONFIG['frontier_gap_scholarly_queries']
        allowed = {q for c in focus['targets'] for q in profiles[c]}
        self.assertTrue(bank)
        self.assertTrue(set(bank).issubset(allowed))
        if focus['empty_targets'] and len(focus['targets']) > len(focus['empty_targets']):
            nonempty = [c for c in focus['targets'] if c not in focus['empty_targets']]
            self.assertTrue(any(q in bank for c in nonempty for q in profiles[c]))
        fallback = sr.frontier_gap_depth_bank(focus, include_nonempty=True)
        self.assertGreaterEqual(len(fallback), len(bank))

    def test_material_current_change_can_be_c_candidate_without_pilot_wording(self):
        title = 'EU launches new quantum research infrastructure investment to reduce foreign compute dependence'
        self.assertTrue(sr.material_update_signal_text(title))
        self.assertTrue(sr.weak_signal_candidate_text(title, ''))
        self.assertTrue(sr.factual_news(title, ''))

    def test_generic_technology_launch_still_does_not_become_weak_signal(self):
        title = 'Company launches new consumer AI photo app in Europe'
        self.assertFalse(sr.material_update_signal_text(title))
        self.assertFalse(sr.factual_news(title, ''))

    def test_budget_is_twenty_minutes_but_scanner_has_matrix_depth_phase(self):
        cfg = sr.CONFIG
        self.assertEqual(cfg['scan_budget_seconds'], 1200)
        self.assertLessEqual(cfg['scan_finalize_reserve_seconds'], 60)
        self.assertGreaterEqual(cfg['frontier_gap_deepening_max_waves'], 24)
        self.assertGreaterEqual(cfg['frontier_gap_deepening_queries_per_wave'], 12)
        scanner = (ROOT / 'scripts' / 'scan_radar.py').read_text(encoding='utf-8')
        self.assertIn('Matrix-first depth wave', scanner)
        self.assertIn('depth_only: bool = False', scanner)
        self.assertIn('weak-signal follow-up', scanner)

    def test_new_allocation_profile_does_not_reset_ab_recall_profile(self):
        self.assertEqual(sr.CONFIG['recall_profile_version'], 'v17.13.1-eu-core-external-shock-english-evidence')
        self.assertEqual(sr.CONFIG['allocation_profile_version'], 'v17.13.6-semantic-matrix-catchup')
        self.assertEqual(sr.CONFIG['signal_discovery_version'], 'v17.7.4-direct-institutional-signals')


if __name__ == '__main__':
    unittest.main()
