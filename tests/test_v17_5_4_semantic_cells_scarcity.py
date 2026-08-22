from pathlib import Path
import json
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class V1754SemanticCellsScarcityTests(unittest.TestCase):
    def run_node_json(self, script: str):
        proc = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=True)
        return json.loads(proc.stdout)

    def test_economic_coercion_report_does_not_fill_brain_drain(self):
        script = r'''
const fs=require('fs');
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const data=JSON.parse(fs.readFileSync('radar.json','utf8'));
const v=F.buildFrontier(data,{now:'2026-08-22T18:45:00Z'});
const bad=v.cells.knowledge.D.filter(x=>/economic coercion/i.test(x.title)||/Mitigate, deter, escalate/i.test(x.evidenceTitle));
const report=v.signals.find(x=>/economic coercion/i.test(x.title)||/Mitigate, deter, escalate/i.test(x.evidenceTitle));
console.log(JSON.stringify({bad:bad.length,report:report?`${report.row.id}-${report.column.id}`:null,count:v.cells.knowledge.D.length}));
'''
        out = self.run_node_json(script)
        self.assertEqual(out["bad"], 0)
        self.assertEqual(out["count"], 0)

    def test_direct_researcher_outflow_is_brain_drain(self):
        script = r'''
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const data={strand_a:[],strand_b:[],strand_c:[{
 headline:'European universities report researcher outflow as scientists leave Europe for US labs, reducing research capacity and competitiveness.',
 source:'EPRS',date:'2026-06-20',watch_theme:'research talent mobility',new_this_scan:true
}]};
const v=F.buildFrontier(data,{now:'2026-08-22T18:45:00Z'});
console.log(JSON.stringify(v.signals.map(x=>({cell:`${x.row.id}-${x.column.id}`,name:x.cellName}))));
'''
        out = self.run_node_json(script)
        self.assertTrue(any(x["cell"] == "knowledge-D" and x["name"] == "Brain drain" for x in out), out)

    def test_short_acronyms_use_boundaries(self):
        script = r'''
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const F=require('./frontier/frontier.js');
const x={headline:'Europe prepares responses to US economic coercion.',watch_theme:'economic security'};
const scores=F.rowScores({...x,_origin:'Weak signal'},null);
console.log(JSON.stringify(scores));
'''
        out = self.run_node_json(script)
        # "ERC" must not be inferred from the letters inside "coercion".
        self.assertEqual(out["knowledge"], 0)

    def test_scarcity_budget_is_proportional_not_hard_coded(self):
        import sys, types
        sys.modules.setdefault("feedparser", types.SimpleNamespace())
        from scripts import scan_radar as scanner
        counts = {key: 3 for key in scanner.FRONTIER_CELL_ORDER}
        counts["knowledge-D"] = 0
        counts["rules-C"] = 1
        counts["conversion-B"] = 2
        state = {"frontier_gap_cursor": 0}
        with patch.object(scanner, "frontier_matrix_coverage", return_value=(counts, sum(counts.values()), "")):
            plan = scanner.frontier_gap_plan({}, state)
        self.assertEqual(plan["deficits"]["knowledge-D"], 3)
        self.assertEqual(plan["deficits"]["rules-C"], 2)
        self.assertEqual(plan["deficits"]["conversion-B"], 1)
        self.assertEqual(plan["deficits"]["knowledge-A"], 0)
        weighted = plan["weighted_targets"]
        self.assertEqual(weighted.count("knowledge-D"), 3)
        self.assertEqual(weighted.count("rules-C"), 2)
        self.assertEqual(weighted.count("conversion-B"), 1)
        self.assertEqual(weighted.count("knowledge-A"), 0)
        self.assertEqual(json.loads((ROOT / "radar_config.json").read_text())["frontier_gap_priority_cells"], [])

    def test_all_sixteen_cells_have_discovery_profiles(self):
        config = json.loads((ROOT / "radar_config.json").read_text())
        cells = {f"{r}-{c}" for r in ("knowledge","infrastructure","conversion","rules") for c in "ABCD"}
        self.assertEqual(set(config["frontier_gap_search_queries"]), cells)
        self.assertEqual(set(config["frontier_gap_scholarly_queries"]), cells)
        self.assertEqual(set(config["frontier_gap_institution_url_terms"]), cells)
        self.assertEqual(set(config["frontier_gap_institution_sources"]), cells)


if __name__ == '__main__':
    unittest.main()
