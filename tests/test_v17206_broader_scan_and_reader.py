import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class V17206BroaderScanAndReaderTests(unittest.TestCase):
    def test_scanner_has_broader_a_b_source_and_query_rotation_without_changing_main_strands(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(len(cfg.get('institution_sources', [])), 100)
        self.assertGreaterEqual(len(cfg.get('queries_a', [])), 180)
        self.assertGreaterEqual(len(cfg.get('queries_b', [])), 40)
        self.assertGreaterEqual(len(cfg.get('queries_b_method', [])), 40)
        names = {str(x.get('name', '')).lower() for x in cfg.get('institution_sources', []) if isinstance(x, dict)}
        for expected in ('european university institute', 'european court of auditors', 'european science foundation'):
            self.assertIn(expected, names)
        a = ' '.join(cfg.get('queries_a', [])).lower()
        for term in ('research security', 'science diplomacy', 'strategic dependencies', 'technology standards'):
            self.assertIn(term, a)

    def test_every_scan_has_strategic_queries_for_risks_opportunities_and_external_shocks(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        scholarly = cfg.get('strategic_pathway_scholarly_queries', {})
        news = cfg.get('strategic_pathway_news_queries', {})
        for kind in ('risk', 'opportunity', 'external_shock'):
            self.assertGreaterEqual(len(scholarly.get(kind, [])), 4)
            self.assertGreaterEqual(len(news.get(kind, [])), 4)
        self.assertGreaterEqual(int(cfg.get('strategic_pathway_scholarly_queries_per_category', 0)), 4)
        py = (ROOT / 'scripts' / 'scan_radar.py').read_text(encoding='utf-8')
        self.assertIn("for kind in ('risk', 'opportunity', 'external_shock')", py)
        self.assertIn('reader_products_refresh', py)
        self.assertIn('last_reader_products_refresh', py)

    def test_matrix_risks_and_shocks_rebuild_from_fresh_radar_json(self):
        for rel in ('frontier/quick/index.html', 'frontier/index.html', 'priorities/index.html', 'shocks/index.html', 'read/index.html'):
            html = (ROOT / rel).read_text(encoding='utf-8')
            self.assertRegex(html, r"fetch\([^\n]*radar\.json\?ts='?\+?Date\.now\(\)")
            self.assertIn("cache:'no-store'", html)

    def test_read_at_least_this_is_eight_compact_linked_topic_trees(self):
        html = (ROOT / 'read' / 'index.html').read_text(encoding='utf-8')
        js = (ROOT / 'read' / 'issues.js').read_text(encoding='utf-8')
        self.assertIn('min-height:268px', html)
        self.assertIn('class="node-meta"', html)
        self.assertIn('Radar →', html)
        self.assertIn('sourceLink', js)
        self.assertIn('evidenceCount', js)
        self.assertIn('buildTrees(items,{count:8})', html)

    def test_external_shock_page_has_top_index_and_more_scenario_families(self):
        html = (ROOT / 'shocks' / 'index.html').read_text(encoding='utf-8')
        js = (ROOT / 'shocks' / 'scenarios.js').read_text(encoding='utf-8')
        variants = (ROOT / 'shocks' / 'variants.js').read_text(encoding='utf-8')
        self.assertIn('id="shockIndex"', html)
        self.assertIn('Shock index', html)
        for sid in ('energy_compute_rationing', 'scaleup_acquisition_drain', 'standards_interoperability_split', 'open_science_security_collision'):
            self.assertIn(sid, js)
        self.assertIn('genericProfile', variants)
        self.assertIn("['strand_a','A'],['strand_c','C'],['strategic_pathways','P']", js)

    def test_four_hour_rotation_and_twenty_four_minute_scan_budget(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        self.assertEqual(cfg.get('scan_budget_seconds'), 1440)
        wf = (ROOT / '.github' / 'workflows' / 'radar-scan.yml').read_text(encoding='utf-8')
        self.assertIn("cron: '17 0,4,8,12,16,20 * * *'", wf)
        self.assertIn('fixed four-hour scheduled scan', wf)
        self.assertIn('age_hours >= 4.0', wf)
        self.assertIn('timeout-minutes: 36', wf)
        self.assertRegex(wf.split('  publish:', 1)[1], r'timeout-minutes:\s*6')


if __name__ == '__main__':
    unittest.main()
