from pathlib import Path
import importlib.util
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / 'scripts' / 'scan_radar.py'
spec = importlib.util.spec_from_file_location('radar_scan_current_contract', SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)

class CurrentRepositoryContractTests(unittest.TestCase):
    def test_live_or_seed_corpus_is_valid(self):
        data = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
        self.assertIsInstance(data, dict)
        total = len(data.get('strand_a', [])) + len(data.get('strand_b', []))
        self.assertGreaterEqual(total, 200)

    def test_ab_is_cumulative_not_capped(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        self.assertEqual(int(cfg.get('max_corpus_per_strand', 0) or 0), 0)

    def test_c_retention_is_sixty_days_and_requires_a_anchor(self):
        self.assertEqual(scan.WEAK_SIGNAL_RETENTION_DAYS, 60)
        source = SCAN_PATH.read_text(encoding='utf-8')
        self.assertIn('Strand-A anchor required', source)

    def test_main_budget_is_twenty_four_minutes(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        self.assertEqual(int(cfg.get('scan_budget_seconds', 0)), 1440)

    def test_legacy_hourly_workflow_is_mapped_to_four_hour_slots(self):
        text = (ROOT / '.github' / 'workflows' / 'radar-scan.yml').read_text(encoding='utf-8')
        if scan.legacy_workflow_schedule_compatibility_active(text):
            import datetime as dt
            completed = dt.datetime(2026, 9, 6, 20, 23, tzinfo=dt.timezone.utc)
            adjusted = scan.scheduler_state_completed_at(completed, text)
            next_slot = scan.next_automatic_scan_slot(completed)
            self.assertEqual(adjusted, next_slot - dt.timedelta(hours=6))
        else:
            self.assertIn("cron: '17 */4 * * *'", text)

    def test_runtime_serialization_guard_is_present(self):
        guard = (ROOT / 'scripts' / 'scanner_run_guard.py').read_text(encoding='utf-8')
        hist = (ROOT / 'historical' / 'scan_historical.py').read_text(encoding='utf-8')
        main = SCAN_PATH.read_text(encoding='utf-8')
        self.assertIn('defer_if_peer_scanner_active', guard)
        self.assertIn('defer_if_peer_scanner_active("main"', main)
        self.assertIn('defer_if_peer_scanner_active("historical"', hist)

    def test_checkout_credentials_are_not_persisted(self):
        text = (ROOT / '.github' / 'workflows' / 'radar-scan.yml').read_text(encoding='utf-8')
        self.assertIn('persist-credentials: false', text)

if __name__ == '__main__':
    unittest.main()
