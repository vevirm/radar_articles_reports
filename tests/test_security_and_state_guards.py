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
        self.assertTrue(bool(cfg.get('full_budget_continuation_enabled')))
        self.assertLessEqual(int(cfg.get('scan_finalize_reserve_seconds', 999)), 45)

    def test_main_spends_early_finish_time_on_more_research(self):
        source = SCAN_PATH.read_text(encoding='utf-8')
        self.assertIn('Full-budget continuation', source)
        self.assertIn('full_budget_continuation', source)
        self.assertIn('oa_unavailable = bool(oa_failed or oa_rate_limited)', source)
        self.assertIn('cr_unavailable = bool(cr_failed or cr_rate_limited)', source)

    def test_legacy_hourly_workflow_is_mapped_to_four_hour_slots(self):
        # GitHub browser bulk upload can leave .github/workflows untouched while
        # replacing ordinary repo files. Do not fail the scanner merely because
        # the retained hidden workflow is the known legacy hourly+6h-gate form.
        text = (ROOT / '.github' / 'workflows' / 'radar-scan.yml').read_text(encoding='utf-8')
        if scan.legacy_workflow_schedule_compatibility_active(text):
            import datetime as dt
            completed = dt.datetime(2026, 9, 6, 20, 23, tzinfo=dt.timezone.utc)
            adjusted = scan.scheduler_state_completed_at(completed, text)
            next_slot = scan.next_automatic_scan_slot(completed)
            self.assertEqual(adjusted, next_slot - dt.timedelta(hours=6))
            return
        # Current workflow: accept equivalent YAML quoting/spelling, and verify
        # the actual four-hour UTC hours rather than a literal source substring.
        import re
        crons = re.findall(r"cron\s*:\s*['\"]?([^'\"\n]+)", text)
        normalized = {c.strip() for c in crons}
        self.assertTrue({'17 */4 * * *', '17 0,4,8,12,16,20 * * *'} & normalized)

    def test_main_historical_are_two_hours_offset_and_share_queue(self):
        main = (ROOT / '.github' / 'workflows' / 'radar-scan.yml').read_text(encoding='utf-8')
        hist = (ROOT / '.github' / 'workflows' / 'historical-scan.yml').read_text(encoding='utf-8')
        if scan.legacy_workflow_schedule_compatibility_active(main):
            # Safe compatibility contract for repositories where the browser upload
            # did not replace hidden workflow YAML. The visible scanner contains the
            # legacy scheduler mapping and sequential Historical fallback, so this
            # known state must not block Main before it can scan.
            source = SCAN_PATH.read_text(encoding='utf-8')
            self.assertIn('legacy_historical_followup_via_main_workflow', source)
            self.assertIn('scheduler_state_completed_at', source)
            self.assertIn('defer_if_peer_scanner_active("main"', source)
            return

        import re
        main_crons = {c.strip() for c in re.findall(r"cron\s*:\s*['\"]?([^'\"\n]+)", main)}
        hist_crons = {c.strip() for c in re.findall(r"cron\s*:\s*['\"]?([^'\"\n]+)", hist)}
        self.assertTrue({'17 */4 * * *', '17 0,4,8,12,16,20 * * *'} & main_crons)
        self.assertIn('17 2,6,10,14,18,22 * * *', hist_crons)
        self.assertIn('group: ri-radar-research-scanners', main)
        self.assertIn('group: ri-radar-research-scanners', hist)
        self.assertIn('cancel-in-progress: false', main)
        self.assertIn('cancel-in-progress: false', hist)

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
