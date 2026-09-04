from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReaderUiV17179Tests(unittest.TestCase):
    def test_landing_page_is_plain_language_current_picture_with_large_main_radar_link(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("What matters", html)
        self.assertIn("these are the issues that stand out now — in plain language", html)
        self.assertIn('class="main-radar-link" href="radar/"', html)
        self.assertIn("THE MAIN RADAR", html)
        self.assertIn('id="issues"', html)
        self.assertIn("buildIssues(data)", html)
        self.assertIn("Read more", html)
        self.assertIn("Read at least this", html)
        self.assertIn("Trends vs. countertrend competition", html)
        self.assertIn("Risks &amp; opportunities", html)
        self.assertIn("External shocks", html)
        self.assertNotIn("Next automatic", html)
        self.assertNotIn("scheduleState", html)
        radar = (ROOT / "radar" / "index.html").read_text(encoding="utf-8")
        self.assertIn('aria-current="page">Main Radar</a>', radar)
        self.assertIn("Quality papers &amp; reports", radar)
        self.assertIn("Foresight methods", radar)
        self.assertIn("Weak signals", radar)

    def test_read_page_is_eight_hierarchical_topic_charts_only(self):
        html = (ROOT / "read" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "read" / "issues.js").read_text(encoding="utf-8")
        self.assertIn('Read at least this', html)
        self.assertIn('class="issue-chart"', html)
        self.assertIn('class="tree-svg"', html)
        self.assertIn('class="node main"', html)
        self.assertIn('class="node sub one"', html)
        self.assertIn('class="node leaf three"', html)
        self.assertIn('buildTrees(items,{count:8})', html)
        self.assertIn('const items=[...(d.strand_a||[]),...(d.strand_c||[])]', html)
        self.assertNotIn('issue-list', html)
        self.assertNotIn('issues stand out', html.lower())
        self.assertIn('function build(items,opt={})', js)

    def test_matrix_reader_is_concise_and_drops_per_item_why_block(self):
        full = (ROOT / "frontier" / "index.html").read_text(encoding="utf-8")
        quick = (ROOT / "frontier" / "quick" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "frontier" / "frontier.js").read_text(encoding="utf-8")
        self.assertNotIn('capped at 80 characters', full)
        self.assertNotIn('capped at 80 characters', quick)
        self.assertNotIn('source-based', quick)
        self.assertNotIn('Why this cell', full)
        self.assertNotIn('cell-why', full)
        self.assertIn('function shortBullet(x)', js)
        self.assertIn('q.length>100', js)
        self.assertIn('cap100', js)

    def test_current_matrix_points_are_all_100_characters_or_less(self):
        js = r"""
const F=require('./frontier/frontier.js');
const D=require('./radar.json');
const v=F.buildFrontier(D);
for(const x of v.signals){
  const point=F.shortBullet(x);
  if(point.length>100){
    console.error(point.length, point);
    process.exit(2);
  }
}
if(!v.signals.length) process.exit(3);
"""
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)

    def test_reader_assets_use_current_cache_buster(self):
        for rel in [
            "index.html", "radar/index.html", "read/index.html", "frontier/index.html", "frontier/quick/index.html",
            "priorities/index.html", "shocks/index.html", "shocks/variants.html", "historical/index.html",
            "literature/index.html", "stuff/index.html",
        ]:
            with self.subTest(rel=rel):
                html=(ROOT / rel).read_text(encoding="utf-8")
                self.assertNotIn('v=17.19.29', html)
                self.assertNotIn('v=17.19.27', html)
                self.assertNotIn('v=17.19.23', html)
                self.assertIn('no-cache, no-store, must-revalidate', html)

    def test_stuff_is_visible_in_reader_top_navigation(self):
        for rel in [
            "read/index.html",
            "frontier/index.html",
            "frontier/quick/index.html",
            "priorities/index.html",
            "literature/index.html",
            "glossary/index.html",
            "stuff/index.html",
        ]:
            with self.subTest(rel=rel):
                html = (ROOT / rel).read_text(encoding="utf-8")
                self.assertIn(">Stuff</a>", html)


if __name__ == "__main__":
    unittest.main()
