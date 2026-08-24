import json
import unittest
from pathlib import Path

import scripts.scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


class V16WeakSignalTests(unittest.TestCase):
    def test_news_scan_has_rolling_week_and_one_time_30_day_recovery(self):
        self.assertGreaterEqual(sr.NEWS_LOOKBACK_HOURS, 168)
        self.assertGreaterEqual(sr.SIGNAL_BACKFILL_HOURS, 720)
        self.assertTrue(sr.needs_signal_backfill({}))
        self.assertFalse(sr.needs_signal_backfill({"signal_discovery_version": sr.SIGNAL_DISCOVERY_VERSION}))

    def test_news_source_universe_is_broad_but_curated(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(len(cfg.get('news_sources', [])), 25)
        self.assertGreaterEqual(len(cfg.get('news_global_queries', [])), 12)
        domains = {x['domain'] for x in cfg['news_sources']}
        for domain in ['reuters.com', 'ft.com', 'politico.eu', 'nature.com', 'sciencebusiness.net', 'commission.europa.eu']:
            self.assertIn(domain, domains)

    def test_external_technology_control_can_prefilter_but_still_needs_eu_anchor(self):
        title = 'US tightens export controls on advanced AI chips to China'
        desc = 'The new technology controls restrict semiconductor research equipment and deepen US-China strategic competition.'
        self.assertTrue(sr.factual_news(title, desc))
        news = [{
            'headline': title, 'source': 'Reuters', 'date': '2026-08-20T08:00Z', 'link': 'https://example.org/us-controls',
            '_desc': desc, '_themes': sr.themes_for(f'{title} {desc}'),
            '_entities': sr.distinct_matches(f'{title} {desc}', sr.ENTITY_TERMS + sr.GEO_ACTORS),
        }]
        self.assertEqual(sr.anchor_news(news, []), [])
        self.assertTrue(sr.factual_news(
            'US pilots tighter export controls on advanced AI chips to China, raising concerns for Europe',
            'A targeted trial would expose European semiconductor researchers and firms to new equipment-access constraints.'
        ))

    def test_generic_technology_launch_is_not_signal(self):
        self.assertFalse(sr.factual_news('Company launches a new smartphone', 'The device has a brighter display and a faster camera.'))

    def test_weak_signal_requires_existing_strand_a_anchor(self):
        item = {
            'headline': 'US pilots chip controls that may raise equipment-access risks for European researchers',
            'source': 'Reuters',
            'date': '2026-08-20T08:00Z',
            'link': 'https://example.org/signal',
            '_desc': 'A targeted trial would restrict semiconductor research equipment amid US-China strategic competition affecting Europe.',
            '_themes': sr.themes_for('European semiconductor research US-China strategic competition export controls'),
            '_entities': ['united states', 'china', 'semiconductor', 'export control'],
        }
        self.assertEqual(sr.anchor_news([item], []), [])

    def test_signal_ui_exposes_what_and_why_fields(self):
        page = (ROOT / 'briefing' / 'index.html').read_text(encoding='utf-8')
        js = (ROOT / 'briefing' / 'insights.js').read_text(encoding='utf-8')
        self.assertIn('What changed', page)
        self.assertIn('Why it matters for EU R&amp;I', page)
        self.assertIn('buildSignals', js)
        self.assertIn('signalWhy', js)


if __name__ == '__main__':
    unittest.main()
