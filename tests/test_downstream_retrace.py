import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import downstream_retrace as dr


class DownstreamRetraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
        cls.revalidation = dr.latest_revalidation_report(ROOT)
        cls.rebuilt, cls.report = dr.retrace_document(
            copy.deepcopy(cls.original),
            now='2026-09-11T01:15:00Z',
            revalidation_report=cls.revalidation,
        )

    def test_current_uploaded_cleaned_radar_retraces_to_zero_orphans(self):
        self.assertEqual(self.report['diagnostics']['orphan_references_remaining'], 0)
        self.assertTrue(self.report['integrity_check']['passed'])
        self.assertEqual(dr.current_orphans(self.rebuilt), [])
        if not self.original.get('downstream_retrace'):
            self.assertGreater(self.report['diagnostics']['stale_evidence_references_removed'], 0)
        else:
            self.assertEqual(self.report['diagnostics']['stale_evidence_references_removed'], 0)

    def test_actual_unsupported_legacy_objects_are_retired_not_carried_forward(self):
        retired = {
            x['id'] for x in self.report['object_audit']
            if x.get('retrace_status') == 'retired' and x.get('kind') in {'shock', 'high_order'}
        }
        if not retired and self.original.get('downstream_retrace'):
            retired = {
                x.get('id') for x in self.original.get('downstream_archive', {}).get('objects', [])
                if x.get('retrace_status') == 'retired' and x.get('kind') in {'shock', 'high_order'}
            }
        active = {oid for kind, oid, _ in dr.active_objects(self.rebuilt) if kind in {'shock', 'high_order'}}
        self.assertTrue(retired)
        self.assertTrue(retired.isdisjoint(active))
        archived = {
            x.get('id') for x in self.rebuilt.get('downstream_archive', {}).get('objects', [])
            if x.get('retrace_status') == 'retired'
        }
        self.assertTrue(retired.issubset(archived))

    def test_strand_c_never_becomes_primary_shock_support(self):
        for shock in self.rebuilt['shock_inference']['dynamic_shocks']:
            primary_count = 0
            for ref in shock.get('support', []):
                weight = float(ref.get('analytical_weight', 0) or 0)
                strand = str(ref.get('strand') or '')
                if strand == 'C':
                    self.assertLessEqual(weight, 0.30)
                    self.assertNotIn(str(ref.get('role') or ''), {'Primary evidence', 'Primary coupling evidence'})
                if weight >= 0.999:
                    primary_count += 1
            self.assertGreaterEqual(primary_count, 4)
            self.assertGreaterEqual(int(shock.get('inference_score', 0)), dr.SHOCK_MIN_SCORE)

    def test_high_order_primary_roles_are_not_closed_by_c_or_history(self):
        for candidate in self.rebuilt['high_order_inference']['candidates']:
            for ref in candidate.get('support', []):
                self.assertEqual(ref.get('strand'), 'A')
                self.assertAlmostEqual(float(ref.get('analytical_weight', 0)), 1.0)
            for ref in candidate.get('context', []):
                self.assertIn(ref.get('strand'), {'C', 'H'})
                self.assertLess(float(ref.get('analytical_weight', 1)), 1.0)

    def test_full_retrace_discovers_new_objects_and_records_a_item_shock_changes(self):
        if not self.original.get('downstream_retrace'):
            self.assertGreater(self.report['diagnostics']['newly_inferred'], 0)
            self.assertGreater(self.report['diagnostics']['retired'], 0)
            self.assertGreater(self.report['diagnostics']['shock_support_chains_changed_after_a_removal'], 0)
        else:
            self.assertEqual(self.report['diagnostics']['orphan_references_remaining'], 0)


if __name__ == '__main__':
    unittest.main()
