import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_scan_v17211", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class RiskOpportunityPolarityTests(unittest.TestCase):
    def test_choose_europe_is_opportunity_not_risk_in_reader(self):
        js = r"""
const fs=require('fs');
const P=require('./priorities/priorities.js');
const D=JSON.parse(fs.readFileSync('radar.json','utf8'));
const v=P.buildPriorityView(D,{limit:50});
if(v.risks.some(x=>x.title==='Choose Europe for Science')) process.exit(2);
const x=v.opportunities.find(x=>x.title==='Choose Europe for Science');
if(!x) process.exit(3);
if(P.plainPriorityTitle(x)!=='Better research careers could help Europe keep and attract researchers.') process.exit(4);
if(!/response to brain drain, not the risk itself/i.test(P.plainPriorityExplanation(x))) process.exit(5);
"""
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)

    def test_scanner_understands_mitigation_direction(self):
        text = (
            "The objective of MSCA Choose Europe for Science is to increase the attractiveness "
            "of European research careers by addressing the issue of precarity and turning the "
            "current challenge of brain drain into brain gain. The pilot action supports projects "
            "in which organisations recruit postdoctoral researchers and offer longer-term employment."
        )
        out = scan.classify_strategic_source_text(text)
        self.assertNotEqual(out.get("primary"), "risk")
        self.assertTrue(any(x.get("type") == "opportunity" for x in out.get("lenses", [])))
        self.assertFalse(any(x.get("type") == "risk" for x in out.get("lenses", [])))

    def test_response_word_does_not_erase_unrelated_material_risk(self):
        # "reduces fossil fuel dependency" is a benefit in one clause, while the actual
        # risk in another clause is critical-material scarcity. The polarity guard must
        # not suppress the whole paper just because a positive verb appears somewhere.
        js = r"""
const P=require('./priorities/priorities.js');
const x={title:'Material limits',source:'Journal',date:'2026-09-01',summary:'Decarbonising energy systems reduces fossil fuel dependency, but expanding renewables increases demand for critical raw materials. Competing demand amplifies scarcity and critical raw material supply can constrain European technology capacity.'};
const t=P.evidenceText(x);
if(P.remedialOnlyRiskText(t)) process.exit(2);
if(!P.inferredLens(x,'risk',t)) process.exit(3);
"""
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)

    def test_reader_uses_plain_language_and_read_more_not_classifier_meta(self):
        page = (ROOT / "priorities" / "index.html").read_text(encoding="utf-8")
        self.assertIn("Read more", page)
        self.assertIn("What the risk is", page)
        self.assertIn("What the opportunity is", page)
        self.assertIn("What the source says", page)
        self.assertNotIn("Why it qualifies", page)
        self.assertNotIn("componentLine", page)

    def test_current_corpus_retains_broad_risk_and_opportunity_coverage(self):
        js = r"""
const fs=require('fs');
const P=require('./priorities/priorities.js');
const D=JSON.parse(fs.readFileSync('radar.json','utf8'));
const v=P.buildPriorityView(D,{limit:50});
if(v.stats.risks<10) process.exit(2);
if(v.stats.opportunities<10) process.exit(3);
"""
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)


if __name__ == "__main__":
    unittest.main()
