from pathlib import Path
import json
import unittest
import sys, types
try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    sys.modules['feedparser'] = types.ModuleType('feedparser')

from scripts import scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


class WiderWeakSignalRecallTests(unittest.TestCase):
    def test_eu_reframing_evidence_no_longer_needs_early_stage_marker(self):
        title = "New data show Europe's quantum research capability gap widening against the US and China"
        desc = (
            "A new study of research publications and investment data shows European quantum innovation capacity "
            "lagging amid strategic technology competition."
        )
        self.assertFalse(any(m in sr.normalized(f"{title} {desc}") for m in ['pilot', 'trial', 'draft', 'proposal', 'delay']))
        self.assertTrue(sr.reframing_signal_text(f"{title} {desc}"))
        self.assertTrue(sr.factual_news(title, desc))

    def test_global_comparative_evidence_can_prefilter_but_needs_eu_anchor(self):
        title = "New study shows China and US pulling ahead in quantum research publications"
        desc = (
            "Publication data reveal a widening innovation-capacity gap in quantum technology and strategic competition."
        )
        self.assertTrue(sr.factual_news(title, desc))
        news = [{
            'headline': title,
            'source': 'Nature',
            'date': '2026-08-20T08:00Z',
            'link': 'https://example.org/quantum-data',
            '_desc': desc,
            '_themes': sr.themes_for(f'{title} {desc}'),
            '_entities': sr.distinct_matches(f'{title} {desc}', sr.ENTITY_TERMS + sr.GEO_ACTORS),
        }]
        self.assertEqual(sr.anchor_news(news, []), [])

    def test_generic_foreign_technology_launch_still_fails(self):
        self.assertFalse(sr.factual_news(
            'US company launches new AI chip',
            'The company announced a faster processor for data centres.'
        ))

    def test_empirical_news_analysis_label_can_pass(self):
        self.assertTrue(sr.factual_news(
            'Analysis: New survey finds European researcher outflow to the US accelerating',
            'The study reports new data on researcher mobility and brain drain from Europe, with implications for research capacity and competitiveness.'
        ))


class RIFuturesMethodRecallTests(unittest.TestCase):
    def test_accepts_new_forward_looking_ri_method_without_foresight_label(self):
        ev = sr.gate_scope(
            'A new bibliometric forecasting methodology for detecting emerging research fronts in quantum technologies',
            'We develop a reusable bibliometric forecasting method that uses publication networks to detect emerging research fronts and forecast research and innovation trajectories.',
            '', 2, source_kind='scholarly'
        )
        self.assertTrue(ev['b_pass'])
        self.assertEqual(ev['b_route'], 'ri-futures-analytic-method')
        self.assertFalse(ev['a_pass'])

    def test_accepts_new_patent_technology_trajectory_method(self):
        ev = sr.gate_scope(
            'Developing a patent analytics method for emerging technology trajectories',
            'This paper develops a patent analytics framework to identify technology emergence, convergence and future innovation trajectories across technology fields.',
            '', 2, source_kind='scholarly'
        )
        self.assertTrue(ev['b_pass'])

    def test_accepts_new_ri_portfolio_method_under_strategic_uncertainty(self):
        ev = sr.gate_scope(
            'A new multi-criteria portfolio methodology for R&I under strategic uncertainty',
            'We develop a multi-criteria portfolio method for research and innovation investment decisions under strategic uncertainty and long-term technology change.',
            '', 2, source_kind='scholarly'
        )
        self.assertTrue(ev['b_pass'])
        self.assertEqual(ev['b_route'], 'ri-futures-analytic-method')

    def test_descriptive_bibliometrics_without_new_method_still_fails(self):
        ev = sr.gate_scope(
            'Bibliometric analysis of European artificial intelligence research',
            'The study maps publication counts, countries and citation patterns from 2015 to 2025.',
            '', 2, source_kind='scholarly'
        )
        self.assertFalse(ev['b_pass'])

    def test_domain_prediction_method_without_ri_futures_route_still_fails(self):
        ev = sr.gate_scope(
            'A new forecasting method for hospital bed demand',
            'We develop a forecasting model for daily hospital bed demand and clinical operations.',
            '', 2, source_kind='scholarly'
        )
        self.assertFalse(ev['b_pass'])


class ExpansionOnlyStateTests(unittest.TestCase):
    def test_bundled_radar_is_supplied_current_state(self):
        data = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
        self.assertEqual(len(data.get('strand_a', [])), 141)
        self.assertEqual(len(data.get('strand_b', [])), 23)
        self.assertEqual(len(data.get('strand_c', [])), 14)
        self.assertEqual(len(data.get('frontier_evidence', [])), 32)
        # Manual review must not advance scanner timestamps/cursors. These values come
        # from the supplied 25 August state and remain unchanged by Additions III.
        self.assertEqual(data.get('last_updated'), '2026-08-25T10:58Z')
        self.assertEqual(data['scan_state']['crossref_broad_cursor'], 61)
        self.assertEqual(data['scan_state']['crossref_priority_cursor'], 320)
        self.assertEqual(data.get('manual_ingest_profile_version'), 'v17.11.1-reviewed-manual-evidence')
        latest = data.get('manual_ingest', {}).get('batches', [])[-1]
        self.assertEqual(latest.get('source_file'), 'EU_RI_Additions_III_May-Aug_2026.docx')
        self.assertEqual(latest.get('counts', {}).get('manual_admitted'), 3)
        self.assertEqual(latest.get('counts', {}).get('manual_signals_admitted'), 2)
        self.assertEqual(latest.get('counts', {}).get('rejected_core_gate'), 1)
        self.assertEqual(latest.get('counts', {}).get('duplicate_in_batch'), 1)

    def test_current_state_needs_no_signal_or_quality_backfill(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        data = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
        self.assertEqual(cfg['quality_profile_version'], data['quality_profile_version'])
        self.assertEqual(cfg['signal_quality_profile_version'], data['signal_quality_profile_version'])
        self.assertEqual(cfg['signal_discovery_version'], data['signal_discovery_version'])
        self.assertFalse(sr.needs_signal_backfill(data))
        self.assertFalse(sr.needs_precision_corpus_cleanup(data))
        self.assertFalse(sr.needs_precision_signal_cleanup(data))

    def test_additions_iii_recall_sources_are_targeted_and_bounded(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        institutional = {x['domain'] for x in cfg['institution_sources']}
        news = {x['domain'] for x in cfg['news_sources']}
        # Additions III exposed two high-value institutional coverage gaps and one
        # specialist defence-tech news gap. Add only those bounded sources rather
        # than lowering the substantive admission gate.
        self.assertIn('health.ec.europa.eu', institutional)
        self.assertIn('cepr.org', institutional)
        self.assertIn('defensenews.com', news)

    def test_scan_banks_are_wider_but_bounded(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(cfg['queries_b_method_per_scan'], 8)
        self.assertGreaterEqual(len(cfg['queries_b_method']), 28)
        self.assertGreaterEqual(len(cfg['news_global_queries']), 30)
        self.assertEqual(len(sr.news_queries('example.org', 168)), 4)
        self.assertEqual(cfg['quality_profile_version'], 'v17.9.0-source-aware-aboutness-matrix-rubric')
        self.assertEqual(cfg['signal_quality_profile_version'], 'v17.9.0-source-aware-aboutness-matrix-rubric')


if __name__ == '__main__':
    unittest.main()
