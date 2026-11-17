"""Policy-only change: future selection and its Deep Scan; no retroactive results."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import relevance_focus as focus
import relevance_focus_deep_scan as deep


class NewFocusSelectionTests(unittest.TestCase):
    def test_exact_ten_critical_technologies_and_regional_priorities(self):
        self.assertEqual(len(focus.CRITICAL_TECHNOLOGIES), 10)
        self.assertEqual(set(focus.REGIONAL_PRIORITIES),
                         {'CELAC', 'Union for the Mediterranean', 'Africa', 'ASEAN'})
        self.assertEqual({r: len(t) for r, t in focus.REGIONAL_PRIORITIES.items()},
                         {'CELAC': 3, 'Union for the Mediterranean': 3, 'Africa': 4, 'ASEAN': 4})
        self.assertEqual(len(focus.focus_areas(raw={})), 24)
        self.assertEqual(focus.focus_areas(raw={}), focus.focus_areas(raw={'strand_a': [
            {'title': 'Obsolete unrelated Radar theme'}]}))

    def test_all_regional_members_covered_without_changing_legacy_country_tags(self):
        geo = focus.FOCUS_GEOGRAPHY
        celac_countries = set(geo['Americas']) - {
            'United States', 'Canada', 'Latin America and Caribbean'}
        african_countries = (set(geo['Africa']) | set(geo['Additional Africa'])) - {'Africa (region)'}
        self.assertEqual(len(celac_countries), 33)
        self.assertEqual(len(african_countries), 54)
        self.assertEqual(len(focus.MEDITERRANEAN_PRIORITY_PLACES), 16)
        self.assertEqual(len(focus.ASEAN_PRIORITY_PLACES) - 1, 11)
        self.assertNotIn('Libya', focus.MEDITERRANEAN_PRIORITY_PLACES)  # observer
        self.assertIn('Timor-Leste', focus.ASEAN_PRIORITY_PLACES)
        # The new recognisers do NOT start reclassifying stored old backfill.
        title = 'Climate change research infrastructure in Venezuela'
        self.assertFalse(focus.aboutness_locations(title))
        self.assertIn('Venezuela', [place for _, place, *_ in
                      focus.aboutness_locations(title, policy=True)])

    def test_all_twenty_four_priorities_reach_real_provider_queries(self):
        queries = list(focus.focused_search_plan(17))
        self.assertTrue(queries)
        self.assertEqual({x[2] for x in queries}, set(focus.focus_areas()))
        self.assertEqual({x[5] for x in queries}, {'openalex', 'crossref'})
        self.assertTrue(all(group != 'EU / UK' for group, *_ in queries))
        self.assertTrue(all(focus.priority_region_match(label, group, place)
                            for group, place, label, *_ in queries))
        for area in focus.CRITICAL_TECHNOLOGIES:
            label = 'Critical technology: ' + area
            self.assertGreaterEqual(len({place for _, place, topic, *_ in queries if topic == label}), 8)

    def test_required_regions_not_confused_with_continent_tags(self):
        for label, good, bad in [
            ('CELAC: AI in Science', ('Americas','Brazil'), ('Asia & Pacific','India')),
            ('Union for the Mediterranean: Renewable energies', ('Africa','Morocco'), ('Africa','Kenya')),
            ('Africa: Green transition', ('Additional Africa','Senegal'), ('Americas','Chile')),
            ('ASEAN: Marine science', ('Asia & Pacific','Viet Nam'), ('Americas','Brazil')),
        ]:
            with self.subTest(label=label):
                self.assertTrue(focus.priority_region_match(label, *good))
                self.assertFalse(focus.priority_region_match(label, *bad))

    def test_actual_aboutness_and_topic_gate_passes_multiple_tracks(self):
        cases = [
            ('Critical technology: Quantum technologies', 'India',
             'Quantum computing research infrastructure in India',
             'This study examines Indian quantum computing research capacity.'),
            ('CELAC: Climate change, environmental sustainability and energy transition', 'Brazil',
             'Climate adaptation research and environmental sustainability in Brazil',
             'This study evaluates climate change policy in Brazil.'),
            ('Union for the Mediterranean: Renewable energies', 'Morocco',
             'Renewable energy research infrastructure in Morocco',
             'This study evaluates solar power research in Morocco.'),
            ('Africa: Public health', 'Kenya',
             'Public health research capacity in Kenya',
             'Researchers investigate public health research infrastructure in Kenya.'),
            ('ASEAN: Marine science', 'Viet Nam',
             'Marine science research infrastructure in Viet Nam',
             'The study examines marine science collaboration in Viet Nam.'),
        ]
        for label, place, title, abstract in cases:
            with self.subTest(label=label):
                result = focus.regional_matching(title, abstract, expected_region=place,
                                                expected_topic=label)
                self.assertIsNotNone(result)
                self.assertEqual(result['matched_locations'], [place])
        self.assertIsNone(focus.regional_matching(
            'Marine science research in Brazil',
            'The study investigates marine science capacity in Brazil.',
            expected_topic='ASEAN: Marine science', expected_region='Brazil'))

    def test_new_crossref_lead_receives_scope_and_priority_track(self):
        entry = {'type': 'report',
                 'title': ['Renewable energy research infrastructure in Morocco'],
                 'abstract': 'This study evaluates renewable energy research capacity in Morocco.',
                 'published': {'date-parts': [[2026, 4, 10]]},
                 'DOI': '10.2345/renewables-morocco-2026',
                 'publisher': 'Credible research institute'}
        label = 'Union for the Mediterranean: Renewable energies'
        got = focus.relevance_work('crossref', entry,
            allowed_topics={label: 'renewable energy research'},
            expected_topic=label, expected_region='Morocco')
        self.assertIsNotNone(got)
        candidate = got[2]
        self.assertEqual(candidate['focus_scope_id'], focus.FOCUS_SCOPE_ID)
        self.assertEqual(candidate['focus_priority_track'], 'Union for the Mediterranean')
        self.assertTrue(deep.valid_v4_lead(candidate))
        wrong = {**candidate, 'focus_region': 'India', 'focus_group': 'Asia & Pacific'}
        self.assertFalse(deep.valid_v4_lead(wrong))


class FocusPackageContinuityTests(unittest.TestCase):
    @staticmethod
    def new_lead():
        return {'candidate_id': 'REL-new-scope', 'title': 'Quantum technology in India',
                'date': '2026-11-17', 'source':'Science Research',
                'doi': '10.1234/quantum-india',
                'url': 'https://doi.org/10.1234/quantum-india',
                'focus_group': 'Asia & Pacific', 'focus_region': 'India',
                'focus_issue': 'Critical technology: Quantum technologies',
                'focus_scope_id': focus.FOCUS_SCOPE_ID,
                'focus_priority_track': 'critical_technology',
                'aboutness_basis': 'title',
                'geographic_evidence': 'Quantum technology research in India',
                'focus_score': 85}

    def test_legacy_manifest_and_imported_reviews_are_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / 'deep_scan'
            base.mkdir()
            (base / 'packages').mkdir()
            old_lead = {**self.new_lead(), 'candidate_id': 'REL-previous',
                        'focus_issue': 'Biodiversity',
                        'focus_scope_id': '', 'focus_priority_track': 'legacy'}
            legacy_manifest = {'format': deep.RESULT_FORMAT, 'package_id': 'rfds-old',
                               'generated_at': '2026-10-01T10:00:00+00:00',
                               'jobs': [old_lead]}
            old_path = base / 'pending_manifest.json'
            old_path.write_text(json.dumps(legacy_manifest, indent=2))
            before_old_bytes = old_path.read_bytes()
            verified = {'format': deep.RESULT_FORMAT, 'records': [
                {'candidate_id': 'REL-imported', 'decision':'keep',
                 'focus_issue':'Biodiversity', 'verified_package_id':'rfds-previous'}]}
            verified_path = base / 'verified_findings.json'
            verified_path.write_text(json.dumps(verified, indent=2))
            before_imported_bytes = verified_path.read_bytes()
            archive = root / 'archive.json'
            archive.write_text(json.dumps({'candidates':[old_lead, self.new_lead()]}))
            with patch.multiple(deep,
                ARCHIVE=archive, BASE=base, MANIFEST=old_path,
                PACKAGES=base / 'packages', VERIFIED=verified_path,
                REVIEW=base / 'review_archive.json',
                INBOX=base / 'inbox', PROCESSED=base / 'processed_inbox'):
                artifact = root / 'new_focus_deep_scan.zip'
                result = deep.prepare(batch_size=30, artifact=artifact)
                self.assertEqual(result['focus_scope_id'], focus.FOCUS_SCOPE_ID)
                self.assertEqual([x['candidate_id'] for x in result['jobs']],
                                 ['REL-new-scope'])
                self.assertEqual(deep.prepare(), result)  # stable reuse
                self.assertEqual(old_path.read_bytes(), before_old_bytes)
                self.assertEqual(verified_path.read_bytes(), before_imported_bytes)
                self.assertIn('rfds-old', deep.all_manifests())
                self.assertIn(result['package_id'], deep.all_manifests())
                with zipfile.ZipFile(artifact) as z:
                    self.assertIn('FOCUS RULES FOR NEWLY DISCOVERED CANDIDATES',
                                  z.read('INSTRUCTIONS.md').decode())
                    self.assertEqual(json.loads(z.read('MANIFEST.json'))['package_id'],
                                     result['package_id'])

    def test_legacy_package_still_eligible_for_review_after_scope_change(self):
        old = {**self.new_lead(), 'focus_issue': 'Biodiversity'}
        old.pop('focus_scope_id')
        old.pop('focus_priority_track')
        self.assertTrue(deep.valid_v4_lead(old))
        self.assertIn('HISTORICAL COMPATIBILITY', deep.INSTRUCTIONS)


if __name__ == '__main__':
    unittest.main()
