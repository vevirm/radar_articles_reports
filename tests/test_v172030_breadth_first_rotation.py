import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / 'scripts' / 'scan_radar.py'
spec = importlib.util.spec_from_file_location('radar_scan_v172030', SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class BreadthFirstRotationTests(unittest.TestCase):
    def test_crossref_plan_cannot_put_all_easy_sources_before_broad_rotation(self):
        plan = scan.crossref_execution_plan(
            [f'q{i}' for i in range(10)],
            [(f'journal{i}', f'pq{i}') for i in range(10)],
            [f'source{i}' for i in range(10)],
            broad_weight=2,
        )
        first_eight = [kind for kind, _ in plan[:8]]
        self.assertEqual(first_eight, ['broad','broad','source','priority','broad','broad','source','priority'])
        self.assertGreater(first_eight.count('broad'), first_eight.count('source'))
        self.assertGreater(first_eight.count('broad'), first_eight.count('priority'))

    def test_crossref_breadth_gets_protected_share_in_current_configuration(self):
        self.assertGreaterEqual(int(scan.CONFIG.get('crossref_broad_execution_weight', 0) or 0), 2)
        self.assertFalse(scan.CONFIG.get('crossref_priority_query_depth_enabled'))
        lanes = set(scan.CONFIG.get('crossref_primary_deep_lanes', []))
        self.assertIn('explore', lanes)
        self.assertNotIn('low-yield-fresh', lanes)

    def test_openalex_primary_rotation_is_breadth_first_but_keeps_explicit_depth_lanes(self):
        lanes = set(scan.CONFIG.get('openalex_primary_deep_lanes', []))
        self.assertEqual(lanes, {'explore','gap','finding-context','curator-seed'})
        src = SCAN_PATH.read_text(encoding='utf-8')
        self.assertIn('lane not in deep_lanes', src)
        self.assertIn('Breadth-first primary discovery', src)

    def test_five_item_target_and_hard_quality_gate_are_unchanged(self):
        self.assertEqual(scan.CONFIG.get('target_new_ab_per_scan'), 5)
        bad = scan.gate_scope(
            'Innovation performance in European universities',
            'A comparative study of European university innovation programmes and administrative coordination.',
            '', 2, source_kind='scholarly'
        )
        good = scan.gate_scope(
            'Research security in European universities under US-China technology competition',
            'European universities face research-security constraints as US-China competition changes scientific collaboration and technology access.',
            '', 2, source_kind='scholarly'
        )
        self.assertFalse(bad['a_pass'])
        self.assertTrue(good['a_pass'])
        self.assertFalse(scan.CONFIG.get('low_yield_full_rescue_run_enabled'))


if __name__ == '__main__':
    unittest.main()
