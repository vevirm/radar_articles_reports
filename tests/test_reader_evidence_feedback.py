from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, rel):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


scan = load('radar_reader_feedback_scan', 'scripts/scan_radar.py')
shock = load('radar_reader_feedback_shock', 'scripts/shock_inference.py')


class ReaderEvidenceFeedbackTests(unittest.TestCase):
    def test_risk_feedback_pairs_support_with_resilience_search(self):
        previous = {
            'strategic_pathways': [{
                'title': 'Chip dependency', 'date': '2026-09-15', 'analytical_weight': 1.0,
                'strategic_classification': {'lenses': [{
                    'type': 'risk',
                    'passage': 'European semiconductor supply faces export controls and chip dependency.'
                }]}
            }]
        }
        qs = scan.strategic_pathway_feedback_queries(previous, 4)
        self.assertGreaterEqual(len(qs), 2)
        self.assertIn('semiconductor', qs[0].lower())
        self.assertIn('export controls', qs[0].lower())
        self.assertTrue(any('resilience' in q.lower() or 'substitution' in q.lower() for q in qs[1:]))

    def test_shock_feedback_pairs_hypothesis_with_absorber_search(self):
        state = {'dynamic_shocks': [{
            'asset_id': 'infrastructure', 'pressure_id': 'security_reclassification',
            'inference_score': 98, 'last_updated_at': '2026-09-15T00:00:00Z'
        }]}
        qs = shock.feedback_queries(state, 4)
        self.assertGreaterEqual(len(qs), 2)
        self.assertTrue(any('disruption' in q.lower() for q in qs))
        self.assertTrue(any('substitution' in q.lower() and 'resilience' in q.lower() for q in qs))

    def test_finding_context_feedback_stays_inside_existing_budget_and_balances_banks(self):
        previous = {
            'strand_a': [{'title': 'European semiconductor dependency', 'summary': 'EU research and innovation chip capability'}],
            'strategic_pathways': [{
                'title': 'Chip dependency', 'date': '2026-09-15', 'analytical_weight': 1.0,
                'strategic_classification': {'lenses': [{
                    'type': 'risk', 'passage': 'European semiconductor supply faces export controls.'
                }]}
            }],
            'high_order_inference': {'candidates': [{
                'status': 'watch', 'score': 90,
                'support_queries': ['higher order missing bridge query'],
                'falsifier_queries': ['higher order falsifier query']
            }]},
            'shock_inference': {'dynamic_shocks': [{
                'asset_id': 'infrastructure', 'pressure_id': 'security_reclassification',
                'inference_score': 98, 'last_updated_at': '2026-09-15T00:00:00Z'
            }]}
        }
        qs = scan.finding_context_query_bank(previous, 12)
        self.assertLessEqual(len(qs), 12)
        self.assertIn('higher order missing bridge query', qs)
        self.assertIn('higher order falsifier query', qs)
        self.assertTrue(any('semiconductor' in q.lower() and 'export controls' in q.lower() for q in qs))
        self.assertTrue(any('substitution' in q.lower() and 'resilience' in q.lower() for q in qs))

    def test_deep_scan_semantic_pathway_keeps_authoritative_provenance(self):
        item = {
            'title': 'Choose Europe for Science',
            'source': 'European Commission',
            'date': '2026-01-01',
            'link': 'https://ec.europa.eu/example',
            'source_tier': 'Tier 1',
            'semantic_source': 'deep_scan_v2',
            'deep_scan_authoritative': True,
            'admission_status': 'keep',
            'reader_title': 'Choose Europe for Science',
            'reader_what': 'An EU pilot aims to make research careers more attractive.',
            'reader_why': 'Stable careers can improve Europe’s ability to retain research talent.',
            'reader_more': 'The MSCA pilot action tackles precarity and aims to turn brain drain into brain gain.',
        }
        # Scope/source gates are intentionally isolated here: this test protects the
        # semantic provenance written by strategic_pathway_record, not those gates.
        old_quality = scan.strategic_source_quality_gate
        old_scope = scan.strategic_pathway_scope_gate
        old_eu = scan.eu_evidence
        try:
            scan.strategic_source_quality_gate = lambda _item: (True, 'test')
            scan.strategic_pathway_scope_gate = lambda _text, _corpus: (True, 'test')
            scan.eu_evidence = lambda *_args: ('direct', ['test'])
            row = scan.strategic_pathway_record(item, [])
        finally:
            scan.strategic_source_quality_gate = old_quality
            scan.strategic_pathway_scope_gate = old_scope
            scan.eu_evidence = old_eu
        self.assertIsNotNone(row)
        self.assertEqual(row['strategic_classification_source'], 'deep_scan_v2_semantics')
        self.assertTrue(row['deep_scan_authoritative'])
        self.assertEqual(row['reader_why'], item['reader_why'])


if __name__ == '__main__':
    unittest.main()
