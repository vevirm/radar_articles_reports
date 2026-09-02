from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LivePagesAndEvidenceTests(unittest.TestCase):
    def test_all_evidence_reader_pages_load_live_radar_json(self):
        pages = [
            'index.html',
            'read/index.html',
            'briefing/index.html',
            'frontier/index.html',
            'frontier/quick/index.html',
            'priorities/index.html',
            'literature/index.html',
            'stuff/index.html',
        ]
        for rel in pages:
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding='utf-8')
                self.assertIn('radar.json', text)
                self.assertIn('no-store', text)

    def test_main_radar_latest_additions_uses_defined_strand_arrays(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.assertIn('const newA=A.filter(x=>x?.new_this_scan).length,newB=B.filter(x=>x?.new_this_scan).length,newC=C.filter(x=>x?.new_this_scan).length;', html)
        self.assertNotIn('const newA=a.filter(x=>x.new_this_scan).length', html)
        self.assertIn('console.error("Radar data load failed",e)', html)
        self.assertIn('safeCard(renderer,x,i)', html)
        self.assertIn('Current issues render failed', html)
        self.assertIn('The radar data itself is loaded.', html)

    def test_source_merit_remains_available_outside_matrix_but_matrix_does_not_display_it(self):
        read_js = (ROOT / 'read/issues.js').read_text(encoding='utf-8')
        frontier_js = (ROOT / 'frontier/frontier.js').read_text(encoding='utf-8')
        frontier = (ROOT / 'frontier/index.html').read_text(encoding='utf-8')
        quick = (ROOT / 'frontier/quick/index.html').read_text(encoding='utf-8')
        priorities_js = (ROOT / 'priorities/priorities.js').read_text(encoding='utf-8')
        stuff = (ROOT / 'stuff/index.html').read_text(encoding='utf-8')
        literature = (ROOT / 'literature/index.html').read_text(encoding='utf-8')
        briefing = (ROOT / 'briefing/index.html').read_text(encoding='utf-8')
        self.assertIn('RadarSourceMerit', read_js)
        self.assertIn('sourceMerit', frontier_js)  # metadata can still serve non-Matrix consumers
        self.assertIn('matrixPriorityScore', frontier_js)
        self.assertIn('Merit', priorities_js)
        self.assertIn('RadarSourceMerit.compare', stuff)
        self.assertIn('RadarSourceMerit.compare', literature)
        self.assertIn('RadarSourceMerit?.scoreFor', briefing)
        for page in (frontier, quick):
            self.assertNotIn('source_merit.js', page)
            self.assertNotIn('merit-badge', page)
            self.assertNotIn('Source strength', page)
            self.assertNotIn('Source: ${esc(m.label)}', page)
            self.assertNotIn('simple-ui.css', page)
        self.assertIn('Source quality is handled upstream', frontier)
        self.assertIn('Source quality is handled before Matrix placement', quick)

    def test_matrix_ordering_does_not_use_source_merit(self):
        frontier_js = (ROOT / 'frontier/frontier.js').read_text(encoding='utf-8')
        score_block = frontier_js.split('function matrixPriorityScore', 1)[1].split('function qualityAwareScore', 1)[0]
        self.assertNotIn('sourceMerit', score_block)
        self.assertNotIn('meritScore', score_block)
        self.assertIn('materiality', score_block)
        self.assertIn('confidence', score_block)
        self.assertIn('triage', score_block)

    def test_briefing_is_not_a_stale_generated_snapshot(self):
        briefing = (ROOT / 'briefing/index.html').read_text(encoding='utf-8')
        self.assertIn("fetch('../radar.json?ts='+Date.now()", briefing)
        self.assertNotIn('Topic digest generated:', briefing)
        self.assertIn('rebuilt from the current radar data', briefing)


if __name__ == '__main__':
    unittest.main()
