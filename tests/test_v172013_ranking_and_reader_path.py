import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RankingAndReaderPathTests(unittest.TestCase):
    def test_new_radar_items_are_ranked_by_reader_score(self):
        js = r"""
const fs=require('fs');
const R=require('./reader_rank.js');
const D=JSON.parse(fs.readFileSync('radar.json','utf8'));
const xs=(D.strand_a||[]).filter(x=>x.new_this_scan).slice().sort(R.compare);
for(let i=1;i<xs.length;i++) if(R.scoreFor(xs[i-1])<R.scoreFor(xs[i])) process.exit(3);
// Keep the regression independent of whichever rotation happened to run last.
const dual={strand:'A',source:'European Commission',type:'official policy',title:'EU Dual-Use Regulation and research security',eu_evidence:['EU'],ri_evidence:['research'],geo_evidence:['dual-use']};
const generic={strand:'A',source:'European Commission',type:'official policy',title:'Horizon Europe Proposal Writing guidance',eu_evidence:['EU'],ri_evidence:['research']};
if(R.scoreFor(dual)<=R.scoreFor(generic)) process.exit(5);
"""
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)

    def test_main_radar_shows_score_and_core_path(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("reader_rank.js", html)
        self.assertIn("rankBadge(x)", html)
        self.assertIn("Reader rank ${n}/100", html)
        self.assertIn("globalThis.RadarReaderRank?.compare", html)
        positions = [
            html.index("1</span><strong>Radar"),
            html.index("2</span><strong>Matrix"),
            html.index("3</span><strong>Trends"),
            html.index("4</span><strong>Risks &amp; opportunities"),
            html.index("5</span><strong>External shocks"),
        ]
        self.assertEqual(positions, sorted(positions))

    def test_analytical_products_weight_source_quality(self):
        priorities = (ROOT / "priorities" / "priorities.js").read_text(encoding="utf-8")
        shocks = (ROOT / "shocks" / "scenarios.js").read_text(encoding="utf-8")
        variants = (ROOT / "shocks" / "variants.js").read_text(encoding="utf-8")
        self.assertIn("quality*1e13", priorities)
        self.assertIn("quality*1e13", priorities)
        self.assertNotIn("quality<68", priorities)
        self.assertIn("qualityScore(x)*100", shocks)
        self.assertIn("inferenceScore", shocks)
        self.assertNotIn("best<82||avg<68", shocks)
        self.assertIn("qualityScore(x)*100", variants)

    def test_release_contains_reader_ranking_runtime(self):
        manifest = (ROOT / "scripts" / "build_release.py").read_text(encoding="utf-8")
        self.assertIn('"reader_rank.js"', manifest)


if __name__ == "__main__":
    unittest.main()
