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

    def test_strong_external_technology_control_can_be_signal_without_eu_in_headline(self):
        title = 'US tightens export controls on advanced AI chips to China'
        desc = 'The new technology controls restrict semiconductor research equipment and deepen US-China strategic competition.'
        self.assertTrue(sr.factual_news(title, desc))

    def test_generic_technology_launch_is_not_signal(self):
        self.assertFalse(sr.factual_news('Company launches a new smartphone', 'The device has a brighter display and a faster camera.'))

    def test_watch_theme_can_admit_signal_without_existing_ab_anchor(self):
        item = {
            'headline': 'US tightens export controls on advanced AI chips to China',
            'source': 'Reuters',
            'date': '2026-08-20T08:00Z',
            'link': 'https://example.org/signal',
            '_desc': 'The technology controls restrict semiconductor research equipment and deepen US-China strategic competition.',
            '_themes': sr.themes_for('US-China strategic competition export controls semiconductor technology research'),
            '_entities': ['united states', 'china', 'semiconductor', 'export control'],
        }
        got = sr.anchor_news([item], [])
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]['anchor_basis'], 'watch-theme')
        self.assertTrue(got[0]['what'])
        self.assertTrue(got[0]['why_it_matters'])
        self.assertTrue(got[0]['watch_theme'])

    def test_signal_ui_exposes_what_and_why_fields(self):
        page = (ROOT / 'briefing' / 'index.html').read_text(encoding='utf-8')
        js = (ROOT / 'briefing' / 'insights.js').read_text(encoding='utf-8')
        self.assertIn('What changed', page)
        self.assertIn('Why it matters for EU R&amp;I', page)
        self.assertIn('buildSignals', js)
        self.assertIn('signalWhy', js)


if __name__ == '__main__':
    unittest.main()
