import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'scripts') not in sys.path:
    sys.path.insert(0, str(ROOT / 'scripts'))
import scan_radar as sr


class V231PrimaryEvidenceSchedulerTests(unittest.TestCase):
    def test_probe_registry_does_not_stall_on_unexecuted_first_probe(self):
        state = {'probe_registry': {}}
        bank = ['q1', 'q2', 'q3']
        first = sr.least_recent_probe_batch(state, 'lane', bank, 2)
        self.assertEqual(first, ['q1', 'q2'])
        # Only q2 executes. q1 remains unvisited and therefore stays at the front; q3 is
        # also unvisited and is preferred over the already executed q2.
        sr.note_probe_execution(state, 'lane', ['q2'], '2026-09-08T10:00Z')
        second = sr.least_recent_probe_batch(state, 'lane', bank, 2)
        self.assertEqual(second, ['q1', 'q3'])

    def test_event_status_proposal_is_not_done_even_when_adopted(self):
        self.assertEqual(
            sr.signal_event_status('The Commission adopted a proposal for a new Cloud and AI Development Act.'),
            'PROPOSED',
        )

    def test_event_status_rejects_programme_funding_boilerplate(self):
        self.assertEqual(sr.signal_event_status('The partnership is co-funded by the EU through Horizon Europe.'), 'UNKNOWN')

    def test_event_status_accepts_observed_finding(self):
        self.assertEqual(
            sr.signal_event_status('The report finds that research-security measures expanded across EU Member States.'),
            'OBSERVED',
        )

    def test_publications_office_page_gets_downloadable_english_pdf_fallback(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<html><body><h1>Research security monitor 2025</h1></body></html>', 'html.parser')
        url = 'https://op.europa.eu/en/publication-detail/-/publication/7348956d-1389-11f1-8870-01aa75ed71a1/language-en'
        got = sr._primary_pdf_link(soup, url, 'Research security monitor 2025')
        self.assertIn('download-handler', got)
        self.assertIn('identifier=7348956d-1389-11f1-8870-01aa75ed71a1', got)
        self.assertIn('language=en', got)

    def test_expired_public_signal_moves_to_private_archive(self):
        import datetime as dt
        old = {
            'strand_a': [],
            'strand_b': [],
            'strand_c': [{
                'headline': 'Observed research collaboration fell sharply',
                'source': 'Example source',
                'date': '2026-06-01',
                'link': 'https://example.eu/old-signal',
                'first_seen': '2026-06-01T00:00Z',
                'evidence_status': 'low',
            }],
        }
        out, removed = sr.prune_public_window(
            old,
            dt.date(2026, 5, 1),
            now=dt.datetime(2026, 9, 8, tzinfo=dt.timezone.utc),
        )
        self.assertEqual(removed['strand_c'], 1)
        self.assertEqual(out['strand_c'], [])
        self.assertTrue(any(x.get('headline') == 'Observed research collaboration fell sharply' for x in out.get('signal_archive', [])))

    def test_precursor_watch_keeps_proposal_private(self):
        candidates = [{
            'headline': 'Commission proposes new semiconductor research framework',
            'source': 'European Commission',
            'date': '2026-09-08',
            'link': 'https://example.eu/proposal',
            '_desc': 'The Commission proposes a new EU semiconductor research framework to strengthen strategic technology capacity.',
            '_themes': ['critical and emerging technologies'],
        }]
        watch = sr.build_precursor_watch([], candidates, '2026-09-08T10:00Z')
        self.assertTrue(watch)
        self.assertEqual(watch[0]['event_status'], 'PROPOSED')
        self.assertIs(watch[0]['private_watch_only'], True)

    def test_main_whole_repo_push_can_union_stronger_preupload_snapshot(self):
        baseline = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
        current = copy.deepcopy(baseline)
        recovered = copy.deepcopy(baseline)
        extra = copy.deepcopy(recovered['strand_a'][0])
        extra['title'] = 'Synthetic retained pre-upload evidence item for continuity test'
        extra['link'] = 'https://example.eu/retained-pre-upload-evidence'
        extra['date'] = '2026-08-20'
        extra['first_seen'] = '2026-09-08T09:00Z'
        extra['new_this_scan'] = False
        recovered['strand_a'] = list(recovered['strand_a']) + [extra]

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            out = td / 'radar.json'
            seed = td / 'radar_seed.json'
            out.write_text(json.dumps(current), encoding='utf-8')
            seed.write_text(json.dumps(current), encoding='utf-8')
            with mock.patch.object(sr, 'OUT_PATH', out), \
                 mock.patch.object(sr, 'SEED_PATH', seed), \
                 mock.patch.object(sr, 'run_trigger_label', return_value='push'), \
                 mock.patch.object(sr, '_recover_radar_from_git', return_value=recovered):
                loaded = sr.load_previous(allow_git_recovery=True)

        self.assertTrue(any(x.get('title') == extra['title'] for x in loaded.get('strand_a', [])))
        self.assertGreaterEqual(len(loaded.get('strand_a', [])), len(current['strand_a']) + 1)

    def test_historical_whole_repo_push_unions_preupload_archive(self):
        import historical.scan_historical as hs

        baseline = json.loads((ROOT / 'historical' / 'historical.json').read_text(encoding='utf-8'))
        current = copy.deepcopy(baseline)
        recovered = copy.deepcopy(baseline)
        extra = copy.deepcopy(recovered['items'][0])
        extra['id'] = 'synthetic-retained-historical-pre-upload-evidence'
        extra['title'] = 'Synthetic retained historical pre-upload evidence item'
        extra['url'] = 'https://example.eu/historical-retained-pre-upload-evidence'
        extra['link'] = extra['url']
        recovered['items'] = list(recovered['items']) + [extra]
        recovered.setdefault('scan_state', {})['completed_runs'] = int(current.get('scan_state', {}).get('completed_runs', 0) or 0) + 1
        recovered['last_updated'] = '2026-09-08T11:55:00Z'

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            out = td / 'historical.json'
            seed = td / 'historical_seed.json'
            radar = td / 'radar.json'
            out.write_text(json.dumps(current), encoding='utf-8')
            seed.write_text(json.dumps(current), encoding='utf-8')
            radar.write_text(json.dumps({'historical_archive': current}), encoding='utf-8')
            with mock.patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'push'}, clear=False), \
                 mock.patch.object(hs, '_recover_historical_from_git', return_value=recovered):
                loaded = hs.load_previous_archive(out_path=out, seed_path=seed, radar_path=radar)

        self.assertTrue(any(x.get('title') == extra['title'] for x in loaded.get('items', [])))
        self.assertGreaterEqual(len(loaded.get('items', [])), len(current['items']) + 1)


if __name__ == '__main__':
    unittest.main()
