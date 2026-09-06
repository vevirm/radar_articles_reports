import importlib.util
import json
import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / 'scripts' / 'scan_radar.py'
spec = importlib.util.spec_from_file_location('radar_scan_v172023', SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class MainRadarRecallRecoveryTests(unittest.TestCase):
    def test_document_level_eu_ri_geopolitics_does_not_require_adjacent_sentences(self):
        title = 'Dependence in advanced scientific instrumentation'
        abstract = (
            'This report examines laboratory access to specialised detector systems and research infrastructure. '
            'Supply bottlenecks can interrupt experimental programmes and delay technology development. '
            'Foreign suppliers control several critical components and replacement capacity is limited. '
            'The evidence base covers the European Union research system. '
            'European laboratories and innovation programmes face common procurement constraints.'
        )
        ok, reason, evidence = scan.source_supported_eu_ri_centrality_rescue(
            title, abstract, '', 'eu_or_ri_only_incidental'
        )
        self.assertTrue(ok)
        self.assertIn('geopolitical', reason)
        self.assertTrue(evidence)

    def test_document_level_rescue_does_not_promote_generic_eu_innovation(self):
        title = 'Administrative coordination in public innovation programmes'
        abstract = (
            'The report reviews implementation practices across the European Union. '
            'European agencies use common reporting templates. '
            'Research funding and innovation programmes are described in several sections. '
            'The paper compares administrative calendars and reporting formats.'
        )
        ok, reason, evidence = scan.source_supported_eu_ri_centrality_rescue(
            title, abstract, '', 'eu_or_ri_only_incidental'
        )
        self.assertFalse(ok)
        self.assertEqual(reason, 'eu_or_ri_only_incidental')
        self.assertEqual(evidence, [])

    def test_trusted_tier3_title_only_can_pass_when_all_three_dimensions_are_explicit(self):
        title = 'Research security in European universities under US-China technology competition'
        ev = scan.gate_scope(title, '', '', 3, source_kind='scholarly')
        self.assertTrue(ev['a_pass'])
        self.assertEqual(ev['aboutness_reason'], 'metadata_title_high_recall')

    def test_tier3_title_only_generic_eu_ri_still_needs_text(self):
        title = 'Innovation performance in European universities'
        ev = scan.gate_scope(title, '', '', 3, source_kind='scholarly')
        self.assertFalse(ev['a_pass'])
        self.assertEqual(ev['aboutness_reason'], 'insufficient_text')

    def test_semantic_publication_date_recovers_common_cms_markup(self):
        soup = BeautifulSoup(
            '<html><body><h1>Report</h1><span class="publication-date">4 September 2026</span></body></html>',
            'html.parser',
        )
        self.assertEqual(str(scan._semantic_publication_date(soup, 'Report')), '2026-09-04')

    def test_openalex_failure_reallocation_is_large_and_rotating(self):
        self.assertGreaterEqual(scan.CONFIG.get('source_failure_reallocation_crossref_queries', 0), 24)
        self.assertGreaterEqual(scan.CONFIG.get('source_failure_reallocation_crossref_journals', 0), 16)
        self.assertGreaterEqual(scan.CONFIG.get('source_failure_reallocation_institution_sources', 0), 20)

    def test_curator_examples_receive_more_rotating_attention(self):
        self.assertGreaterEqual(scan.CONFIG.get('curator_seed_query_bank_size', 0), 24)
        self.assertGreaterEqual(scan.CONFIG.get('curator_seed_queries_per_scan', 0), 10)
        self.assertGreaterEqual(scan.CONFIG.get('manual_recovery_urls_per_scan', 0), 10)

    def test_source_expansion_completion_preserves_rotation_without_reopening_global_backfill(self):
        previous = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
        old_oa = int((previous.get('scan_state') or {}).get('openalex_cursor', 0))
        old_cr = int((previous.get('scan_state') or {}).get('crossref_broad_cursor', 0))
        state = scan.initial_scan_state(previous)
        self.assertEqual(state['openalex_cursor'], old_oa)
        self.assertEqual(state['crossref_broad_cursor'], old_cr)
        # v17.20.48+ deliberately retired the old four-month global source-expansion
        # reset.  New sources are picked up by bounded rotating depth lanes instead.
        self.assertFalse(state.get('source_expansion_backfill_reopened'))
        self.assertFalse(state.get('recall_reset_this_run'))


if __name__ == '__main__':
    unittest.main()
