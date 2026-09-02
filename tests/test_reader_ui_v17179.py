from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReaderUiV17179Tests(unittest.TestCase):
    def test_landing_page_makes_main_radar_primary_and_keeps_navigation_simple(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("R&amp;I × Geopolitics", html)
        self.assertIn("EU research &amp; innovation in geopolitical context.", html)
        self.assertIn('<nav class="landing-nav"', html)
        nav = html.split('<nav class="landing-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertIn('aria-current="page">Radar</a>', nav)
        self.assertLess(nav.find('>Radar</a>'), nav.find('>Read</a>'))
        self.assertLess(nav.find('>Radar</a>'), nav.find('>Matrix</a>'))
        self.assertLess(nav.find('>Radar</a>'), nav.find('>Stuff</a>'))
        self.assertNotIn('>Weak signals</a>', nav)
        self.assertNotIn('landing-choices', html)
        self.assertNotIn('<section class="inside-map"', html)
        self.assertNotIn('<section class="page-map"', html)
        self.assertNotIn("Next automatic", html)
        self.assertNotIn("scheduleState", html)

    def test_read_page_is_simple_and_excludes_weak_signal_module(self):
        html = (ROOT / "read" / "index.html").read_text(encoding="utf-8")
        self.assertIn('A short issue view built from established Radar evidence.', html)
        self.assertIn('class="branches"', html)
        self.assertNotIn('Weak signals to watch', html)
        self.assertNotIn('weakSignals', html)
        self.assertNotIn('strand_c', html)
        self.assertNotIn('issue-chart', html)
        self.assertIn("const items=[...A,...F]", html)

    def test_matrix_reader_is_concise_and_drops_per_item_why_block(self):
        full = (ROOT / "frontier" / "index.html").read_text(encoding="utf-8")
        quick = (ROOT / "frontier" / "quick" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "frontier" / "frontier.js").read_text(encoding="utf-8")
        self.assertIn('Points here are capped at 80 characters', full)
        self.assertIn('capped at 80 characters', quick)
        self.assertNotIn('Why this cell', full)
        self.assertNotIn('cell-why', full)
        self.assertIn('function shortBullet(x)', js)
        self.assertIn('q.length>80', js)
        self.assertIn('cap80', js)

    def test_current_matrix_points_are_all_80_characters_or_less(self):
        js = r"""
const F=require('./frontier/frontier.js');
const D=require('./radar.json');
const v=F.buildFrontier(D);
for(const x of v.signals){
  const point=F.shortBullet(x);
  if(point.length>80){
    console.error(point.length, point);
    process.exit(2);
  }
}
if(!v.signals.length) process.exit(3);
"""
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)

    def test_reader_assets_use_current_cache_buster(self):
        for rel in [
            "index.html", "read/index.html", "frontier/index.html", "frontier/quick/index.html",
            "priorities/index.html", "shocks/index.html", "historical/index.html",
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
