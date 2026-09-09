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
    def test_current_profile_allows_independent_theme_aligned_c(self):
        self.assertIn('independent-c', scan.SIGNAL_QUALITY_PROFILE_VERSION)
        self.assertTrue(bool(scan.CONFIG.get('c_unanchored_rescue_enabled')))

    def test_v235_eu_scope_uses_substance_not_single_member_state_word(self):
        rel, evidence = scan.eu_evidence(
            'Knowledge transfer through disciplinary lenses: insights from German universities',
            'This study examines knowledge transfer practices and research collaboration.', ''
        )
        self.assertEqual(rel, 'unclear')
        self.assertTrue(evidence)
        rel2, evidence2 = scan.eu_evidence(
            'Research security and strategic capabilities',
            'DG RTD examines research security, research infrastructures and strategic dependencies.', ''
        )
        self.assertEqual(rel2, 'direct')
        self.assertTrue(any('dg rtd' in x.lower() for x in evidence2))

    def test_v235_strand_mix_and_b_horizon_are_targets_not_quotas(self):
        self.assertEqual((int(scan.CONFIG.get('target_new_a_per_scan',0)), int(scan.CONFIG.get('target_new_b_per_scan',0)), int(scan.CONFIG.get('target_new_c_per_scan',0))), (8,1,3))
        self.assertIn('Never reject', str(scan.CONFIG.get('target_item_mix_rule','')))
        self.assertGreaterEqual(int(scan.CONFIG.get('b_method_lookback_years',0)), 10)

    def test_v235_research_analysis_platform_can_be_unlabelled_commentary(self):
        self.assertTrue(scan.trusted_unlabelled_commentary_source('', 'techpolicy.press', ''))
        self.assertTrue(scan.trusted_unlabelled_commentary_source('', 'blogs.lse.ac.uk', ''))

    def test_v235_project_word_is_not_an_automatic_a_rejection(self):
        self.assertIsNone(scan.document_exclusion_reason(
            'Project-based funding and strategic autonomy',
            'Analysis of European research and innovation funding, strategic dependencies and policy implications.'
        ))
        self.assertEqual(
            scan.document_exclusion_reason(
                'Horizon Europe project NOVA',
                'The project website lists partners, work packages, meetings and deliverables.'
            ),
            'hard exclusion: project page'
        )

    def test_v235_facility_word_can_be_disambiguated_by_substantive_analysis(self):
        self.assertIsNone(scan.document_exclusion_reason(
            'European laboratory infrastructure',
            'Policy brief assessing research security, strategic dependencies and governance implications for EU R&I facilities.'
        ))
        self.assertEqual(
            scan.document_exclusion_reason(
                'New laboratory facility',
                'Opening hours, user access, equipment and booking information.'
            ),
            'hard exclusion: facility/laboratory page'
        )

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
