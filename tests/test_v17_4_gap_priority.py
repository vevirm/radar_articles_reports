from pathlib import Path
import json
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class V174GapPriorityTests(unittest.TestCase):
    def run_node(self, script: str):
        subprocess.run(["node", "-e", script], cwd=ROOT, check=True)

    def test_exact_frontier_coverage_bridge_uses_same_classifier(self):
        data = {
            "strand_a": [], "strand_b": [],
            "strand_c": [
                {"headline": "EU attracts frontier AI researchers and expands European compute capacity, reducing non-EU dependence", "source": "Reuters", "date": "2026-08-21", "watch_theme": "R&I competitiveness / technological capabilities", "new_this_scan": True},
                {"headline": "Europe loses semiconductor production capacity as foreign suppliers restrict access and EU firms fall behind", "source": "Reuters", "date": "2026-08-21", "watch_theme": "semiconductors", "new_this_scan": True},
            ],
        }
        proc = subprocess.run(
            ["node", str(ROOT / "scripts" / "frontier_coverage.js")],
            cwd=ROOT, input=json.dumps(data), text=True, capture_output=True, check=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(set(payload["counts"]), {
            f"{r}-{c}" for r in ("knowledge", "infrastructure", "conversion", "rules") for c in ("A", "B", "C", "D")
        })
        self.assertGreaterEqual(payload["qualifying"], 2)
        self.assertEqual(sum(payload["counts"].values()), payload["qualifying"])

    def test_scanner_prioritises_sparsest_cells_without_changing_admission(self):
        scanner = (ROOT / "scripts" / "scan_radar.py").read_text(encoding="utf-8")
        config = json.loads((ROOT / "radar_config.json").read_text(encoding="utf-8"))
        self.assertIn("frontier_gap_plan(previous, state)", scanner)
        self.assertIn("frontier_matrix_coverage(previous)", scanner)
        self.assertIn("frontier_focus[\"queries\"]", scanner)
        self.assertIn("scarcity-weighted", scanner)
        self.assertEqual(config.get("frontier_gap_target_count"), 3)
        self.assertEqual(config.get("frontier_gap_queries_per_scan"), 14)
        self.assertEqual(len(config.get("frontier_gap_search_queries", {})), 16)
        self.assertEqual(config.get("frontier_gap_scholarly_queries_per_scan"), 28)
        self.assertEqual(len(config.get("frontier_gap_scholarly_queries", {})), 16)
        self.assertEqual(config.get('frontier_gap_priority_cells', []), [])
        self.assertEqual(config.get('frontier_gap_historical_lookback_months'), 0)
        self.assertIn('europarl.europa.eu', config.get('frontier_gap_institution_sources', {}).get('knowledge-D', []))
        self.assertIn('researcher-mobility', config.get('frontier_gap_institution_url_terms', {}).get('knowledge-D', []))
        self.assertIn('frontier_focus.get("scholarly_queries", [])', scanner)
        # The core classifier gate remains untouched in the browser module.
        frontier = (ROOT / "frontier" / "frontier.js").read_text(encoding="utf-8")
        self.assertIn("cellEvidencePass", frontier)

    def test_opportunity_risk_page_is_cumulative_and_ranks_risks(self):
        script = r'''
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const P=require('./priorities/priorities.js');
const data={strand_a:[],strand_b:[],strand_c:[
 {headline:'EU attracts frontier AI researchers and expands European compute capacity, reducing non-EU dependence',source:'Reuters',date:'2026-08-21',watch_theme:'R&I competitiveness / technological capabilities',new_this_scan:false},
 {headline:'EU research security rules reduce foreign dependence but slow scientific collaboration and raise costs',source:'Reuters',date:'2026-06-21',watch_theme:'research security',new_this_scan:false},
 {headline:'European AI labs gain frontier performance by relying on US cloud and non-EU compute suppliers',source:'Reuters',date:'2026-05-21',watch_theme:'technology sovereignty',new_this_scan:false},
 {headline:'Europe loses semiconductor production capacity as foreign suppliers restrict access and EU firms fall behind',source:'Reuters',date:'2026-04-21',watch_theme:'semiconductors',new_this_scan:false}
]};
const v=P.buildPriorityView(data,{now:'2026-08-22T16:00:00Z'});
if(v.opportunities.length!==1) process.exit(2);
if(v.risks.length!==3) process.exit(3);
if(v.risks[0].column.id!=='D') process.exit(4);
if(v.stats.cumulativeQualifying!==4) process.exit(5);
'''
        self.run_node(script)
        page = (ROOT / "priorities" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Greatest risks", page)
        self.assertIn("Greatest opportunities", page)
        self.assertIn("fetch('../radar.json?ts='+Date.now()", page)
        self.assertNotIn("summaryTitle", page)
        self.assertNotIn("panel-intro", page)
        self.assertNotIn("Show all", page)
        self.assertNotIn("Frontier matrix", page)

    def test_priority_page_caps_and_diversifies_default_lists(self):
        script = r'''
const I=require('./briefing/insights.js'); global.RadarInsights=I;
const P=require('./priorities/priorities.js');
const rows=['knowledge','infrastructure','conversion','rules'];
const fake=[];
for(let i=0;i<20;i++) fake.push({headline:`Europe loses AI capability ${i} as foreign suppliers restrict access and firms fall behind`,source:'Reuters',date:'2026-08-21',watch_theme:'technology sovereignty'});
const v=P.buildPriorityView({strand_a:[],strand_b:[],strand_c:fake},{now:'2026-08-22T16:00:00Z'});
if(v.risks.length>15||v.opportunities.length>15) process.exit(2);
''';
        self.run_node(script)
        page = (ROOT / 'priorities' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('The strongest signals in plain language.', page)

    def test_navigation_and_preservation_guard_remain(self):
        main = (ROOT / "index.html").read_text(encoding="utf-8")
        briefing = (ROOT / "briefing" / "index.html").read_text(encoding="utf-8")
        frontier = (ROOT / "frontier" / "index.html").read_text(encoding="utf-8")
        scanner = (ROOT / "scripts" / "scan_radar.py").read_text(encoding="utf-8")
        radar = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        self.assertIn("priorities/?v=17.8.1", main)
        self.assertIn("../priorities/", briefing)
        self.assertIn("../priorities/", frontier)
        self.assertGreaterEqual(sum(len(radar.get(k, [])) for k in ("strand_a", "strand_b", "strand_c")), 18)
        self.assertGreaterEqual(len(radar.get("strand_a", [])), 10)
        # Do not require a minimum B quota: V17.6.0 keeps the methods library empty rather than retain application-only false positives.
        self.assertGreaterEqual(len(radar.get("strand_c", [])), 4)
        self.assertFalse(radar.get("repository_bundle_seed"))
        self.assertIn("Recovered a larger pre-upload radar corpus from Git history", scanner)
        self.assertIn('clean.pop("repository_bundle_seed", None)', scanner)


if __name__ == "__main__":
    unittest.main()
