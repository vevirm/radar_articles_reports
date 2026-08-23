from pathlib import Path
import json
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class V1755BalancedMatrixPriorityTests(unittest.TestCase):
    def run_node_json(self, script: str):
        proc = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=True)
        return json.loads(proc.stdout)

    def test_current_corpus_recovers_structural_dependency_evidence(self):
        script = r'''
const fs=require('fs');
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const data=JSON.parse(fs.readFileSync('radar.json','utf8'));
const v=F.buildFrontier(data,{now:'2026-08-22T19:22:00Z'});
const dep=v.signals.filter(x=>x.column.id==='C'||x.column.id==='D').filter(x=>/depend|reliance|non-eu|foreign|supplier|vendor|access|hollow|fragment/i.test(`${x.title} ${x.evidenceTitle}`));
console.log(JSON.stringify({qualifying:v.signals.length,dep:dep.length,c:v.signals.filter(x=>x.column.id==='C').length,d:v.signals.filter(x=>x.column.id==='D').length}));
'''
        out = self.run_node_json(script)
        self.assertGreaterEqual(out["qualifying"], 8)
        self.assertGreaterEqual(out["dep"], 1)
        self.assertGreaterEqual(out["c"], 1)

    def test_generic_non_eu_talent_loss_does_not_manufacture_eu_brain_drain(self):
        script = r'''
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const data={strand_a:[{
 title:"Digital Transformation of Portugal's Marine Industry",source:'Journal',date:'2026-06-01',strand:'A',
 summary:"China can draw on Portugal's experience in infrastructure while guarding against industrial polarization and talent loss in China. The paper compares European and Chinese industrial strategies."
}],strand_b:[],strand_c:[]};
const v=F.buildFrontier(data,{now:'2026-08-22T19:22:00Z'});
console.log(JSON.stringify({brain:v.cells.knowledge.D.length}));
'''
        out = self.run_node_json(script)
        self.assertEqual(out["brain"], 0)

    def test_priority_lists_are_variable_length_with_hard_cap_only(self):
        script = r'''
const fs=require('fs');
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const P=require('./priorities/priorities.js');
const data=JSON.parse(fs.readFileSync('radar.json','utf8'));
const v=P.buildPriorityView(data,{now:'2026-08-22T19:22:00Z'});
console.log(JSON.stringify({risks:v.risks.length,opps:v.opportunities.length,allRisks:v.stats.risks,allOpps:v.stats.opportunities}));
'''
        out = self.run_node_json(script)
        self.assertLessEqual(out["risks"], 15)
        self.assertLessEqual(out["opps"], 15)
        self.assertEqual(out["risks"], min(15, out["allRisks"]))
        self.assertEqual(out["opps"], min(15, out["allOpps"]))
        page = (ROOT / 'priorities' / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('Top six', page)
        self.assertNotIn('Top 15', page)
        self.assertIn('Strongest qualifying signals', page)


if __name__ == '__main__':
    unittest.main()
