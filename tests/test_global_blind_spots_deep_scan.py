"""Strict regression tests for manual global source-based Deep Scan."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import global_blind_spots_deep_scan as d


class GlobalDeepScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / 'Global R&I Blind Spots'
        self.deep = self.base / 'deep_scan'
        self.deep.mkdir(parents=True)
        self.config = d.g.load_json(ROOT / 'global_blind_spots_config.json')
        self.radar = {'strand_a': [
            {'title': 'Chinese quantum research infrastructure and industrial policy',
             'link': 'https://doi.org/10.1234/china', 'date': '2026-09-01',
             'core_message': 'China quantum technology transfer changes research infrastructure',
             'source': 'Research Policy', 'deep_scan_authoritative': True},
            {'title': 'European fusion programme', 'link': 'https://doi.org/10.1234/europe',
             'summary': 'A footnote mentions China and quantum investment',
             'core_message': 'European R&I science investment'},
            {'title': 'Russia and China critical research technology cooperation',
             'link': 'https://doi.org/10.1234/russia',
             'core_message': 'Russian scientific cooperation in quantum research',
             'source': 'Nature'}], 'strand_b': [], 'strand_c': []}

    def test_country_cannot_be_incidental_summary_mention(self):
        works = d.main_radar_matches(self.radar, self.config)
        self.assertTrue(any('Chinese quantum research' in x['title'] for x in works))
        self.assertFalse(any(x['title'] == 'European fusion programme' for x in works))

    def test_radar_overlap_is_exact_and_preserves_origin(self):
        matching = d.main_radar_matches(self.radar, self.config)
        x = next(x for x in matching if 'Chinese quantum' in x['title'])
        self.assertEqual(x['radar_overlap'], 'exact')
        self.assertEqual(x['main_radar_links'][0]['strand'], 'A')
        self.assertTrue(x['main_radar_links'][0]['deep_scan_authoritative'])
        self.assertEqual(x['assessment_status'], 'not_independently_verified_by_global_deep_scan')

    def test_dedupe_shared_china_russia_source(self):
        prepared, diag = d.plan_queue(self.radar, self.config, self.base, self.deep, 24)
        self.assertEqual(len({(x['document_key'], x['region']) for x in prepared}), len(prepared))
        self.assertGreaterEqual(diag['curated_source_eligible'], 4)
        self.assertTrue(any(x['region'] == 'Russia' for x in prepared))
        self.assertTrue(any(x['region'] == 'United States' for x in prepared))

    def test_shared_international_source_keeps_country_specific_assignments(self):
        selected, diag = d.plan_queue(self.radar, self.config, self.base, self.deep, 24)
        # Intergovernmental reports can supply leads for more than one country.
        # Neither country's lead may be silently collapsed into the other.
        family = {}
        for row in selected:
            family.setdefault(row['document_key'], set()).add(row['region'])
        self.assertTrue(any(len(regions) > 1 for regions in family.values()))

    def test_repeated_prepare_reuses_package_without_invalidating_review(self):
        radarfile = Path(self.tmp.name) / 'radar.json'
        radarfile.write_text(json.dumps(self.radar))
        manifest1, _ = d.prepare(self.base, self.deep, radarfile, batch_size=8,
                                 artifact=Path(self.tmp.name) / 'first.zip')
        # A second click, even with another batch size, retains IDs and queue.
        manifest2, path = d.prepare(self.base, self.deep, radarfile, batch_size=2,
                                    artifact=Path(self.tmp.name) / 'second.zip')
        self.assertEqual(manifest1['package_id'], manifest2['package_id'])
        self.assertEqual(manifest1['items'], manifest2['items'])
        with zipfile.ZipFile(path) as z:
            self.assertEqual(json.loads(z.read('manifest.json'))['package_id'], manifest1['package_id'])

    def test_untrusted_discovery_record_has_to_have_https(self):
        self.base.mkdir(exist_ok=True)
        (self.base / 'archive.json').write_text(json.dumps({'items': [
            {'title': 'China research funding and universities', 'url': 'http://example.com/a',
             'region': 'China', 'theme': list(self.config['themes'])[0]},
            {'title': 'China research funding and universities', 'url': 'https://example.com/b',
             'region': 'China', 'theme': list(self.config['themes'])[0]}]}))
        found = d.discoverable_candidates(self.base, self.config, [])
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['radar_overlap'], 'not_identified')

    def test_zip_contains_review_instructions_and_real_work(self):
        radarfile = Path(self.tmp.name) / 'radar.json'
        radarfile.write_text(json.dumps(self.radar))
        path = Path(self.tmp.name) / 'artifact.zip'
        manifest, path = d.prepare(self.base, self.deep, radarfile, batch_size=8, artifact=path)
        self.assertEqual(len(manifest['items']), 8)
        self.assertTrue((self.deep / 'pending_manifest.json').exists())
        with zipfile.ZipFile(path) as archive:
            self.assertIn('INSTRUCTIONS.md', archive.namelist())
            self.assertIn('RESULT_TEMPLATE.json', archive.namelist())
            txt = archive.read('INSTRUCTIONS.md').decode()
            self.assertIn('MUST open the real linked source', txt)
            self.assertIn('ALREADY be present in the main Radar', txt)
        self.assertFalse((self.deep / 'verified_findings.json').exists())

    def test_package_has_structural_questions_and_source_trails(self):
        self.base.mkdir(exist_ok=True)
        theme = 'Technology leadership and industrial capacity'
        rows = [{'title': 'Japan advanced semiconductor research programme',
                 'url': 'https://example.jp/program', 'region': 'Japan', 'theme': theme,
                 'source': 'Institution', 'source_kind': 'official_primary',
                 'signal_role': 'structural_context', 'date': '',
                 'investigation_question': 'What capability has been established and what is its measurable effect?'},
                {'title': 'Japan semiconductor research output statistics and indicators',
                 'url': 'https://different.jp/indicators', 'region': 'Japan', 'theme': theme,
                 'source': 'Statistics', 'source_kind': 'institutional_statistics',
                 'signal_role': 'trend_evidence', 'date': '2026-10-10'}]
        (self.base / 'latest.json').write_text(json.dumps({'items': rows}))
        selected, _ = d.plan_queue({'strand_a': [], 'strand_b': [], 'strand_c': []},
                                   self.config, self.base, self.deep, 24)
        first = next(x for x in selected if x['title'] == rows[0]['title'])
        self.assertEqual(first['signal_role'], 'structural_context')
        self.assertTrue(first['related_unverified_leads'])
        radarfile = Path(self.tmp.name) / 'radar.json'
        radarfile.write_text(json.dumps({'strand_a': [], 'strand_b': [], 'strand_c': []}))
        package, path = d.prepare(self.base, self.deep, radarfile,
                                  artifact=Path(self.tmp.name) / 'review.zip', batch_size=24)
        with zipfile.ZipFile(path) as archive:
            self.assertIn('programme page', archive.read('INSTRUCTIONS.md').decode())
            candidates = archive.read('CANDIDATES.md').decode()
            self.assertIn('Investigation:', candidates)
            self.assertIn('Related lead to check:', candidates)
            self.assertTrue(any(x.get('signal_role') for x in package['items']))

    def test_validate_rejects_false_keep_unverified_claim(self):
        candidate = {'candidate_id': 'a', 'radar_overlap': 'not_identified'}
        self.assertTrue(d.validate_result({'candidate_id': 'a', 'decision': 'KEEP',
                                           'specific_finding': 'Unknown'}, candidate))
        self.assertEqual(d.validate_result({'candidate_id': 'a', 'decision': 'REVIEW',
              'reason_for_review_or_drop': 'The original full report could not be opened and only a partial metadata record was found; independent evidence remains unavailable.'}, candidate), [])

    def test_keep_requires_independent_host_and_radar_comparison(self):
        row = {'candidate_id': 'a', 'radar_overlap': 'exact'}
        valid = self.good_keep()
        valid['comparison_type'] = 'not_in_main_radar'
        self.assertTrue(any('already in main Radar' in s for s in d.validate_result(valid, row)))
        valid['comparison_type'] = 'extends_main_radar'
        valid['corroboration_urls'] = ['https://original.example.net/other']
        self.assertTrue(any('same host' in s for s in d.validate_result(valid, row)))
        valid['corroboration_urls'] = ['https://independent.example.org/other']
        self.assertEqual(d.validate_result(valid, row), [])

    def good_keep(self):
        return {'candidate_id': 'a', 'decision': 'KEEP',
                'verified_title': 'A verified original study on investment and policy',
                'verified_primary_url': 'https://original.example.net/study',
                'source_date': '2026-09-12', 'source_type': 'published report',
                'source_identity_basis': 'The publisher article heading, organisation, document number and full report tables directly match the supplied manifest identity and title.',
                'evidence_location': 'section 2 page 17 table 3',
                'specific_finding': 'An independently read original report demonstrates a documented change in research funding distribution with identified sectors and the observed timing in its tables.',
                'primary_evidence_summary': 'The data in the detailed report provide year-on-year changes in disclosed research expenditure and identify the programme conditions and statistical bounds.',
                'corroboration_urls': ['https://independent.example.org/data'],
                'corroboration_assessment': 'The independent statistical comparison broadly supports the direction of the change but not every programme-level attribution.',
                'mechanism_and_ri_importance': 'This change affects the structure of national research institutions and changes where international scientific cooperation and talent recruitment can expand.',
                'eu_radar_comparison': 'This complements existing EU-centred coverage and adds the original non-EU statistical mechanism.',
                'comparison_type': 'extends_main_radar',
                'method_and_limitations': 'Some data are preliminary estimates with incomplete time coverage.',
                'confidence': 'medium'}

    def test_import_only_promotes_keep_and_never_writes_main_radar(self):
        c = {'candidate_id': 'a', 'document_key': 'docA', 'region': 'China', 'theme': 'Technology leadership and industrial capacity',
             'title': 'China research investment changes', 'date': '2026-09-12', 'url': 'https://original.example.net/study',
             'source': 'research', 'source_kind': 'official_statistics', 'provenance': 'curated_high_quality_source',
             'main_radar_links': [{'strand': 'A', 'title': 'China research investment changes',
                                  'url': 'https://original.example.net/study'}], 'radar_overlap': 'exact'}
        b = {**c, 'candidate_id': 'b', 'document_key': 'docB', 'title': 'Russia technology funding', 'region': 'Russia',
             'main_radar_links': [], 'radar_overlap': 'not_identified'}
        manifest = {'schema': d.SCHEMA, 'package_id': 'abc', 'items': [c, b]}
        (self.deep / 'pending_manifest.json').write_text(json.dumps(manifest))
        good = self.good_keep()
        review = {'candidate_id': 'b', 'decision': 'REVIEW',
                  'reason_for_review_or_drop': 'The university published a data table, but the provenance of its underlying sample and independent replication cannot yet be established.'}
        response = Path(self.tmp.name) / 'answers.json'
        response.write_text(json.dumps({'schema': d.SCHEMA, 'package_id': 'abc', 'results': [good, review]}))
        self.assertEqual(d.import_results(response, deep=self.deep), {'processed': 2, 'verified_keep': 1})
        rows = d.g.load_json(self.deep / 'verified_findings.json')['items']
        self.assertEqual(len(rows), 2)
        self.assertEqual(sum(x['decision'] == 'KEEP' for x in rows), 1)
        self.assertIn('China research investment changes', (self.deep / 'VERIFIED_FINDINGS.md').read_text())
        self.assertNotIn('Russia technology funding', (self.deep / 'VERIFIED_FINDINGS.md').read_text())
        self.assertEqual(len((self.deep / 'verified_findings.csv').read_text(encoding='utf-8-sig').splitlines()), 2)

    def test_import_invalid_is_atomic(self):
        candidate = {'candidate_id': 'a', 'document_key': 'x', 'radar_overlap': 'exact'}
        (self.deep / 'pending_manifest.json').write_text(json.dumps({'schema': d.SCHEMA,
                  'package_id': 'test', 'items': [candidate]}))
        data = {'schema': d.SCHEMA, 'package_id': 'test', 'results': [{'candidate_id': 'a', 'decision': 'KEEP'}]}
        path = Path(self.tmp.name) / 'invalid.json'
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'REJECTED'):
            d.import_results(path, deep=self.deep)
        self.assertFalse((self.deep / 'verified_findings.json').exists())

    def _sample_manifest(self, package_id, candidate_id, doc_key, region):
        return {'schema': d.SCHEMA, 'package_id': package_id, 'items': [{
            'candidate_id': candidate_id, 'document_key': doc_key,
            'region': region, 'theme': 'Technology leadership and industrial capacity',
            'title': f'{region} science and innovation evidence',
            'url': f'https://original.example.net/{doc_key}',
            'source': 'Independent research', 'date': '2026-09-12',
            'main_radar_links': [], 'radar_overlap': 'not_identified'}]}

    def _sample_results(self, package_id, candidate_id):
        item = dict(self.good_keep())
        item['candidate_id'] = candidate_id
        item['comparison_type'] = 'not_in_main_radar'
        return {'schema': d.SCHEMA, 'package_id': package_id, 'results': [item]}

    def test_recover_old_package_and_windows_duplicate_without_manual_rename(self):
        # The actual user case: imported Package 1 remains in inbox;
        # new Package 2 is uploaded as Windows' ' (1).json'.
        inbox = self.deep / 'inbox'
        inbox.mkdir()
        (inbox / 'README.txt').write_text('Leave this file alone')
        first = self._sample_manifest('gri-first', 'a', 'doc1', 'China')
        second = self._sample_manifest('gri-second', 'b', 'doc2', 'Australia')
        (self.deep / 'pending_manifest.json').write_text(json.dumps(first))
        old = inbox / 'global_deep_scan_results.json'
        old.write_text(json.dumps(self._sample_results('gri-first', 'a')))
        self.assertEqual(d.import_results(old, deep=self.deep)['verified_keep'], 1)
        # The old importer did NOT remove the inbox file.
        self.assertTrue(old.exists())
        (self.deep / 'pending_manifest.json').write_text(json.dumps(second))
        new = inbox / 'global_deep_scan_results (1).json'
        new.write_text(json.dumps(self._sample_results('gri-second', 'b')))
        result = d.import_inbox(self.deep)
        self.assertEqual(result, {'imported': 1, 'archived_old': 1, 'unmatched': 0})
        self.assertFalse(old.exists())
        self.assertFalse(new.exists())
        self.assertTrue((inbox / 'README.txt').exists())
        archived = list((self.deep / 'processed_inbox').glob('*.json'))
        self.assertEqual(len(archived), 2)
        records = d.g.load_json(self.deep / 'verified_findings.json')['items']
        self.assertEqual({x['package_id'] for x in records}, {'gri-first', 'gri-second'})
        self.assertEqual(sum(x['decision'] == 'KEEP' for x in records), 2)
        self.assertEqual(d.g.load_json(self.deep / 'last_import.json')['package_id'], 'gri-second')

    def test_inbox_reupload_identical_package_does_not_reimport(self):
        inbox = self.deep / 'inbox'
        inbox.mkdir()
        manifest = self._sample_manifest('gri-repeat', 'a', 'doc1', 'China')
        (self.deep / 'pending_manifest.json').write_text(json.dumps(manifest))
        new = inbox / 'global_deep_scan_results_gri-repeat.json'
        results = self._sample_results('gri-repeat', 'a')
        new.write_text(json.dumps(results))
        self.assertEqual(d.import_inbox(self.deep)['imported'], 1)
        first = d.g.load_json(self.deep / 'verified_findings.json')['items']
        first_reviewed_at = first[0]['reviewed_at']
        new.write_text(json.dumps(results))
        self.assertEqual(d.import_inbox(self.deep), {'imported': 0, 'archived_old': 1, 'unmatched': 0})
        second = d.g.load_json(self.deep / 'verified_findings.json')['items']
        self.assertEqual(second[0]['reviewed_at'], first_reviewed_at)
        self.assertFalse(new.exists())
        self.assertEqual(len(list((self.deep / 'processed_inbox').glob('*.json'))), 1)

    def test_unrecognised_previous_package_does_not_block_current(self):
        inbox = self.deep / 'inbox'
        inbox.mkdir()
        (self.deep / 'pending_manifest.json').write_text(json.dumps(
            self._sample_manifest('gri-current', 'a', 'docA', 'China')))
        unmatched = inbox / 'global_deep_scan_results_old.json'
        unmatched.write_text(json.dumps(self._sample_results('gri-other', 'b')))
        current = inbox / 'global_deep_scan_results_gri-current.json'
        current.write_text(json.dumps(self._sample_results('gri-current', 'a')))
        result = d.import_inbox(self.deep)
        self.assertEqual(result, {'imported': 1, 'archived_old': 0, 'unmatched': 1})
        self.assertTrue(unmatched.exists())
        self.assertFalse(current.exists())

    def test_invalid_package_remains_in_inbox_and_archive_unchanged(self):
        inbox = self.deep / 'inbox'
        inbox.mkdir()
        (self.deep / 'pending_manifest.json').write_text(json.dumps(
            self._sample_manifest('gri-invalid', 'a', 'docA', 'China')))
        current = inbox / 'global_deep_scan_results (3).json'
        current.write_text(json.dumps({'schema': d.SCHEMA, 'package_id': 'gri-invalid',
                                       'results': [{'candidate_id': 'a', 'decision': 'KEEP'}]}))
        with self.assertRaisesRegex(ValueError, 'REJECTED'):
            d.import_inbox(self.deep)
        self.assertTrue(current.exists())
        self.assertFalse((self.deep / 'verified_findings.json').exists())
        self.assertFalse((self.deep / 'processed_inbox').exists())

    def test_different_replies_same_package_do_not_clobber_one_another(self):
        inbox = self.deep / 'inbox'
        inbox.mkdir()
        (self.deep / 'pending_manifest.json').write_text(json.dumps(
            self._sample_manifest('gri-dupe', 'a', 'docA', 'China')))
        one = self._sample_results('gri-dupe', 'a')
        two = self._sample_results('gri-dupe', 'a')
        two['results'][0]['specific_finding'] += ' A materially different claim.'
        (inbox / 'global_deep_scan_results.json').write_text(json.dumps(one))
        (inbox / 'global_deep_scan_results (1).json').write_text(json.dumps(two))
        with self.assertRaisesRegex(ValueError, 'Different files'):
            d.import_inbox(self.deep)
        self.assertFalse((self.deep / 'verified_findings.json').exists())
        self.assertEqual(len(list(inbox.glob('*.json'))), 2)

    def test_arbitrary_filename_imports_by_json_package_id(self):
        inbox = self.deep / 'inbox'
        inbox.mkdir()
        (self.deep / 'pending_manifest.json').write_text(json.dumps(
            self._sample_manifest('gri-arbitrary', 'a', 'docA', 'China')))
        arbitrary = inbox / 'deep_scan_results (16).json'
        arbitrary.write_text(json.dumps(self._sample_results('gri-arbitrary', 'a')))
        self.assertEqual(d.import_inbox(self.deep)['imported'], 1)
        self.assertFalse(arbitrary.exists())
        self.assertEqual(len(list((self.deep / 'processed_inbox').glob('*.json'))), 1)
        self.assertEqual(d.g.load_json(self.deep / 'last_import.json')['package_id'], 'gri-arbitrary')

    def test_unrelated_json_does_not_block_valid_filename_agnostic_result(self):
        inbox = self.deep / 'inbox'
        inbox.mkdir()
        (self.deep / 'pending_manifest.json').write_text(json.dumps(
            self._sample_manifest('gri-arbitrary', 'a', 'docA', 'China')))
        unrelated = inbox / 'notes.json'
        unrelated.write_text(json.dumps({'kind': 'some-other-document'}))
        result = inbox / 'anything.JSON'
        result.write_text(json.dumps(self._sample_results('gri-arbitrary', 'a')))
        self.assertEqual(d.import_inbox(self.deep), {'imported': 1, 'archived_old': 0, 'unmatched': 1})
        self.assertTrue(unrelated.exists())
        self.assertFalse(result.exists())

    def test_scanner_manual_only_deep_scan_push_is_import_only(self):
        scan = (ROOT / '.github/workflows/global-ri-blind-spots.yml').read_text()
        deep = (ROOT / '.github/workflows/global-ri-deep-scan-auto.yml').read_text()
        for text in (scan, deep):
            self.assertIn('workflow_dispatch', text)
            self.assertNotIn('  schedule:', text)
            self.assertNotIn('  workflow_run:', text)
        self.assertNotIn('  push:', scan)
        self.assertIn("'Global R&I Blind Spots/deep_scan/inbox/*.json'", deep)
        self.assertIn('import-inbox', deep)
        self.assertIn('processed_inbox', deep)
        self.assertNotIn('copilot-requests:', deep)
        self.assertNotIn('OPENAI_API_KEY', deep)
        self.assertIn("inputs.operation == 'prepare'", deep)
        self.assertIn("inputs.operation == 'import'", deep)


if __name__ == '__main__':
    unittest.main()
