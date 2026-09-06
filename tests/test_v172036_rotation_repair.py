import importlib.util
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / 'scripts' / 'scan_radar.py'
spec = importlib.util.spec_from_file_location('radar_scan_v172036', SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}
        self.headers = {}
    def json(self):
        return self._payload


class RotationRepairTests(unittest.TestCase):
    def test_openalex_429_does_not_advance_success_cursor(self):
        old_retries = scan.CONFIG.get('scholarly_public_retries')
        scan.CONFIG['scholarly_public_retries'] = 0
        stats = {}
        warnings = []
        try:
            with mock.patch.object(scan, 'openalex_get', return_value=_Resp(429)):
                rows = scan.collect_openalex(
                    scan.DATE_FLOOR, warnings, ['EU research security test'],
                    time.monotonic() + 10, execution_stats=stats,
                )
        finally:
            scan.CONFIG['scholarly_public_retries'] = old_retries
        self.assertEqual(rows, [])
        self.assertEqual(stats.get('openalex_queries', set()), set())
        self.assertTrue(scan.source_stage_rate_limited(warnings, 'openalex'))

    def test_crossref_429_does_not_advance_success_cursor(self):
        old_retries = scan.CONFIG.get('scholarly_public_retries')
        scan.CONFIG['scholarly_public_retries'] = 0
        stats = {}
        warnings = []
        try:
            with mock.patch.object(scan.SESSION, 'get', return_value=_Resp(429)):
                rows = scan.collect_crossref(
                    scan.DATE_FLOOR, warnings, ['EU research security test'], [], [],
                    time.monotonic() + 10, execution_stats=stats,
                )
        finally:
            scan.CONFIG['scholarly_public_retries'] = old_retries
        self.assertEqual(rows, [])
        self.assertEqual(stats.get('crossref_broad_queries', set()), set())
        self.assertTrue(scan.source_stage_rate_limited(warnings, 'crossref'))

    def test_crossref_primary_broad_query_uses_one_page_one_request(self):
        old_retries = scan.CONFIG.get('scholarly_public_retries')
        old_second = scan.CONFIG.get('crossref_primary_second_lane_enabled')
        scan.CONFIG['scholarly_public_retries'] = 0
        scan.CONFIG['crossref_primary_second_lane_enabled'] = False
        stats = {}
        try:
            with mock.patch.object(scan.SESSION, 'get', return_value=_Resp(200, {'message': {'items': []}})) as get:
                scan.collect_crossref(
                    scan.DATE_FLOOR, [], ['EU research security test'], [], [],
                    time.monotonic() + 10, execution_stats=stats,
                )
                self.assertEqual(get.call_count, 1)
        finally:
            scan.CONFIG['scholarly_public_retries'] = old_retries
            scan.CONFIG['crossref_primary_second_lane_enabled'] = old_second
        self.assertEqual(stats.get('crossref_broad_queries'), {'EU research security test'})

    def test_low_yield_is_depth_rotation_and_has_two_bounded_waves(self):
        src = SCAN_PATH.read_text(encoding='utf-8')
        self.assertIn('low-yield-depth', src)
        self.assertIn('fresh_exec, True', src)
        self.assertEqual(scan.CONFIG.get('low_yield_fresh_rotation_max_waves'), 2)
        self.assertEqual(scan.CONFIG.get('target_new_ab_per_scan'), 5)

    def test_known_false_positives_cannot_be_resurrected(self):
        self.assertIn(scan.normalized('Advancing the WEFE nexus: Expert insights on implementation and challenges'), scan.A_RETIRED_EXACT_TITLES)
        self.assertIn(scan.normalized('“I understand more what works”: Evaluating an intervention developed to support dramatherapists in writing their first clinical case study'), scan.A_RETIRED_EXACT_TITLES)

    def test_four_to_six_month_fallback_can_use_good_peer_reviewed_journals(self):
        good = {
            'source_tier': 'Tier 2 priority journal',
            'type': 'peer-reviewed article',
            'source': 'International Affairs',
            'link': 'https://doi.org/10.1234/example',
        }
        weak = {
            'source_tier': 'Tier 3 preprint',
            'type': 'preprint',
            'source': 'arXiv',
            'link': 'https://arxiv.org/abs/1234.5678',
        }
        self.assertTrue(scan.extended_high_quality_merit(good))
        self.assertFalse(scan.extended_high_quality_merit(weak))


if __name__ == '__main__':
    unittest.main()
