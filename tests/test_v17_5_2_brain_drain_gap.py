import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BrainDrainGapTests(unittest.TestCase):
    def run_node(self, script: str):
        return subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)

    def test_substantive_eu_research_brain_drain_report_fills_knowledge_d(self):
        script = r"""
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const data={strand_a:[{
 title:'Boosting research and innovation in the EU', source:'European Parliamentary Research Service',
 date:'2026-06-01', strand:'A',
 summary:'Members underscored the tension between facilitating researcher mobility and preventing brain drain, identifying difficulties faced by researchers returning to their home countries as a major impediment. EU research and innovation investment needs to close the innovation gap with global competitors.'
}],strand_b:[],strand_c:[]};
const v=F.buildFrontier(data,{now:'2026-08-22T12:00:00Z'});
if(v.cells.knowledge.D.length!==1) process.exit(2);
if(!/brain drain/i.test(v.cells.knowledge.D[0].title)) process.exit(3);
"""
        self.run_node(script)

    def test_gap_rescue_stays_inside_live_corpus_window_by_default(self):
        cfg=json.loads((ROOT/'radar_config.json').read_text(encoding='utf-8'))
        self.assertEqual(cfg.get('frontier_gap_historical_lookback_months'), 0)
        self.assertIn('europarl.europa.eu', cfg['frontier_gap_institution_sources']['knowledge-D'])
        self.assertTrue(any(x.get('domain')=='euraxess.ec.europa.eu' for x in cfg['institution_sources']))


if __name__ == '__main__':
    unittest.main()
