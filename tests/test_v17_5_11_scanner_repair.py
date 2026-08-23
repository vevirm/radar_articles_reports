from pathlib import Path
import json
import subprocess
import sys
import types
import unittest

try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    sys.modules['feedparser'] = types.ModuleType('feedparser')

from scripts import scan_radar as scanner

ROOT = Path(__file__).resolve().parents[1]


class V17511ScannerRepairTests(unittest.TestCase):
    def test_strand_b_rejects_topical_fp10_paper_that_merely_mentions_scenario(self):
        ev = scanner.gate_scope(
            'Globalising FP10: better engagement with associated countries',
            'The European Union is designing FP10 amid geopolitical tension. '
            'What would be the consequences of such a scenario for Horizon Europe governance?',
            '', 2, source_kind='institutional'
        )
        self.assertTrue(ev['a_pass'])
        self.assertFalse(ev['b_pass'])
        self.assertFalse(ev['b_methodology_first'])

    def test_strand_b_rejects_domain_application_even_when_called_technology_foresight(self):
        ev = scanner.gate_scope(
            'Mobile apps for cancer patient education: a technology foresight analysis',
            'Methods A technology foresight study was conducted in four phases to identify future mobile-app functions. '
            'The paper evaluates patient education content and clinical usability.',
            '', 2, source_kind='scholarly'
        )
        self.assertFalse(ev['b_pass'])
        self.assertFalse(ev['b_transferable'])

    def test_strand_b_accepts_methodology_first_ri_delphi(self):
        ev = scanner.gate_scope(
            'A new Delphi methodology for R&I foresight',
            'This paper develops and evaluates a Delphi method for research and innovation foresight. '
            'It compares expert-selection, bias-control and weak-signal aggregation procedures for innovation policy.',
            '', 2, source_kind='scholarly'
        )
        self.assertTrue(ev['b_pass'])
        self.assertTrue(ev['b_methodology_first'])
        self.assertEqual(ev['b_route'], 'future-of-A-method')
        self.assertFalse(ev['a_pass'])

    def test_student_erasmus_mobility_is_not_research_talent_geopolitics(self):
        text = ('Academic and Cultural Experiences in Europe through the Erasmus+ Program. '
                'The study examines international student mobility, cultural experiences and higher education participation.')
        self.assertFalse(scanner.research_talent_flow_signal(text))
        ev = scanner.gate_scope('Academic and Cultural Experiences in Europe through the Erasmus+ Program', text, '', 2, source_kind='scholarly')
        self.assertFalse(ev['a_pass'])

    def test_researcher_brain_drain_remains_valid(self):
        text = ('Europe faces research brain drain as researchers leave Germany and France for laboratories in the United States, '
                'weakening scientific capacity and research competitiveness.')
        self.assertTrue(scanner.research_talent_flow_signal(text))

    def test_all_four_knowledge_cells_are_reachable_with_correct_semantics(self):
        script = r'''
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const cases={
 A:{title:'EU attracts and retains international researchers',summary:'European research programmes attract and retain international researchers, strengthening European research capacity and reducing reliance on external expertise.'},
 B:{title:'EU research security screening protects sensitive science',summary:'EU research security screening protects sensitive science but restricts international scientific collaboration, creates barriers and delays researcher mobility.'},
 C:{title:'Europe relies on non-EU scientific talent',summary:'European laboratories rely on non-EU scientific talent and foreign expertise; access to this expertise strengthens research excellence and research capacity.'},
 D:{title:'Researchers leave Germany for the United States',summary:'Researchers are leaving Germany for the United States, causing research brain drain and loss of European research capacity and competitiveness.'}
};
const out={};
for(const [expected,x] of Object.entries(cases)){
  const data={strand_a:[Object.assign({source:'Test',date:'2026-08-20',strand:'A',eu_relevance:'direct'},x)],strand_b:[],strand_c:[]};
  const v=F.buildFrontier(data,{now:'2026-08-23T06:22:00Z'});
  const hits=[];
  for(const r of v.rows) for(const c of v.columns) if(v.cells[r.id][c.id].length) hits.push(`${r.id}-${c.id}`);
  out[expected]=hits;
}
console.log(JSON.stringify(out));
'''
        out = json.loads(subprocess.run(['node','-e',script], cwd=ROOT, text=True, capture_output=True, check=True).stdout)
        for col in 'ABCD':
            self.assertEqual(out[col], [f'knowledge-{col}'])

    def test_member_state_adjective_survives_frontier_eu_scope(self):
        script = r'''
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const data={strand_a:[{title:'German research security screening',source:'Test',date:'2026-08-20',strand:'A',eu_relevance:'direct',summary:'German research security screening protects sensitive research but restricts international scientific collaboration and creates delay risks.'}],strand_b:[],strand_c:[]};
const v=F.buildFrontier(data,{now:'2026-08-23T06:22:00Z'});
console.log(JSON.stringify({b:v.cells.knowledge.B.length,total:v.signals.length}));
'''
        out = json.loads(subprocess.run(['node','-e',script], cwd=ROOT, text=True, capture_output=True, check=True).stdout)
        self.assertGreaterEqual(out['b'], 1)

    def test_quality_profile_change_does_not_reset_rotation_state(self):
        prev={'quality_profile_version':'older-profile','scan_state':{
            'version':scanner.INCREMENTAL_STATE_VERSION,
            'source_expansion_version':scanner.SOURCE_EXPANSION_VERSION,
            'openalex_cursor':17,'crossref_broad_cursor':23,'crossref_priority_cursor':41,
            'strand_b_method_cursor':5,'institution_cursor':11,'frontier_gap_cursor':7,
            'backfill':{},'completed_cycles':{},'cycle_failed':{}
        }}
        state=scanner.initial_scan_state(prev)
        self.assertEqual(state['openalex_cursor'],17)
        self.assertEqual(state['crossref_broad_cursor'],23)
        self.assertEqual(state['crossref_priority_cursor'],41)
        self.assertEqual(state['strand_b_method_cursor'],5)
        self.assertEqual(state['institution_cursor'],11)
        self.assertEqual(state['frontier_gap_cursor'],7)

    def test_method_lane_rotates_independently(self):
        bank=list(dict.fromkeys(scanner.CONFIG['queries_b_method']))
        first,c1,_=scanner.rotating_batch(bank,0,scanner.CONFIG['queries_b_method_per_scan'])
        second,c2,_=scanner.rotating_batch(bank,c1,scanner.CONFIG['queries_b_method_per_scan'])
        self.assertTrue(first and second)
        self.assertNotEqual(first,second)
        self.assertNotEqual(c1,c2)


if __name__ == '__main__':
    unittest.main()
