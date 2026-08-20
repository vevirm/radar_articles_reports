import json
import unittest
from pathlib import Path

import scripts.scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


class V17EvidenceQualityTests(unittest.TestCase):
    def test_scan_budget_is_close_to_an_hour_and_job_has_commit_margin(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        self.assertEqual(cfg['scan_budget_seconds'], 3300)
        workflow = (ROOT / '.github' / 'workflows' / 'radar-scan.yml').read_text(encoding='utf-8')
        self.assertIn('timeout-minutes: 90', workflow)

    def test_scholarly_discovery_has_dedicated_priority_sweep(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(len(cfg.get('queries_a', [])), 100)
        self.assertGreaterEqual(len(cfg.get('queries_b', [])), 25)
        self.assertGreaterEqual(len(cfg.get('crossref_priority_journals', [])), 30)
        self.assertGreaterEqual(len(cfg.get('crossref_priority_journal_queries', [])), 6)

    def test_insights_default_is_balanced_not_signal_only(self):
        page = (ROOT / 'briefing' / 'index.html').read_text(encoding='utf-8')
        self.assertIn("mode:'all'", page)
        self.assertIn('Research publications', page)
        self.assertIn('EU &amp; institutional reports', page)
        self.assertIn('Weak signals', page)
        self.assertIn('data-mode="all"', page)

    def test_quality_migration_removes_old_false_positive_but_keeps_relevant_tech_report(self):
        previous = {
            'strand_a': [
                {
                    'title': '2026 Rule of law report - Communication and country chapters',
                    'summary': 'The European Commission reviews justice systems, media pluralism and anti-corruption across EU Member States.',
                    'type': 'institutional report', 'source_tier': 'Tier 1'
                },
                {
                    'title': 'Nuclear technology dependencies and European strategic autonomy',
                    'summary': 'The EU relies on non-EU reactor technology vendors, raising strategic dependencies, economic-security and technology sovereignty concerns.',
                    'type': 'institutional report', 'source_tier': 'Tier 1'
                },
            ],
            'strand_b': [
                {
                    'title': 'PATHWAYS TO ZERO WASTE: PROSPECTIVE SCIENCE TEACHERS’ SOLUTIONS THROUGH EVERYDAY LIFE SCENARIOS',
                    'summary': 'Prospective science teachers use scenarios to design household waste solutions and sustainability learning activities.',
                    'type': 'peer-reviewed article', 'source_tier': 'Tier 2 broad journal'
                }
            ],
            'strand_c': [{'headline': 'Keep signal', 'source': 'Reuters'}]
        }
        cleaned, removed = sr.revalidate_saved_ab(previous)
        self.assertEqual(removed['strand_a'], 1)
        self.assertEqual(removed['strand_b'], 1)
        self.assertEqual(len(cleaned['strand_a']), 1)
        self.assertEqual(cleaned['strand_a'][0]['title'], 'Nuclear technology dependencies and European strategic autonomy')
        self.assertEqual(len(cleaned['strand_c']), 1)


if __name__ == '__main__':
    unittest.main()
