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

    def test_main_radar_restores_three_original_strands_without_analytical_dashboard(self):
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Strand A', html)
        self.assertIn('Quality papers &amp; reports', html)
        self.assertIn('Strand B', html)
        self.assertIn('Foresight methods', html)
        self.assertIn('Strand C', html)
        self.assertIn('Weak signals', html)
        self.assertIn('C=d.strand_c||[]', html)
        self.assertNotIn('function newsItems(d)', html)
        self.assertNotIn('statShock', html)
        self.assertNotIn('shockStrip', html)
        self.assertNotIn('Recent journalism and official developments', html)
        self.assertNotIn('Watchlist', html)
        self.assertIn('console.error("Radar data load failed",e)', html)
        self.assertIn('safeCard(renderer,x,i)', html)

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

    def test_stuff_workbook_is_current_even_with_legacy_hidden_workflow(self):
        # GitHub's web uploader can leave the hidden .github workflow untouched.
        # The public Stuff page therefore generates the XLSX from live radar.json;
        # a newer workflow may additionally refresh the repository snapshot.
        workflow=(ROOT / '.github' / 'workflows' / 'radar-scan.yml').read_text(encoding='utf-8')
        stuff=(ROOT / 'stuff' / 'index.html').read_text(encoding='utf-8')
        browser_generator=(ROOT / 'stuff' / 'workbook.js').read_text(encoding='utf-8')
        generator=(ROOT / 'scripts' / 'generate_stuff_workbook.js').read_text(encoding='utf-8')
        self.assertIn('workbook.js', stuff)
        self.assertIn('downloadExcel', stuff)
        self.assertIn('RadarStuffWorkbook', stuff)
        self.assertIn('buildXlsx', browser_generator)
        self.assertIn('EU relevance / 25', browser_generator)
        self.assertIn("require('../source_merit.js')", generator)
        self.assertIn("require('../stuff/workbook.js')", generator)
        if 'node scripts/generate_stuff_workbook.js' in workflow:
            self.assertIn('git add -- radar.json stuff/source_merit_ranking.xlsx', workflow)
            self.assertIn("- 'stuff/source_merit_ranking.xlsx'", workflow)
            self.assertIn("':!stuff/source_merit_ranking.xlsx'", workflow)
        else:
            self.assertIn('git add -- radar.json', workflow)
            self.assertIn('radar.json is the ONLY persistent output', workflow)

    def test_release_manifest_keeps_shocks_and_stuff_merit_workbook(self):
        manifest=(ROOT / 'scripts' / 'build_release.py').read_text(encoding='utf-8')
        self.assertIn('"shocks/index.html"', manifest)
        self.assertIn('"shocks/scenarios.js"', manifest)
        self.assertIn('"stuff/source_merit_ranking.xlsx"', manifest)
        self.assertIn('"stuff/workbook.js"', manifest)
        self.assertIn('"source_merit.js"', manifest)


    def test_matrix_ordering_does_not_use_source_merit(self):
        frontier_js = (ROOT / 'frontier/frontier.js').read_text(encoding='utf-8')
        score_block = frontier_js.split('function matrixPriorityScore', 1)[1].split('function qualityAwareScore', 1)[0]
        self.assertNotIn('sourceMerit', score_block)
        self.assertNotIn('meritScore', score_block)
        self.assertIn('materiality', score_block)
        self.assertIn('confidence', score_block)
        self.assertIn('triage', score_block)

    def test_risks_opportunities_use_repository_analytical_layer_not_matrix_inference(self):
        js = (ROOT / 'priorities' / 'priorities.js').read_text(encoding='utf-8')
        html = (ROOT / 'priorities' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('strategic_classification', js)
        self.assertIn('repository_evidence_interpretation', js)
        self.assertIn('data?.strategic_pathways', js)
        self.assertIn('data?.strand_a', js)
        self.assertIn('data?.strand_c', js)
        self.assertNotIn('buildFrontier', js)
        self.assertNotIn('column.id', js)
        self.assertNotIn('matrix_auto_cell', js)
        self.assertNotIn('sourceMerit', js)
        self.assertIn('Forward-looking risks and opportunities for EU research &amp; innovation.', html)
        self.assertNotIn('retained Radar evidence', html)
        self.assertNotIn('Matrix placement', html)
        shocks = (ROOT / 'shocks' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Realised shocks, plus cross-evidence scenarios', shocks)
        self.assertIn('RadarPriorities.buildPriorityView', shocks)
        self.assertNotIn('Matrix placement', shocks)
        self.assertIn('Reasoned shock scenarios', shocks)
        self.assertIn('scenarios.js', shocks)
        self.assertIn('Exact rows used', shocks)
        self.assertIn('Why it is easy to miss', shocks)

    def test_briefing_is_not_a_stale_generated_snapshot(self):
        briefing = (ROOT / 'briefing/index.html').read_text(encoding='utf-8')
        self.assertIn("fetch('../radar.json?ts='+Date.now()", briefing)
        self.assertNotIn('Topic digest generated:', briefing)
        self.assertIn('The newest findings on the main geopolitical themes', briefing)
        self.assertNotIn('rebuilt from the current radar data', briefing)


if __name__ == '__main__':
    unittest.main()
