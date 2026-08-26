import json
import sys, types
import unittest
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
        # Balanced allocation must follow actual scarcity; a fully covered A cell
        # is not forced into the target set merely to satisfy a quadrant quota.
        self.assertTrue(all(focus['deficits'].get(c, 0) > 0 for c in focus['targets']))

    def test_gap_depth_bank_uses_zero_cells_first_then_sparse_targets(self):
        prev = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
        state = sr.initial_scan_state(prev)
        focus = sr.frontier_gap_plan(prev, state)
        bank = sr.frontier_gap_depth_bank(focus)
        profiles = sr.CONFIG['frontier_gap_scholarly_queries']
        if focus['empty_targets']:
            expected = []
            for i in range(max(len(profiles[c]) for c in focus['empty_targets'])):
                for c in focus['empty_targets']:
                    if i < len(profiles[c]):
                        expected.append(profiles[c][i])
            self.assertEqual(bank, expected)
        else:
            allowed = {q for c in focus['targets'] for q in profiles[c]}
            self.assertTrue(bank)
            self.assertTrue(set(bank).issubset(allowed))
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
        self.assertEqual(sr.CONFIG['recall_profile_version'], 'v17.7.2-source-first-contextual-recall')
        self.assertEqual(sr.CONFIG['allocation_profile_version'], 'v17.8.2-balanced-frontier')
        self.assertEqual(sr.CONFIG['signal_discovery_version'], 'v17.7.4-direct-institutional-signals')


if __name__ == '__main__':
    unittest.main()
