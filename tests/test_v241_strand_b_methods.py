from pathlib import Path
import importlib.util
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / 'scripts' / 'scan_radar.py'
spec = importlib.util.spec_from_file_location('radar_scan_b241', SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class StrandBMethodsContractTests(unittest.TestCase):
    def b(self, title, abstract):
        return scan._b_method_evidence(title, abstract, '', 'scholarly', 1)

    def test_method_review_and_comparison_are_b(self):
        ok, families, bridge, _, route = self.b(
            'Comparing horizon scanning methods for emerging technologies in science and innovation policy',
            'This systematic review compares horizon scanning methods, evaluates their quality criteria and discusses method selection for research and innovation policy.'
        )
        self.assertTrue(ok)
        self.assertIn('horizon scanning', families)
        self.assertTrue(bridge)
        self.assertEqual(route, 'future-method-study')

    def test_method_testing_is_b(self):
        ok, _, bridge, _, _ = self.b(
            'Evaluating Delphi and scenario planning for research priority setting',
            'We test and compare the reliability, validity and transferability of Delphi and scenario planning as foresight methods for science and technology policy.'
        )
        self.assertTrue(ok)
        self.assertIn('reliability', bridge.lower())

    def test_ai_horizon_scanning_method_evaluation_is_b(self):
        ok, _, _, _, _ = self.b(
            'LLM-based horizon scanning for emerging technologies: a methodological evaluation',
            'We evaluate an LLM-based horizon scanning method for detecting emerging technologies in research and innovation policy, benchmarking reliability and reproducibility.'
        )
        self.assertTrue(ok)

    def test_pure_delphi_application_is_not_b(self):
        ok, *_ = self.b(
            'Using Delphi to prioritise AI investments in European universities',
            'We apply Delphi to rank artificial intelligence investment priorities in European universities. The study reports the resulting priorities.'
        )
        self.assertFalse(ok)

    def test_scenario_case_application_is_not_b(self):
        ok, *_ = self.b(
            'Scenario planning for a regional tourism strategy',
            'This case study uses scenario planning to develop tourism options for a local region.'
        )
        self.assertFalse(ok)

    def test_soft_mix_and_b_attention(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text())
        self.assertEqual((cfg['target_new_a_per_scan'], cfg['target_new_b_per_scan'], cfg['target_new_c_per_scan']), (8, 1, 3))
        self.assertEqual(cfg['queries_b_method_recent_per_scan'] + cfg['queries_b_method_foundational_per_scan'], 12)
        self.assertGreaterEqual(cfg['b_method_protected_scholarly_queries_per_source'], 6)
        self.assertGreaterEqual(len(cfg['b_method_journal_watchlist']), 10)
        self.assertIn('Never reject', cfg['target_item_mix_rule'])

    def test_b_is_recent_first_with_foundational_fallback(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text())
        self.assertEqual(cfg['b_method_recent_lookback_years'], 5)
        self.assertEqual(cfg['b_method_lookback_years'], 15)
        self.assertGreater(cfg['queries_b_method_recent_per_scan'], cfg['queries_b_method_foundational_per_scan'])
        self.assertTrue(any('systematic review' in q for q in cfg['queries_b_method_recent']))
        self.assertTrue(any('evaluation' in q for q in cfg['queries_b_method_recent']))


if __name__ == '__main__':
    unittest.main()
