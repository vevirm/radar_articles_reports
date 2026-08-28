import json
import sys, types
import unittest
from pathlib import Path

try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    mod = types.ModuleType('feedparser')
    mod.parse = lambda *a, **k: types.SimpleNamespace(entries=[])
    sys.modules['feedparser'] = mod

from scripts import scan_radar as sr

ROOT=Path(__file__).resolve().parents[1]

class RotationCellFillTests(unittest.TestCase):
    def test_stubborn_recovery_rotates_formulations_per_cell(self):
        state={'frontier_recovery_query_cursors': {'knowledge-D': 2, 'rules-C': 1}}
        focus={'empty_targets':['knowledge-D','rules-C']}
        plan=sr.frontier_gap_recovery_plan(focus,state,4)
        kd=sr.CONFIG['frontier_gap_scholarly_queries']['knowledge-D']
        rc=sr.CONFIG['frontier_gap_scholarly_queries']['rules-C']
        self.assertEqual(plan['planned_by_cell']['knowledge-D'][:2],[kd[2],kd[3]])
        self.assertEqual(plan['planned_by_cell']['rules-C'][:2],[rc[1],rc[2]])
        executed=set(plan['queries'])
        adv=sr.commit_frontier_recovery_plan(state,plan,executed)
        self.assertEqual(adv,{'knowledge-D':2,'rules-C':2})
        self.assertEqual(state['frontier_recovery_query_cursors']['knowledge-D'],4)
        self.assertEqual(state['frontier_recovery_query_cursors']['rules-C'],3)

    def test_unexecuted_recovery_work_does_not_advance_cell_cursor(self):
        state={'frontier_recovery_query_cursors': {'knowledge-C': 0}}
        focus={'empty_targets':['knowledge-C']}
        plan=sr.frontier_gap_recovery_plan(focus,state,3)
        first=plan['planned_by_cell']['knowledge-C'][0]
        sr.commit_frontier_recovery_plan(state,plan,{first})
        self.assertEqual(state['frontier_recovery_query_cursors']['knowledge-C'],1)

    def test_target_sentence_preserves_real_brain_drain_mechanism(self):
        text=('A generic introduction about research policy in Europe. '
              'European researchers are leaving for the United States, creating a brain drain and loss of scientific talent that weakens research capacity. '
              'The paper discusses several policy options.')
        ev={'bridge_sentence':'A generic introduction about research policy in Europe.','ri_evidence':['research policy'],'geo_evidence':['united states'],'eu_evidence':['europe']}
        out=sr.make_summary(text,ev,'A','Example',['knowledge-D'])
        self.assertIn('researchers are leaving',out.lower())
        self.assertIn('brain drain',out.lower())

    def test_target_sentence_does_not_invent_missing_mechanism(self):
        text='European research policy supports universities. The programme funds collaboration and training.'
        ev={'ri_evidence':['research policy'],'eu_evidence':['european']}
        out=sr.make_summary(text,ev,'A','Example',['knowledge-D'])
        self.assertNotIn('brain drain',out.lower())

    def test_all_six_user_empty_cells_have_multi_variant_recovery_banks(self):
        for cell in ['knowledge-C','knowledge-D','infrastructure-B','infrastructure-D','conversion-D','rules-C']:
            self.assertGreaterEqual(len(sr.CONFIG['frontier_gap_scholarly_queries'][cell]),6,cell)

    def test_allocation_version_bumped(self):
        self.assertEqual(sr.CONFIG['allocation_profile_version'],'v17.13.7-recurring-multifactor-rotation')

if __name__=='__main__': unittest.main()
