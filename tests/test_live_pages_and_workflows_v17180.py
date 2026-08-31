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

    def test_reader_rankings_use_shared_source_merit_after_admission(self):
        read_js = (ROOT / 'read/issues.js').read_text(encoding='utf-8')
        frontier_js = (ROOT / 'frontier/frontier.js').read_text(encoding='utf-8')
        priorities_js = (ROOT / 'priorities/priorities.js').read_text(encoding='utf-8')
        stuff = (ROOT / 'stuff/index.html').read_text(encoding='utf-8')
        literature = (ROOT / 'literature/index.html').read_text(encoding='utf-8')
        briefing = (ROOT / 'briefing/index.html').read_text(encoding='utf-8')
        self.assertIn('RadarSourceMerit', read_js)
        self.assertIn('qualityAwareScore', frontier_js)
        self.assertIn('Merit', priorities_js)
        self.assertIn('RadarSourceMerit.compare', stuff)
        self.assertIn('RadarSourceMerit.compare', literature)
        self.assertIn('RadarSourceMerit?.scoreFor', briefing)

    def test_briefing_is_not_a_stale_generated_snapshot(self):
        briefing = (ROOT / 'briefing/index.html').read_text(encoding='utf-8')
        self.assertIn("fetch('../radar.json?ts='+Date.now()", briefing)
        self.assertNotIn('Topic digest generated:', briefing)
        self.assertIn('Nothing here is a hand-written snapshot', briefing)


if __name__ == '__main__':
    unittest.main()
