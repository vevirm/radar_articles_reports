import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PhenomenaAndStructureTests(unittest.TestCase):
    def run_node(self, source: str):
        proc = subprocess.run(
            ["node", "-e", source], cwd=ROOT, text=True, capture_output=True, check=True
        )
        return json.loads(proc.stdout)

    def test_phenomena_require_old_and_current_evidence(self):
        payload = self.run_node(
            """
const fs=require('fs');
const P=require('./phenomena/phenomena.js');
const d=JSON.parse(fs.readFileSync('radar.json','utf8'));
const h=JSON.parse(fs.readFileSync('historical/historical.json','utf8'));
const out=P.build(d,h);
console.log(JSON.stringify(out.map(x=>({
  id:x.id,current:x.currentCount,currentSources:x.currentSources,
  historical:x.historicalCount,historicalSources:x.historicalSources,
  oldDates:x.historicalEvidence.map(e=>String(e.date||'').slice(0,10)),
  newDates:x.currentEvidence.map(e=>String(e.date||'').slice(0,10))
}))));
"""
        )
        self.assertGreaterEqual(len(payload), 5)
        cutoff = json.loads((ROOT / "historical" / "historical.json").read_text(encoding="utf-8"))["cutoff_exclusive"]
        for item in payload:
            self.assertGreaterEqual(item["current"], 3, item["id"])
            self.assertGreaterEqual(item["currentSources"], 2, item["id"])
            self.assertGreaterEqual(item["historical"], 2, item["id"])
            self.assertGreaterEqual(item["historicalSources"], 2, item["id"])
            for date in item["oldDates"]:
                self.assertLess(date, cutoff, item["id"])
            for date in item["newDates"]:
                self.assertGreaterEqual(date, cutoff, item["id"])

    def test_old_evidence_alone_cannot_create_ongoing_phenomenon(self):
        result = self.run_node(
            """
const fs=require('fs');
const P=require('./phenomena/phenomena.js');
const h=JSON.parse(fs.readFileSync('historical/historical.json','utf8'));
console.log(JSON.stringify({count:P.build({strand_a:[],strand_c:[]},h).length}));
"""
        )
        self.assertEqual(result["count"], 0)

    def test_home_explains_layers_and_reader_chain(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for phrase in [
            "Established evidence", "Ways to look ahead", "Weak signals",
            "Collect evidence", "Organise it", "Find patterns", "Look ahead", "Ongoing phenomena"
        ]:
            self.assertIn(phrase, html)
        header_end = html.index("</header>")
        for phrase in ["Established evidence", "Ways to look ahead", "Weak signals"]:
            self.assertLess(html.index(phrase), header_end, phrase)
        for code in [">A</span>", ">B</span>", ">C</span>"]:
            self.assertIn(code, html)

    def test_main_radar_exposes_a_b_c_jumps_before_items(self):
        html = (ROOT / "radar" / "index.html").read_text(encoding="utf-8")
        jump = html.index('class="strand-jump"')
        first_items = html.index('id="strand-a"')
        self.assertLess(jump, first_items)
        self.assertIn("A · Established evidence", html)
        self.assertIn("B · Ways to look ahead", html)
        self.assertIn("C · Weak signals", html)


if __name__ == "__main__":
    unittest.main()
