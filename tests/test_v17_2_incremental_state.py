import json
import datetime as dt
import unittest
from pathlib import Path
from unittest import mock

import scripts.scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


class V172IncrementalStateTests(unittest.TestCase):
    def test_rotating_batch_advances_without_repeating_inside_wrap_run(self):
        items = list(range(10))
        b1, c1, w1 = sr.rotating_batch(items, 0, 4)
        b2, c2, w2 = sr.rotating_batch(items, c1, 4)
        b3, c3, w3 = sr.rotating_batch(items, c2, 4)
        self.assertEqual(b1, [0, 1, 2, 3])
        self.assertEqual(b2, [4, 5, 6, 7])
        self.assertEqual(b3, [8, 9])
        self.assertFalse(w1)
        self.assertFalse(w2)
        self.assertTrue(w3)
        self.assertEqual(c3, 0)

    def test_incremental_caps_are_smaller_than_full_source_universe(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        query_total = len(cfg['queries_a']) + len(cfg['queries_b'])
        priority_total = len(cfg['crossref_priority_journals']) * len(cfg['crossref_priority_journal_queries'])
        self.assertLess(cfg['openalex_queries_per_scan'], query_total)
        self.assertLess(cfg['crossref_broad_queries_per_scan'], query_total)
        self.assertLess(cfg['crossref_priority_tasks_per_scan'], priority_total)
        self.assertLess(cfg['institution_sources_per_scan'], len(cfg['institution_sources']))

    def test_scan_state_persists_independent_source_cursors(self):
        state = sr.initial_scan_state({})
        self.assertEqual(state['version'], sr.INCREMENTAL_STATE_VERSION)
        self.assertIn('openalex_cursor', state)
        self.assertIn('crossref_broad_cursor', state)
        self.assertIn('crossref_priority_cursor', state)
        self.assertIn('institution_cursor', state)
        self.assertFalse(state['backfill']['openalex'])
        self.assertFalse(state['backfill']['institutions'])
        self.assertEqual(state['institution_seen_fingerprints'], {})

    def test_known_previous_items_are_loaded_before_discovery(self):
        prev = {
            'strand_a': [{'title': 'Known paper', 'link': 'https://doi.org/10.1234/ABC'}],
            'strand_b': [{'title': 'Known report', 'link': 'https://example.org/report'}],
            'strand_c': [{'headline': 'Known signal', 'source': 'Reuters', 'link': 'https://example.org/s'}],
        }
        ab, links, signals = sr.known_sets_from_previous(prev)
        self.assertIn('doi:10.1234/abc', ab)
        self.assertIn('https://example.org/report', links)
        self.assertIn('signal:reuters:known signal', signals)

    def test_institution_discovery_skips_successfully_scanned_page_fingerprint(self):
        url = 'https://example.org/reports/eu-research-security-report'
        lastmod = dt.date.today()
        fp = sr.institution_fingerprint(url, lastmod)
        old = dict(sr.INSTITUTION_SEEN_FINGERPRINTS)
        try:
            sr.INSTITUTION_SEEN_FINGERPRINTS = {fp: '2026-08-20T12:00Z'}
            with mock.patch.object(sr, 'SCAN_DEADLINE_MONO', None), \
                 mock.patch.object(sr, 'discover_sitemaps', return_value=['https://example.org/sitemap.xml']), \
                 mock.patch.object(sr, 'sitemap_entries', return_value=[(url, lastmod)]), \
                 mock.patch.object(sr, 'institution_url_score', return_value=10):
                jobs, warning = sr._discover_domain({'domain': 'example.org', 'name': 'Example', 'tier': 1}, lastmod)
            self.assertEqual(jobs, [])
            self.assertIsNone(warning)
        finally:
            sr.INSTITUTION_SEEN_FINGERPRINTS = old

    def test_repeated_bundle_upload_recovers_live_v172_cursor_state(self):
        current = {
            'repository_bundle_seed': 'seed',
            'strand_a': [], 'strand_b': [], 'strand_c': [],
            'scan_state': sr.initial_scan_state({}),
        }
        recovered_state = sr.initial_scan_state({})
        recovered_state['openalex_cursor'] = 80
        recovered = {
            'strand_a': [{'title': 'Recovered', 'link': 'https://doi.org/10.1234/recovered'}],
            'strand_b': [], 'strand_c': [],
            'scan_state': recovered_state,
        }
        merged = sr._merge_saved_snapshots(current, recovered)
        self.assertEqual(merged['scan_state']['openalex_cursor'], 80)
        self.assertEqual(len(merged['strand_a']), 1)

    def test_upload_commit_triggers_immediate_scan_and_schedule_remains_12_hourly(self):
        workflow = (ROOT / '.github' / 'workflows' / 'radar-scan.yml').read_text(encoding='utf-8')
        self.assertIn('push:', workflow)
        self.assertIn('branches: [main]', workflow)
        self.assertIn("cron: '23 */12 * * *'", workflow)
        self.assertIn('workflow_dispatch:', workflow)
        self.assertIn('paths-ignore:', workflow)
        self.assertIn('- radar.json', workflow)

    def test_source_families_have_separate_time_slices(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text(encoding='utf-8'))
        self.assertLess(cfg['news_stage_seconds'], cfg['scan_budget_seconds'])
        self.assertLess(cfg['openalex_stage_seconds'], cfg['scan_budget_seconds'])
        self.assertLess(cfg['crossref_stage_seconds'], cfg['scan_budget_seconds'])
        self.assertLess(cfg['institution_stage_seconds'], cfg['scan_budget_seconds'])
        self.assertGreaterEqual(cfg['network_reserve_seconds'], 120)


if __name__ == '__main__':
    unittest.main()
