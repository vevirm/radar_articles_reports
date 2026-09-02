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
            'shocks/index.html',
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

    def test_source_merit_ranking_is_confined_to_stuff(self):
        reader_files = [
            'index.html', 'read/index.html', 'briefing/index.html', 'literature/index.html',
            'frontier/index.html', 'frontier/quick/index.html', 'priorities/index.html',
            'shocks/index.html', 'historical/index.html',
        ]
        for rel in reader_files:
            with self.subTest(rel=rel):
                text=(ROOT / rel).read_text(encoding='utf-8')
                self.assertNotIn('source_merit.js', text)
                self.assertNotIn('RadarSourceMerit', text)
                self.assertNotIn('merit-badge', text)
        stuff=(ROOT / 'stuff' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('source_merit.js', stuff)
        self.assertIn('source_merit_ranking.xlsx', stuff)
        self.assertIn('0–100', stuff)
        self.assertIn('EU relevance', stuff)
        helper=(ROOT / 'source_merit.js').read_text(encoding='utf-8')
        self.assertIn('scoreFor', helper)
        self.assertIn('compare', helper)
        self.assertIn("if(rel==='direct')return {points:25", helper)
        config=(ROOT / 'radar_config.json').read_text(encoding='utf-8')
        self.assertIn('Stuff audit/export workbook alone', config)
        self.assertIn('EU relevance is an explicit scanner gate', config)


    def test_historical_reader_does_not_display_or_rank_source_merit(self):
        html=(ROOT / 'historical' / 'index.html').read_text(encoding='utf-8')
        scanner=(ROOT / 'historical' / 'scan_historical.py').read_text(encoding='utf-8')
        self.assertNotIn('source_merit_label||', html)
        self.assertNotIn('class="merit"', html)
        self.assertNotIn('(int(x.get("source_merit_score",0)),int(x.get("year",0))', scanner)
        self.assertIn('Reader/corpus ordering is chronological after admission', scanner)

    def test_main_scan_refreshes_and_commits_stuff_workbook(self):
        workflow=(ROOT / '.github' / 'workflows' / 'radar-scan.yml').read_text(encoding='utf-8')
        self.assertIn('node scripts/generate_stuff_workbook.js', workflow)
        self.assertIn('git add -- radar.json stuff/source_merit_ranking.xlsx', workflow)
        self.assertIn("- 'stuff/source_merit_ranking.xlsx'", workflow)
        self.assertIn("':!stuff/source_merit_ranking.xlsx'", workflow)
        generator=(ROOT / 'scripts' / 'generate_stuff_workbook.js').read_text(encoding='utf-8')
        self.assertIn("require('../source_merit.js')", generator)
        self.assertIn('EU relevance / 25', generator)

    def test_release_manifest_keeps_shocks_and_stuff_merit_workbook(self):
        manifest=(ROOT / 'scripts' / 'build_release.py').read_text(encoding='utf-8')
        self.assertIn('"shocks/index.html"', manifest)
        self.assertIn('"stuff/source_merit_ranking.xlsx"', manifest)
        self.assertIn('"source_merit.js"', manifest)


    def test_matrix_ordering_does_not_use_source_merit(self):
        frontier_js = (ROOT / 'frontier/frontier.js').read_text(encoding='utf-8')
        score_block = frontier_js.split('function matrixPriorityScore', 1)[1].split('function qualityAwareScore', 1)[0]
        self.assertNotIn('sourceMerit', score_block)
        self.assertNotIn('meritScore', score_block)
        self.assertIn('materiality', score_block)
        self.assertIn('confidence', score_block)
        self.assertIn('triage', score_block)

    def test_risks_opportunities_are_not_derived_from_matrix(self):
        js = (ROOT / 'priorities' / 'priorities.js').read_text(encoding='utf-8')
        html = (ROOT / 'priorities' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('strategic_classification', js)
        self.assertNotIn('buildFrontier', js)
        self.assertNotIn('column.id', js)
        self.assertNotIn('sourceMerit', js)
        self.assertNotIn('current Matrix findings support this view', html)
        self.assertIn('Independent analytical product', html)
        shocks = (ROOT / 'shocks' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('scanner actively searches event language', shocks)
        self.assertIn('RadarPriorities.buildPriorityView', shocks)
        self.assertNotIn('Matrix placement', shocks)

    def test_briefing_is_not_a_stale_generated_snapshot(self):
        briefing = (ROOT / 'briefing/index.html').read_text(encoding='utf-8')
        self.assertIn("fetch('../radar.json?ts='+Date.now()", briefing)
        self.assertNotIn('Topic digest generated:', briefing)
        self.assertIn('rebuilt from the current radar data', briefing)


if __name__ == '__main__':
    unittest.main()
