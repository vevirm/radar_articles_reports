import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / 'scripts' / 'scan_radar.py'
spec = importlib.util.spec_from_file_location('radar_scan_v172022', SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class RecallWithoutTopicDriftTests(unittest.TestCase):
    def test_separated_eu_ri_evidence_can_be_rescued_when_geopolitical_context_is_real(self):
        ev = scan.gate_scope(
            'Technology exposure and strategic resilience',
            (
                'This report examines the European Union and its exposure to foreign suppliers. '
                'The analysis considers policy choices over the coming decade. '
                'Export controls and dependence on non-EU suppliers are reshaping access to critical inputs. '
                'Research capacity and innovation ecosystems rely on secure access to semiconductor infrastructure.'
            ),
            '',
            1,
            source_kind='institutional',
        )
        self.assertTrue(ev['a_pass'])
        self.assertEqual(ev['eu_relevance'], 'direct')
        self.assertIn('geopolitical', ev['centrality_reason'])

    def test_same_separated_structure_is_not_rescued_for_generic_eu_ri_policy(self):
        ev = scan.gate_scope(
            'Administrative arrangements for public policy',
            (
                'This report examines the European Union and its administrative framework. '
                'The analysis describes implementation arrangements and reporting cycles. '
                'Several procedural changes are reviewed. '
                'Research capacity and innovation ecosystems are discussed as one policy field.'
            ),
            '',
            1,
            source_kind='institutional',
        )
        self.assertFalse(ev['a_pass'])

    def test_curator_examples_seed_adjacent_discovery_queries(self):
        queries = scan.curator_seed_query_bank(16)
        self.assertTrue(queries)
        self.assertLessEqual(len(queries), 16)
        self.assertTrue(any('Europe' in q or 'EU ' in q for q in queries))

    def test_high_output_journal_depth_and_institution_depth_are_enabled(self):
        self.assertGreaterEqual(scan.CONFIG.get('crossref_source_first_depth_pages_max', 0), 3)
        self.assertGreaterEqual(scan.CONFIG.get('institution_pages_per_domain', 0), 12)
        self.assertGreaterEqual(scan.CONFIG.get('crossref_missing_abstract_enrichment_per_scan', 0), 100)


if __name__ == '__main__':
    unittest.main()
