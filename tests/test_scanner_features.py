from pathlib import Path
import importlib.util
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / 'scripts' / 'scan_radar.py'
spec = importlib.util.spec_from_file_location('radar_scan_feature_contract', SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)

class ScannerFeatureContractTests(unittest.TestCase):
    def test_current_profile_is_a_anchored_signal_model(self):
        self.assertIn('a-anchored', scan.SIGNAL_QUALITY_PROFILE_VERSION)

    def test_public_ab_corpus_can_grow_past_seed(self):
        data = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(len(data.get('strand_a', [])) + len(data.get('strand_b', [])), 200)

    def test_signal_retention_floor_is_sixty_days(self):
        import datetime as dt
        today = dt.date(2026, 9, 6)
        self.assertEqual(scan.weak_signal_retention_floor(today), today - dt.timedelta(days=60))

    def test_reader_products_exist(self):
        for rel in ('radar/index.html','frontier/index.html','trends/index.html','priorities/index.html','shocks/index.html','read/index.html'):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_construct_shock_toy_is_not_loaded(self):
        text = (ROOT / 'shocks' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('toy.js', text)
        self.assertNotIn('Construct one shock', text)

    def test_legacy_followup_can_be_used_for_historical_without_main_rescan(self):
        source = SCAN_PATH.read_text(encoding='utf-8')
        self.assertIn('legacy_historical_followup_via_main_workflow', source)

if __name__ == '__main__':
    unittest.main()
