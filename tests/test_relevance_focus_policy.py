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
        for group, place, label, _lens, query, *_ in queries:
            self.assertTrue(focus.priority_region_match(label, group, place))
            if label.startswith('Critical technology: '):
                self.assertEqual((group, place), ('Global', 'Global / unspecified'))
                self.assertNotIn('Global / unspecified', query)
            else:
                self.assertNotEqual(group, 'Global')
        for area in focus.CRITICAL_TECHNOLOGIES:
            label = 'Critical technology: ' + area
            self.assertTrue(any(topic == label for _, _, topic, *_ in queries))

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


    def test_critical_technologies_need_no_country_or_eu_mentions(self):
        topic = 'Critical technology: Quantum technologies'
        title = 'Quantum computing error correction architecture for robust qubits'
        abstract = 'Researchers demonstrate a quantum computing correction method for qubit systems.'
        m = focus.regional_matching(title, abstract, expected_topic=topic)
        self.assertIsNotNone(m)
        self.assertEqual(m['matched_locations'], ['Global / unspecified'])
        self.assertIsNone(focus.regional_matching(title, abstract,
            expected_topic='ASEAN: Marine science'))
        entry = {'type':'report','title':[title],'abstract':abstract,
            'published':{'date-parts':[[2026,11,4]]},
            'DOI':'10.2345/quantum-error-correction-2026',
            'publisher':'University research centre'}
        rec = focus.relevance_work('crossref',entry, expected_topic=topic)
        self.assertIsNotNone(rec)
        self.assertEqual(rec[2]['focus_region'],'Global / unspecified')
        self.assertTrue(deep.valid_v4_lead(rec[2]))

    def test_eu_primary_study_qualifies_for_global_technology(self):
        m=focus.regional_matching('Semiconductor chip fabrication research in Germany',
            'German research laboratories test semiconductor manufacturing.',
            expected_topic='Critical technology: Advanced semiconductors')
        self.assertIsNotNone(m)
        self.assertEqual(m['primary_group'], 'EU / UK')



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

    def test_real_november_batch_false_positives_and_policy_studies(self):
        # These titles occurred in the November 17 candidate batch, not in
        # hypothetical synthetic research or in old verified material.
        for label, title in [
            ('Africa: Innovation and technology',
             'Troop Morale and Organizational Innovation Capacity Within the Armed Forces of the Democratic Republic of the Congo'),
            ('ASEAN: Green technologies',
             'Green Technology Innovation and Firm-Level Technical Efficiency: A Two-Stage Analysis in the Philippines'),
            ('Critical technology: Artificial intelligence',
             'Measuring the Impact of Digital Technology on Consumer Behavior Using Machine Learning: A Case Study of Saudi Arabia Research-in-progress'),
        ]:
            with self.subTest(title=title):
                self.assertFalse(focus.substantive_policy_technology(label, title))
        self.assertTrue(focus.substantive_policy_technology(
            'Africa: Innovation and technology',
            'Research commercialization and technology transfer networks in Kenya'))
        self.assertTrue(focus.substantive_policy_technology(
            'Critical technology: Artificial intelligence',
            'Machine learning for drought forecasting in India: model development and validation'))
        self.assertTrue(focus.substantive_policy_technology(
            'Critical technology: Advanced materials, manufacturing and recycling technologies',
            'Policy governance for advanced manufacturing in China'))

    def test_new_discovery_filters_low_substance_but_not_real_eu_relevance(self):
        f = focus.discovery_research_signal
        for label, title in [
            ('Africa: Capacities for science and higher education',
             'Students Perceptions and Expectations of Higher Education in Burundi'),
            ('Africa: Capacities for science and higher education',
             'Promoting Inclusive Education for Students with Disabilities in Higher Education'),
            ('CELAC: Climate change, environmental sustainability and energy transition',
             'Voices of the Caribbean: Media Discourses on Climate Change in Jamaica News Coverage'),
            ('CELAC: Health',
             'From the Editor-in-Chief: Biomedical Research and Biopharmaceutical Advances in Cuba'),
            ('Critical technology: Advanced materials, manufacturing and recycling technologies',
             'Additive Manufacturing Awareness for Engineering Education in France'),
        ]:
            with self.subTest(title=title):
                self.assertFalse(f(label, title)[0])
        for label, title in [
            ('Critical technology: Quantum technologies',
             'Quantum error correction architecture demonstrated for qubits'),
            ('Critical technology: Advanced semiconductors',
             'Semiconductor investment and manufacturing supply chains in Mexico'),
            ('Africa: Capacities for science and higher education',
             'Research infrastructure and research capacity in Ethiopian universities'),
            ('CELAC: Health',
             'Brazil health industrial policy and biomedical technology transfer'),
        ]:
            with self.subTest(title=title):
                self.assertTrue(f(label, title)[0])
        self.assertGreater(f('Critical technology: Advanced semiconductors',
            'Semiconductor fabrication prototype for power electronics')[1],
            f('Critical technology: Advanced semiconductors',
            'General review of semiconductor industry history')[1])

    def test_regional_social_exposure_weak_matches_not_selected(self):
        f = focus.discovery_research_signal
        cases = [
            ('Africa: Public health',
             'Public Health Risks Associated with Almajiri Migration: The Role of Social Workers in Northern Nigeria'),
            ('CELAC: Climate change, environmental sustainability and energy transition',
             'How climate change is shaping young people’s health: a participatory, youth co-led study from Bangladesh, Guatemala and Nigeria'),
            ('Africa: Green transition',
             'Crop vulnerability and climate adaptation to moisture stress in the semi-arid zones of Senegal'),
        ]
        for label, title in cases:
            with self.subTest(title=title):
                self.assertFalse(f(label, title, 'Generic research findings reported.')[0])

    def test_legitimate_ri_and_reviews_outlooks_survive(self):
        f = focus.discovery_research_signal
        cases = [
            ('Africa: Green transition',
             'Crop vulnerability forecasting with a new remote sensing model in Senegal'),
            ('Africa: Green transition',
             'Modelling climate adaptation infrastructure investments in Senegal: future scenarios'),
            ('Africa: Public health',
             'Implementation of a disease surveillance platform for mobile populations in Nigeria'),
            ('CELAC: Health',
             'Participatory design of a new public health surveillance system in Guatemala'),
            ('Critical technology: Advanced semiconductors',
             'Development of Photolithography for Semiconductor Manufacturing – A Review'),
            ('Critical technology: Advanced connectivity, navigation and digital technologies',
             'From 5G to 6G: A Survey on Security, Privacy, and Standardization Pathways'),
            ('Critical technology: Robotics and autonomous systems',
             'Outlook for robotics-related clinical trials: current status and future directions'),
            ('Africa: Green transition',
             'A foresight outlook for green hydrogen investment in Namibia'),
        ]
        for label, title in cases:
            with self.subTest(title=title):
                self.assertTrue(f(label, title)[0])
        self.assertGreaterEqual(f('Critical technology: Advanced semiconductors',
            'A review of future semiconductor manufacturing pathways')[1], 0)

    def test_candidate_title_and_publisher_identity_does_not_change_doi_archive(self):
        title = 'Higher education-industry research partnership: engaging with South Africa forms'
        first = {'title':title, 'source':'Human Science Research Council SA',
                 'doi':'10.14749/32866847'}
        second = {**first, 'doi':'10.14749/32866850',
                  'title':title.upper() + '!!'}
        self.assertNotEqual(focus.doi_identity(first), focus.doi_identity(second))
        self.assertEqual(focus.publication_title_venue_identity(first),
                         focus.publication_title_venue_identity(second))
        self.assertNotEqual(focus.publication_title_venue_identity(first),
                            focus.publication_title_venue_identity({**second, 'source':'Another journal'}))

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

    def test_current_focus_manual_60_excludes_legacy_reserved_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); base=root/'deep_scan'; packages=base/'packages'
            packages.mkdir(parents=True)
            new = []
            for i in range(95):
                row = {**self.new_lead(), 'candidate_id':f'REL-current-{i:03}',
                       'title':f'Quantum technology research infrastructure in India, programme {i}',
                       'doi':f'10.1234/quantum-{i}', 'url':f'https://doi.org/10.1234/quantum-{i}',
                       'focus_quality_revision':'precision-aboutness-technology-v2'}
                new.append(row)
            new[94]['title'] = new[93]['title']  # different DOI, same title and venue
            old = [{**self.new_lead(), 'candidate_id':f'REL-legacy-{i}',
                    'focus_issue':'Biodiversity', 'focus_scope_id':'',
                    'focus_priority_track':'legacy'} for i in range(75)]
            archive=root/'archive.json'
            archive.write_text(json.dumps({'candidates':old+new}))
            original={'format':deep.RESULT_FORMAT, 'package_id':'rfds-already-reserved',
                      'generated_at':'2026-11-17T13:00:00+00:00', 'jobs':new[:30]}
            (packages/'rfds-already-reserved.json').write_text(json.dumps(original))
            original_bytes=(packages/'rfds-already-reserved.json').read_bytes()
            verified=base/'verified_findings.json'
            verified.write_text(json.dumps({'records':[{'candidate_id':'REL-current-030'}]}))
            first_bytes=verified.read_bytes()
            with patch.multiple(deep, ARCHIVE=archive, MANIFEST=base/'pending_manifest.json',
                PACKAGES=packages, VERIFIED=verified, REVIEW=base/'review_archive.json',
                INBOX=base/'inbox', PROCESSED=base/'processed_inbox'):
                manifest=deep.prepare(batch_size=60, additional=True, artifact=root/'current.zip')
                self.assertEqual(len(manifest['jobs']),60)
                self.assertEqual(manifest['focus_scope_id'],focus.FOCUS_SCOPE_ID)
                self.assertTrue(all(row['candidate_id'].startswith('REL-current-')
                                    for row in manifest['jobs']))
                self.assertFalse({row['candidate_id'] for row in manifest['jobs']}
                                 & {row['candidate_id'] for row in new[:31]})
                self.assertEqual(len({focus.publication_title_venue_identity(row)
                                      for row in manifest['jobs']}),60)
                next_batch=deep.prepare(batch_size=60,additional=True)
                self.assertEqual(len(next_batch['jobs']),3)
                self.assertFalse({x['candidate_id'] for x in next_batch['jobs']}
                                 & {x['candidate_id'] for x in manifest['jobs']})
                self.assertEqual((packages/'rfds-already-reserved.json').read_bytes(),original_bytes)
                self.assertEqual(verified.read_bytes(),first_bytes)
                with zipfile.ZipFile(root/'current.zip') as z:
                    self.assertEqual(len(json.loads(z.read('MANIFEST.json'))['jobs']),60)
                    self.assertIn('verified_doi',z.read('INSTRUCTIONS.md').decode())

    def test_new_revision_keep_requires_matching_publisher_title_and_doi(self):
        lead = self.new_lead()
        result = {'candidate_id':lead['candidate_id'], 'decision':'keep',
            'source_verification':{'identity_verified':True,
                'primary_url':'https://example.com/primary-article',
                'source_type':'scholarly_article', 'source_integrity':'independent_credible',
                'propaganda_or_influence_risk':'none_identified',
                'basis':'Reviewed primary publisher landing page against full text, authors, journal and article identifier.',
                'independent_corrob_urls':[]},
            'aboutness':{'place':'India', 'is_substantive':True,
                'publisher_country_only':False,'basis':'The study examines Indian quantum research capacity.',
                'verified_excerpt':'Research infrastructure and quantum technology activity are studied in India.'},
            'topic':{'label':lead['focus_issue'], 'is_relevant':True,
                'basis':'The work specifically studies quantum technology capability.'},
            'futures':{'classification':'observed',
                'mechanism':'Quantum technology research infrastructure and enabling technical skills.',
                'why_could_matter':'The infrastructure might enable more domestic quantum science research.',
                'uncertainty':'Long-term research outcomes have not been independently established.',
                'research_question':'Could new infrastructure improve quantum research capacity in India?'}}
        with self.assertRaisesRegex(ValueError,'verified_doi and verified_title'):
            deep.validate_result(result,lead)
        result['source_verification'].update(verified_doi=lead['doi'], verified_title=lead['title'])
        result['eu_perspective'] = {
            'relevance': 'plausible',
            'implications': 'EU quantum research capability may be affected by new scientific methods.',
            'evidence_limits': 'The publication provides no direct evidence of a resulting EU impact.'}
        self.assertEqual(deep.validate_result(result,lead)['decision'],'keep')
        result['eu_perspective']['relevance'] = 'uncertain'
        with self.assertRaisesRegex(ValueError, 'uncertain belongs in REVIEW'):
            deep.validate_result(result, lead)
        result['eu_perspective']['relevance'] = 'plausible'
        result['source_verification']['verified_doi']=lead['doi']+'/pdf'
        with self.assertRaisesRegex(ValueError,'DOI differs'):
            deep.validate_result(result,lead)
        result['source_verification']['verified_doi']=lead['doi']
        result['source_verification']['verified_title']='Entirely different article'
        with self.assertRaisesRegex(ValueError,'title differs'):
            deep.validate_result(result,lead)
        # Existing issued v2 manifest schema remains importable.
        result['source_verification'].pop('verified_title')
        result['source_verification'].pop('verified_doi')
        self.assertEqual(deep.validate_result(result, {**lead,
            'focus_quality_revision':'precision-aboutness-technology-v2'})['decision'],'keep')

    def test_automatic_30_does_not_reuse_manual_60_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); base=root/'deep_scan'; (base/'packages').mkdir(parents=True)
            archive=root/'archive.json'
            rows=[{**self.new_lead(), 'candidate_id':f'REL-auto-{i}',
                    'title':f'Quantum research infrastructure in India programme {i}',
                    'doi':f'10.1234/quantum-auto-{i}',
                    'url':f'https://doi.org/10.1234/quantum-auto-{i}'}
                  for i in range(5)]
            archive.write_text(json.dumps({'candidates':rows}))
            with patch.multiple(deep, ARCHIVE=archive, MANIFEST=base/'pending_manifest.json',
                PACKAGES=base/'packages', VERIFIED=base/'verified_findings.json',
                REVIEW=base/'review_archive.json',INBOX=base/'inbox',
                PROCESSED=base/'processed_inbox'):
                manual=deep.prepare(batch_size=3, additional=True)
                auto=deep.prepare(batch_size=30)
                self.assertEqual(len(manual['jobs']),3)
                self.assertEqual(len(auto['jobs']),2)
                self.assertEqual(auto['package_purpose'],'automatic_scan')
                self.assertNotEqual(auto['package_id'],manual['package_id'])
                self.assertFalse({r['candidate_id'] for r in manual['jobs']}
                                 & {r['candidate_id'] for r in auto['jobs']})
                self.assertEqual(deep.prepare(batch_size=30)['package_id'],auto['package_id'])


if __name__ == '__main__':
    unittest.main()
