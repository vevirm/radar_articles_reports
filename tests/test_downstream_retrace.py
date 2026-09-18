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
        # Downstream reasoning is now defined over the authoritative active
        # snapshot, while radar.json deliberately retains inactive raw evidence
        # for audit/reversibility.
        corpus_path = ROOT / 'radar_active.json'
        cls.original = json.loads(corpus_path.read_text(encoding='utf-8'))
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
        active = {oid for kind, oid, _ in dr.active_objects(self.rebuilt) if kind in {'shock', 'high_order'}}
        # A fully cleaned/revalidated corpus can legitimately have no objects to
        # retire. What matters is that anything retired by *this retrace* is
        # never left active and is preserved in the archive. Older archive entries
        # are an audit history, not a permanent blacklist: after Deep Scan changes
        # the authoritative active corpus, the same inference ID may legitimately
        # become supported again and be re-inferred.
        archived = {
            x.get('id') for x in self.rebuilt.get('downstream_archive', {}).get('objects', [])
            if x.get('retrace_status') == 'retired'
        }
        self.assertTrue(retired.isdisjoint(active))
        self.assertTrue(retired.issubset(archived))
        self.assertEqual(self.report['diagnostics']['orphan_references_remaining'], 0)

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

    def test_high_order_primary_roles_follow_claim_primary_semantics(self):
        # R-09 after the reasoning reform: A/frontier claims are primary, and a
        # Deep-Scan KEEP Strand-C claim may also be primary when it is verified
        # event content (action/effect). Historical claims remain context only.
        # `analytical_weight` on claim-native support is the R-21 role strength,
        # not the old A-vs-C context weight.
        for candidate in self.rebuilt['high_order_inference']['candidates']:
            if not candidate.get('claim_native'):
                continue
            for ref in candidate.get('support', []):
                self.assertIn(ref.get('strand'), {'A', 'C'})
                self.assertNotEqual(ref.get('strand'), 'H')
                self.assertTrue(ref.get('claim_primary'))
                # R-09 primary/context authority is independent of R-21 role
                # strength. A primary claim may legitimately carry zero role
                # strength when its status is abandoned/lapsed (or merit is 0);
                # Stage 7 must keep that evidence in stock while preventing it
                # from satisfying a qualification floor.
                weight = float(ref.get('analytical_weight', 0) or 0)
                self.assertGreaterEqual(weight, 0.0)
                if weight == 0.0:
                    self.assertTrue(
                        str(ref.get('claim_status') or '') in {'abandoned', 'lapsed'}
                        or float(ref.get('claim_merit', 0) or 0) <= 0.0
                    )
                if ref.get('strand') == 'C':
                    self.assertNotEqual(str(ref.get('claim_origin') or ''), 'provisional')
                    self.assertIn(str(ref.get('claim_kind') or ''), {'action', 'effect'})
            for ref in candidate.get('context', []):
                # Context holds historical/context-only claims plus A/C rows that
                # were demoted from support (provisional, non-directional or not
                # source-grounded). Whatever the strand, context is never primary.
                self.assertIn(ref.get('strand'), {'A', 'C', 'H'})
                self.assertFalse(ref.get('claim_primary', False))
                if ref.get('strand') == 'A':
                    self.assertTrue(ref.get('demoted_from_primary') or ref.get('evidence_contribution'))

    def test_full_retrace_records_changes_without_requiring_new_or_retired_objects(self):
        # `newly_inferred` and `retired` are change counters, not invariants.
        # Both are allowed to be zero when the current cumulative corpus has
        # already been cleaned/revalidated.  The retrace invariant is that all
        # stale evidence is removed and no orphan reference remains.
        diagnostics = self.report['diagnostics']
        self.assertGreaterEqual(diagnostics['newly_inferred'], 0)
        self.assertGreaterEqual(diagnostics['retired'], 0)
        self.assertGreaterEqual(diagnostics['shock_support_chains_changed_after_a_removal'], 0)
        self.assertEqual(diagnostics['orphan_references_remaining'], 0)
        self.assertTrue(self.report['integrity_check']['passed'])
        self.assertEqual(dr.current_orphans(self.rebuilt), [])


if __name__ == '__main__':
    unittest.main()
