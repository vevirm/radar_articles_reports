from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReaderUiV17179Tests(unittest.TestCase):
    def test_landing_page_is_orientation_first_and_reader_views_are_top(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("This is the Main Radar for", html)
        self.assertIn("EU research &amp; innovation in geopolitical context.", html)
        self.assertIn('<nav class="landing-nav"', html)
        nav = html.split('<nav class="landing-nav"', 1)[1].split('</nav>', 1)[0]
        self.assertLess(nav.find('>Read at least this</a>'), nav.find('>Stuff</a>'))
        self.assertLess(nav.find('>Weak signals</a>'), nav.find('>Stuff</a>'))
        self.assertLess(nav.find('>History</a>'), nav.find('>Stuff</a>'))
        self.assertNotIn('<section class="inside-map"', html)
        self.assertNotIn('<section class="page-map"', html)
        self.assertNotIn("Next automatic", html)
        self.assertNotIn("scheduleState", html)

    def test_read_at_least_this_keeps_original_open_branch_chart(self):
        html = (ROOT / "read" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "simple-ui.css").read_text(encoding="utf-8")
        self.assertIn('class="issue-chart"', html)
        self.assertIn('class="chart-main"', html)
        self.assertIn('class="chart-branches"', html)
        self.assertIn('.issue-chart{min-width:940px!important;display:grid!important;', css)
        self.assertIn('.chart-main{display:block!important;', css)
        self.assertIn('.chart-branch{display:grid!important;', css)
        self.assertIn('.branch-node::after{display:block!important;', css)
        self.assertNotIn('chart-main{display:none!important}', css)
        self.assertNotIn('no wiring diagram', css.lower())

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
