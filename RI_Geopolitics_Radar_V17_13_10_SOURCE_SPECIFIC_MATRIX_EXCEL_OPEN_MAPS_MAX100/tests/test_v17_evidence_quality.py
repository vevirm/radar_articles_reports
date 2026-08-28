import json
import unittest
from unittest import mock
from pathlib import Path

import scripts.scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


class V17EvidenceQualityTests(unittest.TestCase):
    def test_scan_budget_finishes_inside_30_minute_job_with_commit_margin(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        self.assertEqual(cfg['scan_budget_seconds'], 1200)
        self.assertGreaterEqual(cfg.get('network_reserve_seconds', 0), 60)
        workflow = (ROOT / '.github' / 'workflows' / 'radar-scan.yml').read_text(encoding='utf-8')
        self.assertIn('timeout-minutes: 30', workflow)

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
                    'summary': 'The EU nuclear research and innovation system relies on non-EU reactor technology vendors and R&D partnerships, raising strategic dependencies, economic-security and technology-sovereignty concerns for European technological capability.',
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


    def test_inherited_corpus_audit_runs_once_independent_of_quality_profile(self):
        self.assertTrue(sr.needs_inherited_corpus_audit({}))
        self.assertTrue(sr.needs_inherited_corpus_audit({'quality_profile_version': sr.QUALITY_PROFILE_VERSION}))
        self.assertFalse(sr.needs_inherited_corpus_audit({'inherited_corpus_audit_complete': True}))

    def test_first_run_audit_refreshes_thin_saved_evidence_before_deleting(self):
        previous = {
            'strand_a': [
                {
                    'title': 'European research autonomy through international partnerships',
                    'summary': 'A short legacy summary that does not contain enough gate evidence.',
                    'link': 'https://example.test/relevant',
                    'type': 'institutional report', 'source_tier': 'Tier 1'
                },
                {
                    'title': 'Local bicycle parking regulation',
                    'summary': 'Municipal rules for bicycle parking and administrative fines.',
                    'link': 'https://example.test/irrelevant',
                    'type': 'institutional report', 'source_tier': 'Tier 1'
                },
            ],
            'strand_b': [],
            'strand_c': [{'headline': 'Keep historical signal', 'source': 'Reuters'}],
        }

        def refresh(item):
            if 'research autonomy' in item['title'].lower():
                return (
                    item['title'],
                    'European research institutions depend on non-EU technology and scientific talent. '
                    'The EU examines international research partnerships, researcher mobility, strategic autonomy '
                    'and economic security in science and innovation.',
                    ''
                )
            return (item['title'], 'Municipal bicycle parking enforcement and administrative fines.', '')

        with mock.patch.object(sr, '_audit_refresh_document', side_effect=refresh):
            cleaned, stats = sr.audit_inherited_ab(previous, [])

        self.assertEqual(len(cleaned['strand_a']), 1)
        self.assertIn('research autonomy', cleaned['strand_a'][0]['title'].lower())
        self.assertEqual(stats['refreshed_pass'], 1)
        self.assertEqual(stats['strand_a_removed'], 1)
        self.assertEqual(len(cleaned['strand_c']), 1)

    def test_matcher_preserves_ampersands_and_requires_token_boundaries(self):
        self.assertEqual(sr.clean_text('R&D'), 'R&D')
        self.assertEqual(sr.distinct_matches('regarding electric bicycles', ['r&d']), [])
        self.assertEqual(sr.distinct_matches('international security cooperation', ['national security']), [])

    def test_e_bike_regulation_false_positive_is_rejected(self):
        title = 'Regulatory Reconstruction and Law Enforcement Effectiveness Regarding Electric Bicycle Use by Minors'
        abstract = ('This article proposes regulatory reconstruction through technical standardization, strengthening '
                    'administrative sanctions, and vicarious criminal liability for negligent parents. Using a legal '
                    'research method, it compares micro-mobility regulations with standards in the European Union, '
                    'Queensland, and Mongolia.')
        evidence = sr.gate_scope(title, abstract, '', 2, 'scholarly')
        self.assertFalse(evidence['a_pass'])
        self.assertFalse(evidence['ri_evidence'])
        self.assertFalse(evidence['geo_evidence'])

    def test_research_brain_drain_is_valid_ri_geoeconomic_evidence(self):
        title = 'Choose Europe: Research Careers, Brain Drain and Policy Lessons from the CESAER Survey'
        abstract = ('Europe faces a persistent research brain drain, undermining its ability to compete globally in '
                    'science and technology. The study examines research careers and researcher mobility across '
                    'European universities.')
        evidence = sr.gate_scope(title, abstract, '', 2, 'scholarly')
        self.assertTrue(evidence['a_pass'])
        self.assertIn('research-talent flow / brain drain', evidence['ri_evidence'])
        self.assertIn('research-talent allocation / brain drain', evidence['geo_evidence'])


if __name__ == '__main__':
    unittest.main()
