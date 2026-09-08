import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
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

    def test_download_block_without_pdf_suffix_is_a_primary_document_candidate(self):
        from bs4 import BeautifulSoup
        html = """
        <html><body><h1>Proposal for the Chips Act 2.0</h1>
          <div class='download'><span>1 - Proposal Chips Act 2.0</span>
            <a href='https://ec.europa.eu/newsroom/dae/redirection/document/129104'>Download</a>
          </div>
          <div class='download'><span>3 - Impact Assessment (Part 1)</span>
            <a href='https://ec.europa.eu/newsroom/dae/redirection/document/129106'>Download</a>
          </div>
        </body></html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        rows = sr._primary_document_candidates(
            soup, 'https://digital-strategy.ec.europa.eu/en/library/proposal-chips-act-20',
            'Proposal for the Chips Act 2.0',
        )
        self.assertTrue(rows)
        self.assertEqual(rows[0]['url'], 'https://ec.europa.eu/newsroom/dae/redirection/document/129104')
        self.assertEqual(rows[0]['role'], 'proposal')

    def test_primary_evidence_hub_follows_download_redirect_even_without_pdf_suffix(self):
        class FakeResponse:
            def __init__(self, url, content_type, text='', content=b''):
                self.url = url
                self.headers = {'content-type': content_type}
                self.text = text
                self.content = content
                self.status_code = 200

        landing_url = 'https://digital-strategy.ec.europa.eu/en/library/proposal-chips-act-20'
        doc_url = 'https://ec.europa.eu/newsroom/dae/redirection/document/129104'
        landing_html = """
        <html><head><meta property='og:title' content='Proposal for the Chips Act 2.0'>
        <meta name='date' content='2026-06-03'></head><body>
          <h1>Proposal for the Chips Act 2.0</h1>
          <div><span>1 - Proposal Chips Act 2.0</span><a href='%s'>Download</a></div>
        </body></html>
        """ % doc_url
        responses = {
            landing_url: FakeResponse(landing_url, 'text/html', text=landing_html),
            doc_url: FakeResponse(doc_url, 'application/octet-stream', content=b'%PDF-fake'),
        }
        parsed = {
            'title': 'Proposal for the Chips Act 2.0', 'source': 'European Commission — DG CONNECT',
            'date': '2026-06-03', 'link': doc_url, 'strand': 'A', 'summary': 'Synthetic test',
        }
        spec = {'url': landing_url, 'source': 'European Commission — DG CONNECT', 'tier': 1, 'label': 'Chips Act 2.0 proposal'}
        with mock.patch.object(sr, 'get', side_effect=lambda url, timeout=0: responses.get(url)), \
             mock.patch.object(sr, 'parse_institution_pdf', return_value=parsed.copy()) as pdf_parser:
            rows, status = sr._primary_evidence_from_landing(spec, [], None)
        self.assertEqual(status['status'], 'FOUND')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['link'], doc_url)
        self.assertEqual(rows[0]['landing_page_url'], landing_url)
        self.assertEqual(rows[0]['primary_document_role'], 'proposal')
        self.assertTrue(pdf_parser.called)

    def test_primary_target_is_incomplete_when_only_landing_page_is_saved(self):
        spec = {
            'url': 'https://digital-strategy.ec.europa.eu/en/library/proposal-cloud-and-ai-development-act-cada',
            'source': 'European Commission — Digital Strategy', 'tier': 1,
            'label': 'Cloud and AI Development Act (CADA) proposal',
        }
        # Regression fixtures must not depend on the live cumulative radar.json: once the
        # scanner successfully discovers the PDF, a live-corpus fixture would invert this
        # test's premise and make success break the next scheduled run.
        previous = {'strand_a': [{
            'title': 'Proposal for the Cloud and AI Development Act (CADA)',
            'source': 'European Commission — Digital Strategy',
            'date': '2026-06-03',
            'link': spec['url'],
            'landing_page_url': spec['url'],
            'primary_document_role': 'landing_page',
            'source_integrity_basis': 'institution_html',
        }]}
        self.assertFalse(sr._primary_target_present(spec, previous))

    def test_primary_target_is_incomplete_when_only_companion_annex_is_saved(self):
        spec = {
            'url': 'https://digital-strategy.ec.europa.eu/en/library/proposal-cloud-and-ai-development-act-cada',
            'source': 'European Commission — Digital Strategy', 'tier': 1,
            'label': 'Cloud and AI Development Act (CADA) proposal',
        }
        previous = {'strand_a': [{
            'title': 'Cloud and AI Development Act (CADA) — Annexes',
            'source': 'European Commission — Digital Strategy',
            'date': '2026-06-03',
            'link': 'https://ec.europa.eu/newsroom/dae/redirection/document/129112',
            'landing_page_url': spec['url'],
            'primary_evidence_target_label': spec['label'],
            'primary_document_role': 'annex',
            'source_integrity_basis': 'institution_pdf',
        }]}
        self.assertFalse(sr._primary_target_present(spec, previous))

    def test_primary_target_is_complete_when_downloadable_primary_document_is_saved(self):
        spec = {
            'url': 'https://digital-strategy.ec.europa.eu/en/library/proposal-cloud-and-ai-development-act-cada',
            'source': 'European Commission — Digital Strategy', 'tier': 1,
            'label': 'Cloud and AI Development Act (CADA) proposal',
        }
        previous = {'strand_a': [{
            'title': 'Proposal for a Regulation on Cloud and AI Development',
            'source': 'European Commission — Digital Strategy',
            'date': '2026-06-03',
            'link': 'https://ec.europa.eu/newsroom/dae/redirection/document/129200',
            'landing_page_url': spec['url'],
            'primary_evidence_target_label': spec['label'],
            'primary_document_role': 'proposal',
            'source_integrity_basis': 'institution PDF',
        }]}
        self.assertTrue(sr._primary_target_present(spec, previous))

    def test_merge_upgrades_landing_wrapper_without_fake_new_item_or_losing_first_seen(self):
        landing = 'https://digital-strategy.ec.europa.eu/en/library/proposal-cloud-and-ai-development-act-cada'
        old = {
            'title': 'Proposal for the Cloud and AI Development Act (CADA)',
            'source': 'European Commission — Digital Strategy',
            'date': '2026-06-03',
            'link': landing,
            'landing_page_url': landing,
            'strand': 'A',
            'source_integrity_basis': 'institution_html',
            'first_seen': '2026-09-08T09:59Z',
            'new_this_scan': False,
        }
        new = copy.deepcopy(old)
        new.update({
            'title': 'Proposal for a Regulation on Cloud and AI Development',
            'link': 'https://ec.europa.eu/newsroom/dae/redirection/document/129200',
            'landing_page_url': landing,
            'primary_document_role': 'proposal',
            'source_integrity_basis': 'institution_pdf',
            'primary_evidence_upgrade': True,
            'primary_evidence_upgrade_from_link': landing,
            'primary_evidence_upgrade_from_title': old['title'],
            'new_this_scan': True,
        })
        merged = sr.merge_corpus([old], [new], 'A', '2026-09-08T12:00Z')
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]['link'], new['link'])
        self.assertEqual(merged[0]['landing_page_url'], landing)
        self.assertEqual(merged[0]['first_seen'], old['first_seen'])
        self.assertFalse(merged[0]['new_this_scan'])

    def test_merge_does_not_readd_landing_wrapper_discovered_in_parallel_with_pdf(self):
        landing = 'https://digital-strategy.ec.europa.eu/en/library/proposal-cloud-and-ai-development-act-cada'
        old = {
            'title': 'Proposal for the Cloud and AI Development Act (CADA)',
            'source': 'European Commission — Digital Strategy',
            'date': '2026-06-03',
            'link': landing, 'landing_page_url': landing, 'strand': 'A',
            'source_integrity_basis': 'institution_html',
            'first_seen': '2026-09-08T09:59Z', 'new_this_scan': False,
        }
        pdf = {
            **old,
            'title': 'Proposal for a Regulation on Cloud and AI Development',
            'link': 'https://ec.europa.eu/newsroom/dae/redirection/document/129200',
            'primary_document_role': 'proposal',
            'source_integrity_basis': 'institution_pdf',
            'primary_evidence_upgrade': True,
            'primary_evidence_upgrade_from_link': landing,
        }
        rediscovered_wrapper = {**old, 'new_this_scan': True}
        merged = sr.merge_corpus([old], [pdf, rediscovered_wrapper], 'A', '2026-09-08T12:00Z')
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]['link'], pdf['link'])
        self.assertEqual(merged[0]['first_seen'], old['first_seen'])
        self.assertFalse(merged[0]['new_this_scan'])

    def test_merge_repairs_existing_wrapper_duplicate_when_primary_is_already_saved(self):
        landing = 'https://digital-strategy.ec.europa.eu/en/library/proposal-cloud-and-ai-development-act-cada'
        wrapper = {
            'title': 'Proposal for the Cloud and AI Development Act (CADA)',
            'source': 'European Commission — Digital Strategy', 'date': '2026-06-03',
            'link': landing, 'landing_page_url': landing, 'strand': 'A',
            'source_integrity_basis': 'institution_html',
            'first_seen': '2026-09-08T09:59Z', 'new_this_scan': False,
        }
        pdf = {
            'title': 'Proposal for a Regulation on Cloud and AI Development',
            'source': 'European Commission — Digital Strategy', 'date': '2026-06-03',
            'link': 'https://ec.europa.eu/newsroom/dae/redirection/document/129200',
            'landing_page_url': landing, 'strand': 'A',
            'primary_document_role': 'proposal', 'source_integrity_basis': 'institution_pdf',
            'first_seen': '2026-09-08T10:10Z', 'new_this_scan': False,
        }
        merged = sr.merge_corpus([wrapper, pdf], [], 'A', '2026-09-08T12:00Z')
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]['link'], pdf['link'])
        self.assertEqual(merged[0]['first_seen'], wrapper['first_seen'])

    def test_workflow_cumulative_guard_accepts_primary_wrapper_upgrade(self):
        workflow = (ROOT / '.github' / 'workflows' / 'radar-scan.yml').read_text(encoding='utf-8')
        self.assertIn('def primary_upgrade_landings(items):', workflow)
        self.assertIn('link in upgraded_landings', workflow)

    def test_open_call_is_precursor_not_public_done_event(self):
        claim = 'The EU launched a call for tenders to establish up to seven AI Gigafactories across Europe.'
        self.assertEqual(sr.signal_event_status(claim), 'PROPOSED')
        self.assertFalse(sr.public_signal_event_status(sr.signal_event_status(claim)))

    def test_snapshot_merge_archives_previously_accepted_c_that_no_longer_passes_public_gate(self):
        current = {'strand_a': [], 'strand_b': [], 'strand_c': [], 'last_updated': '2026-09-08T12:00:00Z'}
        recovered = copy.deepcopy(current)
        old_signal = {
            'headline': 'EU proposes a future research roadmap',
            'source': 'Example source',
            'date': '2026-08-01',
            'link': 'https://example.eu/proposed-roadmap',
            'first_seen': '2026-08-01T00:00Z',
            'signal_note': 'The EU proposes a future research roadmap for strategic technology.',
            'why_it_matters': 'This may affect European research policy.',
            'evidence_status': 'low',
        }
        recovered['strand_c'] = list(recovered.get('strand_c', [])) + [old_signal]
        merged = sr._merge_saved_snapshots(current, recovered)
        self.assertFalse(any(x.get('headline') == old_signal['headline'] for x in merged.get('strand_c', [])))
        self.assertTrue(any(x.get('headline') == old_signal['headline'] for x in merged.get('signal_archive', [])))


    def test_main_whole_repo_push_can_union_stronger_preupload_snapshot(self):
        baseline = json.loads((ROOT / 'radar.json').read_text(encoding='utf-8'))
        current = {
            'strand_a': [copy.deepcopy(baseline['strand_a'][0])],
            'strand_b': [], 'strand_c': [],
            'last_updated': '2026-09-08T10:00:00Z',
            'first_scan_complete': True,
        }
        recovered = copy.deepcopy(current)
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
                 mock.patch.object(sr, 'is_fresh_repository_seed', return_value=False), \
                 mock.patch.object(sr, '_recover_radar_from_git', return_value=recovered), \
                 mock.patch.object(sr, '_recover_signal_archive_from_git', side_effect=lambda current, *a, **k: current):
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
