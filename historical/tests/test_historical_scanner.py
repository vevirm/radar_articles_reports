from pathlib import Path
import importlib.util
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'historical' / 'scan_historical.py'
spec = importlib.util.spec_from_file_location('historical_current_contract', PATH)
H = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = H
spec.loader.exec_module(H)

class HistoricalCurrentContractTests(unittest.TestCase):
    def test_budget_is_ten_minutes(self):
        self.assertEqual(H.BUDGET_SECONDS, 600)


    def test_full_ten_minute_research_window(self):
        self.assertEqual(H.MIN_RUNTIME_SECONDS, 600)
        self.assertLessEqual(H.FINALIZE_MARGIN_SECONDS, 10)
        source = PATH.read_text(encoding='utf-8')
        self.assertIn('while budget_ok(FINALIZE_MARGIN_SECONDS)', source)
        self.assertNotIn('current_new<target_new and budget_ok', source)

    def test_cutoff_is_strictly_older_than_six_months(self):
        self.assertEqual(H.MAIN_RADAR_WINDOW_MONTHS, 6)
        self.assertEqual(H.DATE_TO, H.CUTOFF_EXCLUSIVE - H.dt.timedelta(days=1))

    def test_historical_is_ab_only(self):
        source = PATH.read_text(encoding='utf-8')
        self.assertIn('main_gate_scope', source)
        self.assertIn('main_final_ab_candidate_worthiness', source)

    def test_existing_archive_loads(self):
        data = json.loads((ROOT / 'historical' / 'historical.json').read_text(encoding='utf-8'))
        self.assertIsInstance(data.get('items'), list)
        self.assertGreater(len(data['items']), 0)

if __name__ == '__main__':
    unittest.main()
