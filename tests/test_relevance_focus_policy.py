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


class PrecisionRegressionTests(unittest.TestCase):
    """Specific false positives from the November 17 review package."""

    def test_niger_delta_and_niger_state_are_not_the_country_niger(self):
        cases = [
            ('Struggles for a Just Energy Transition in Nigeria’s Niger Delta: Just for Whom?',
             'This study evaluates the energy transition in Nigeria’s Niger Delta.',
             'Africa: Green transition'),
            ('Feasibility Analysis of Hybrid Renewable Energy Systems with Battery Storage '
             'for Rural Electrification in Samunaka, Niger State: A Newton-Raphson Approach',
             'Rural electrification systems in Niger State, Nigeria.',
             'Critical technology: Energy technologies'),
        ]
        for title, abstract, label in cases:
            with self.subTest(title=title):
                locations = focus.aboutness_locations(title, abstract, policy=True)
                self.assertNotIn('Niger', [row[1] for row in locations])
                self.assertIsNone(focus.regional_matching(
                    title, abstract, expected_topic=label, expected_region='Niger'))
        # The African regional scope is retained, with the correct subject country.
        locations = focus.aboutness_locations(cases[0][0], cases[0][1], policy=True)
        self.assertIn('Nigeria', [row[1] for row in locations])
        # Actual country Niger remains discoverable.
        positive = focus.regional_matching('Green transition research in Niger',
            'The study examines renewable-energy research capacity in the Republic of Niger.',
            expected_topic='Africa: Green transition', expected_region='Niger')
        self.assertIsNotNone(positive)

    def test_benin_city_nigeria_is_not_the_country_benin(self):
        title = ('Lipid Profiles and Metal Levels Assessment in Chicken Meat Sold '
                 'in Benin, Nigeria: Implications for Public Health')
        abstract = 'Public health research on food safety in Benin City, Edo State, Nigeria.'
        locations = focus.aboutness_locations(title, abstract, policy=True)
        self.assertNotIn('Benin', [row[1] for row in locations])
        self.assertIn('Nigeria', [row[1] for row in locations])
        self.assertIsNone(focus.regional_matching(
            title, abstract, expected_topic='Africa: Public health', expected_region='Benin'))
        self.assertIsNotNone(focus.regional_matching(
            'Public health research infrastructure in the Republic of Benin',
            'This research studies public health systems across Benin.',
            expected_topic='Africa: Public health', expected_region='Benin'))

    def test_attitude_surveys_and_green_hr_do_not_qualify_as_technologies(self):
        self.assertFalse(focus.substantive_policy_technology(
            'Critical technology: Artificial intelligence',
            'Student perceptions of AI ethics and awareness in the Philippines',
            'Students reported their views on artificial intelligence.'))
        self.assertFalse(focus.substantive_policy_technology(
            'ASEAN: Green technologies',
            'Green Human Resource Management and Green Innovation in Timor-Leste',
            'The study examines corporate green innovation and staff attitudes.'))
        self.assertTrue(focus.substantive_policy_technology(
            'Critical technology: Artificial intelligence',
            'Research on neural network algorithms for medical imaging in the Philippines'))
        self.assertTrue(focus.substantive_policy_technology(
            'ASEAN: Green technologies',
            'Green Hydrogen Technology Deployment in Timor-Leste',
            'Researchers test renewable energy technology in Timor-Leste.'))

    def test_no_cross_region_secondary_priority_tags(self):
        match = focus.regional_matching(
            'Public health research infrastructure in Nigeria',
            'Researchers examine public health research in Nigeria.',
            expected_topic='Africa: Public health', expected_region='Nigeria')
        self.assertIsNotNone(match)
        self.assertIn('Africa: Public health', match['matched_topics'])
        self.assertNotIn('CELAC: Health', match['matched_topics'])
        self.assertNotIn('Union for the Mediterranean: Health', match['matched_topics'])
        self.assertNotIn('ASEAN: Green technologies', match['matched_topics'])
        # Critical technologies are global, not region-locked.
        match = focus.regional_matching(
            'Quantum computing research infrastructure in Nigeria',
            'Researchers evaluate quantum computing systems in Nigeria.',
            expected_topic='Critical technology: Quantum technologies', expected_region='Nigeria')
        self.assertIsNotNone(match)

    def test_deep_scan_requires_current_precision_instructions(self):
        instructions = deep.INSTRUCTIONS
        for phrase in ['Niger Delta', 'Niger State', 'Benin City',
                       'human-resource management', 'canonical DOI',
                       'Secondary priority tags']:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), instructions.lower())
        old = {'candidate_id': 'REL-old', 'title':'Historical biodiversity research in Kenya',
               'focus_issue':'Biodiversity', 'focus_region':'Kenya',
               'focus_group':'Africa', 'aboutness_basis':'title',
               'geographic_evidence':'Biodiversity research in Kenya',
               'url':'https://doi.org/10.1234/historical'}
        self.assertTrue(deep.valid_v4_lead(old))
        self.assertTrue(deep.unambiguous_new_focus_geography(old))

    def test_deep_scan_blocks_wrong_country_keep_without_touching_existing_results(self):
        for place, title in [
            ('Niger', 'Struggles for a Just Energy Transition in Nigeria’s Niger Delta: Just for Whom?'),
            ('Niger', 'Hybrid Renewable Energy Systems in Samunaka, Niger State'),
            ('Benin', 'Public Health of Chicken Meat Sold in Benin, Nigeria'),
        ]:
            lead = {'candidate_id':'REL-country-error', 'title':title,
                    'focus_scope_id':focus.FOCUS_SCOPE_ID,
                    'focus_region':place, 'focus_issue':'Africa: Public health',
                    'focus_priority_track':'Africa', 'geographic_evidence':title,
                    'url':'https://doi.org/10.1234/review-case'}
            with self.subTest(place=place, title=title):
                self.assertFalse(deep.unambiguous_new_focus_geography(lead))
                # A source reviewer can still submit REVIEW or DROP for old packages.
                result = deep.validate_result({'candidate_id':lead['candidate_id'],
                    'decision':'review', 'review_reason':
                    'The manifest country is incorrect and needs further verification.'}, lead)
                self.assertEqual(result['decision'], 'review')
        real = {'focus_scope_id':focus.FOCUS_SCOPE_ID, 'focus_region':'Niger',
                'title':'Research infrastructure in the Republic of Niger'}
        self.assertTrue(deep.unambiguous_new_focus_geography(real))

    def test_new_revision_separates_previous_unfinished_policy_package(self):
        lead = FocusPackageContinuityTests.new_lead()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); base=root/'deep_scan'
            (base/'packages').mkdir(parents=True)
            old = {**lead, 'candidate_id':'REL-old-policy',
                   'focus_quality_revision':None}
            oldmanifest = {'format':deep.RESULT_FORMAT, 'package_id':'rfds-earlier-policy',
                'generated_at':'2026-11-17T09:00:00+00:00',
                'focus_scope_id':focus.FOCUS_SCOPE_ID, 'jobs':[old]}
            old_file=base/'packages'/'rfds-earlier-policy.json'
            old_file.write_text(json.dumps(oldmanifest))
            earlier_bytes=old_file.read_bytes()
            archive=root/'archive.json'; archive.write_text(json.dumps({'candidates':[old, lead]}))
            verified=base/'verified_findings.json'; verified.write_text(json.dumps({'records':[
                {'candidate_id':'REL-reviewed-import', 'decision':'keep'}]}))
            verified_bytes=verified.read_bytes()
            with patch.multiple(deep, ARCHIVE=archive, BASE=base,
                MANIFEST=base/'pending_manifest.json', PACKAGES=base/'packages',
                VERIFIED=verified, REVIEW=base/'review_archive.json',
                INBOX=base/'inbox', PROCESSED=base/'processed_inbox'):
                manifest=deep.prepare(artifact=root/'new.zip')
                self.assertEqual(manifest['focus_quality_revision'], focus.FOCUS_QUALITY_REVISION)
                self.assertEqual([x['candidate_id'] for x in manifest['jobs']], ['REL-new-scope'])
                self.assertEqual(deep.prepare()['package_id'], manifest['package_id'])
                self.assertEqual(earlier_bytes, old_file.read_bytes())
                self.assertEqual(verified_bytes, verified.read_bytes())
                self.assertIn('rfds-earlier-policy', deep.all_manifests())


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
                'focus_quality_revision': focus.FOCUS_QUALITY_REVISION,
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
