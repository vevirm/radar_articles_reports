import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / 'scripts' / 'scan_radar.py'
spec = importlib.util.spec_from_file_location('radar_scan_v172012', SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class RecallFirstDiscoveryTests(unittest.TestCase):
    def test_source_universe_is_hundreds_not_a_handful(self):
        self.assertTrue(scan.CONFIG.get('crossref_full_source_census_each_scan'))
        self.assertTrue(scan.CONFIG.get('institution_full_census_each_scan'))
        self.assertGreaterEqual(len(scan.CONFIG.get('institution_sources', [])), 190)
        self.assertGreaterEqual(len(scan.CONFIG.get('crossref_priority_journals', [])), 160)
        self.assertGreaterEqual(
            len(scan.CONFIG.get('institution_sources', [])) + len(scan.CONFIG.get('crossref_priority_journals', [])),
            350,
        )

    def test_base_query_slice_is_no_longer_tiny(self):
        self.assertGreaterEqual(scan.CONFIG.get('scholarly_base_queries_per_scan', 0), 30)
        self.assertGreaterEqual(scan.CONFIG.get('openalex_queries_per_scan', 0), 90)
        self.assertGreaterEqual(scan.CONFIG.get('crossref_broad_queries_per_scan', 0), 100)

    def test_missing_abstract_does_not_hide_obvious_tier2_eu_ri_paper(self):
        ev = scan.gate_scope(
            'European research security and innovation policy',
            '',
            '',
            2,
            source_kind='scholarly',
        )
        self.assertTrue(ev['a_pass'])
        self.assertEqual(ev['text_mode'], 'metadata_only')
        self.assertEqual(ev['aboutness_reason'], 'metadata_title_high_recall')

    def test_missing_abstract_is_not_a_waiver_for_low_tier_or_vague_title(self):
        ev = scan.gate_scope(
            'European research security and innovation policy',
            '',
            '',
            3,
            source_kind='scholarly',
        )
        self.assertFalse(ev['a_pass'])
        vague = scan.gate_scope('European policy perspectives', '', '', 1, source_kind='scholarly')
        self.assertFalse(vague['a_pass'])

    def test_institution_page_queue_is_breadth_first(self):
        sources = [
            {'name': 'One', 'domain': 'one.example', 'tier': 1},
            {'name': 'Two', 'domain': 'two.example', 'tier': 1},
            {'name': 'Three', 'domain': 'three.example', 'tier': 1},
        ]
        jobs = {
            'one.example': [(f'https://one.example/p{i}', 'One', 1, f'one{i}') for i in range(5)],
            'two.example': [(f'https://two.example/p{i}', 'Two', 1, f'two{i}') for i in range(5)],
            'three.example': [(f'https://three.example/p{i}', 'Three', 1, f'three{i}') for i in range(5)],
        }
        parsed = []

        def fake_discover(src, *args, **kwargs):
            return jobs[src['domain']], None

        def fake_parse(url, source, tier, *args, **kwargs):
            parsed.append(source)
            return {'title': url, 'source': source, 'strand': 'A'}

        old_max = scan.CONFIG.get('institution_max_pages')
        old_workers = scan.CONFIG.get('institution_discovery_workers')
        scan.CONFIG['institution_max_pages'] = 4
        scan.CONFIG['institution_discovery_workers'] = 1
        try:
            with mock.patch.object(scan, '_discover_domain', side_effect=fake_discover), \
                 mock.patch.object(scan, 'parse_institution_page', side_effect=fake_parse):
                out = scan.collect_institutions(
                    scan.dt.date.today(), [], bootstrap=False, sources_override=sources,
                    stage_deadline=None, execution_stats={}
                )
        finally:
            scan.CONFIG['institution_max_pages'] = old_max
            scan.CONFIG['institution_discovery_workers'] = old_workers
        self.assertEqual(len(out), 4)
        # Every source gets one parser slot before any source gets a second.
        self.assertTrue({'One', 'Two', 'Three'}.issubset(set(parsed)))


if __name__ == '__main__':
    unittest.main()
