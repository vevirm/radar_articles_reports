from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LivePagesAndWorkflowsTests(unittest.TestCase):
    def test_main_and_historical_are_true_four_hour_rotations(self):
        main = (ROOT / '.github/workflows/radar-scan.yml').read_text(encoding='utf-8')
        hist = (ROOT / '.github/workflows/historical-scan.yml').read_text(encoding='utf-8')
        self.assertIn("cron: '17 0,4,8,12,16,20 * * *'", main)
        self.assertNotIn('age_hours >= 6.0', main)
        self.assertIn("cron: '41 2,6,10,14,18,22 * * *'", hist)
        self.assertIn("HISTORICAL_MIN_RUNTIME_SECONDS: '0'", hist)

    def test_runtime_noise_cannot_jam_completed_scan(self):
        main = (ROOT / '.github/workflows/radar-scan.yml').read_text(encoding='utf-8')
        hist = (ROOT / '.github/workflows/historical-scan.yml').read_text(encoding='utf-8')
        self.assertIn('only radar.json can be committed', main)
        self.assertIn('only historical/historical.json can be committed', hist)
        self.assertNotIn('Could not isolate scanner output safely', main)
        self.assertNotIn('Historical scanner changed unexpected files; refusing to save anything', hist)
        self.assertIn('git add -- radar.json', main)
        self.assertIn('git add -- historical/historical.json', hist)

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

    def test_publish_jobs_rebuild_pages_after_success(self):
        main = (ROOT / '.github/workflows/radar-scan.yml').read_text(encoding='utf-8')
        hist = (ROOT / '.github/workflows/historical-scan.yml').read_text(encoding='utf-8')
        self.assertIn('/pages/builds', main)
        self.assertIn('/pages/builds', hist)
        self.assertIn("needs.scan.result == 'success'", main)
        self.assertIn("needs.scan.result == 'success'", hist)


if __name__ == '__main__':
    unittest.main()
