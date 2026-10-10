import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from tests.make_fixture import workbook
from trajectory_engine.xlsx_reader import read_sheets,normalize_date
from trajectory_engine.storage import connect,rows
from trajectory_engine.engine import import_workbook,make_graph,evaluate_chains,classify,judge_support
from trajectory_engine.render import render
from trajectory_engine.llm import _validate

class EvidenceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)
  self.xlsx=workbook(self.root/'radar_all_publication_data.xlsx')
  self.db=connect(self.root/'graph.sqlite')
  self.snapshot,self.sheets,self.warnings=import_workbook(self.db,self.xlsx,synthetic=True)
  self.chains=make_graph(self.db,self.snapshot)
  evaluate_chains(self.db,self.snapshot,self.chains)
 def test_five_sheets(self):
  self.assertEqual(set(self.sheets),{'Historical findings','All publication data','Ranked sources','Shock audit','Method'})
  self.assertEqual(len(rows(self.db,'raw_records')),11)
 def test_deduplicate_publications_but_keep_occurrences(self):
  e=rows(self.db,'evidence')
  self.assertEqual(len(e),7) # 4 Historical findings + 4 All publication data - 1 duplicate
  matches=[x for x in e if 'chip-proposal' in x['source_url']]
  self.assertEqual(len(matches),1)
  obs=[o for o in rows(self.db,'evidence_occurrences') if o['evidence_id']==matches[0]['evidence_id']]
  self.assertEqual(len(obs),2)
 def test_no_ranked_source_or_shock_promoted_to_fact(self):
  self.assertFalse(any(x['origin_sheet'] in ('Ranked sources','Shock audit') for x in rows(self.db,'evidence')))
  self.assertTrue(any(x['sheet']=='Shock audit' for x in rows(self.db,'raw_records')))
 def test_dates_not_conflated(self):
  e=next(x for x in rows(self.db,'evidence') if x['title']=='Fictional quantum prototype launched')
  self.assertEqual(e['publication_date'],'2020-08-10');self.assertEqual(e['event_date'],'2020-07-01')
  self.assertEqual(normalize_date('2026-02-12'),'2026-02-12')
  self.assertEqual(normalize_date('2026'),'2026')
 def test_proposal_is_not_outcome(self):
  e=next(x for x in rows(self.db,'evidence') if x['title']=='Fictional chip goal proposed')
  self.assertEqual(e['evidence_type'],'proposed_action')
  self.assertEqual(e['outcome'],'')
  self.assertNotEqual(classify({},'We propose a new policy.')[0],'implemented_action')
 def test_relation_is_never_inferred_causation(self):
  self.assertFalse(any(r['relation_type'] in ('caused','implemented_as_result') for r in rows(self.db,'relations')))
  self.assertTrue(all(r['strength'] in ('weak','documented') for r in rows(self.db,'relations')))
 def test_same_event_one_group(self):
  q=[x for x in rows(self.db,'evidence') if x['title'].startswith(('Fictional quantum prototype','Prototype mentioned'))]
  self.assertEqual(q[0]['event_group_id'],q[1]['event_group_id'])
 def test_no_hypothesis_has_unfounded_documented_claim(self):
  self.assertFalse(any(h['status']=='documented' for h in rows(self.db,'hypotheses')))
 def test_same_event_reports_not_two_independent_developments(self):
  all_e=rows(self.db,'evidence')
  same=[e for e in all_e if e['event_group_id'] and e['event_group_id']==next(x for x in all_e if x['title']=='Fictional quantum prototype launched')['event_group_id']]
  metrics=judge_support(same)
  self.assertEqual(metrics['publications'],2)
  self.assertEqual(metrics['underlying_developments'],1)
 def test_no_duplicate_event_from_ranked_list(self):
  titles=[e['title'] for e in rows(self.db,'evidence')]
  self.assertEqual(titles.count('Fictional chip goal proposed'),1)
 def test_sensitivity_flags_single_source_family(self):
  self.assertTrue(any(r['outcome']=='fragile' for r in rows(self.db,'robustness')))
 def test_not_a_real_world_turning_point(self):
  self.assertFalse(any('turning point' in h['claim'].lower() for h in rows(self.db,'hypotheses')))
 def test_unsupported_llm_ids_rejected(self):
  o={'assessment':'documented','interpretation':'It happened','alternative':'Other','support_ids':['invented'],'against_ids':[],'what_would_change':'Evidence'}
  self.assertTrue(_validate(o,{'real'}))
 def test_optional_report(self):
  model=render(self.db,self.snapshot,self.root/'index.html')
  body=(self.root/'index.html').read_text()
  self.assertIn('What the evidence establishes',body)
  self.assertIn('SYNTHETIC',str(model['snapshot']['notes']))
  self.assertIn('Fictional',body)
 def test_no_claim_without_date_on_ingest(self):
  for e in rows(self.db,'evidence'):
   self.assertTrue(e['publication_date'] is None or len(e['publication_date']) in (4,10))
 def test_never_count_llm_claim_as_original_evidence(self):
  self.assertEqual(len(rows(self.db,'llm_assessments')),0)

if __name__=='__main__':unittest.main()
