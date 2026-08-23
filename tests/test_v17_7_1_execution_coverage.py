from pathlib import Path
import json
import unittest
from unittest.mock import patch

from scripts import scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


class ExecutedRotationTests(unittest.TestCase):
    def test_rotation_advances_only_over_contiguous_executed_work(self):
        bank = ['q0', 'q1', 'q2', 'q3', 'q4']
        planned, _, _ = sr.rotating_batch(bank, 1, 3)
        self.assertEqual(planned, ['q1', 'q2', 'q3'])
        cursor, wrapped, consumed = sr.committed_rotation_cursor(bank, 1, planned, {'q1', 'q3'})
        self.assertEqual(cursor, 2)
        self.assertFalse(wrapped)
        self.assertEqual(consumed, 1)

    def test_budget_warning_is_not_source_failure(self):
        warnings = ['Crossref scan budget reached; remaining queued scholarly queries skipped']
        self.assertFalse(sr.source_stage_failed(warnings, 'crossref'))

    def test_fatal_warning_still_is_source_failure(self):
        warnings = ['Crossref fatal stage error: RuntimeError: upstream unavailable']
        self.assertTrue(sr.source_stage_failed(warnings, 'crossref'))


class RecallExecutionConfigTests(unittest.TestCase):
    def test_exploration_is_wider_but_live_gap_horizon_is_preserved(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        self.assertEqual(cfg['frontier_gap_historical_lookback_months'], 0)
        self.assertGreaterEqual(cfg['openalex_exploration_queries_per_scan'], 12)
        self.assertGreaterEqual(cfg['crossref_exploration_queries_per_scan'], 10)
        self.assertGreaterEqual(cfg['queries_b_method_per_scan'], 10)
        self.assertLess(cfg['quiet_scan_rescue_min_seconds_remaining'], 260)

    def test_doi_landing_metadata_can_recover_missing_abstract(self):
        class R:
            status_code = 200
            headers = {'content-type': 'text/html'}
            text = '<html><head><meta name="citation_abstract" content="We develop a new forecasting methodology for research and innovation trajectories under strategic uncertainty, using publication and patent signals to identify emerging technology pathways and future capability shifts across science and technology systems."></head></html>'
        with patch.object(sr, 'deadline_reached', return_value=False), patch.object(sr.SESSION, 'get', return_value=R()):
            text = sr.doi_landing_abstract('10.1234/example', 3)
        self.assertIn('forecasting methodology', text)
        self.assertGreaterEqual(len(text.split()), 20)


if __name__ == '__main__':
    unittest.main()
