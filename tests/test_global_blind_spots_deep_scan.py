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
        self.assertEqual(len({x['document_key'] for x in prepared}), len(prepared))
        self.assertGreaterEqual(diag['curated_source_eligible'], 4)
        self.assertTrue(any(x['region'] == 'Russia' for x in prepared))
        self.assertTrue(any(x['region'] == 'United States' for x in prepared))

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

    def test_actions_have_only_explicit_manual_trigger(self):
        for workflow in ('global-ri-blind-spots.yml', 'global-ri-deep-scan-auto.yml'):
            text = (ROOT / '.github' / 'workflows' / workflow).read_text()
            self.assertIn('workflow_dispatch', text)
            self.assertNotIn('  schedule:', text)
            self.assertNotIn('  push:', text)
            self.assertNotIn('  workflow_run:', text)


if __name__ == '__main__':
    unittest.main()
