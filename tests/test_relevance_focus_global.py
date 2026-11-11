"""Global aboutness/futures scope and independent source-review integrity gates."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import relevance_focus as focus
import relevance_focus_deep_scan as review


class AboutnessTests(unittest.TestCase):
    def test_era_portal_austria_boilerplate_is_not_about_austria(self):
        summary = ('The Austrian online platform for the European Research Area (ERA) '
                   'is a promotion initiative aiming at providing comprehensive information '
                   'on the implementation of the ERA. The study examines European '
                   'research policy and innovation procurement governance.')
        result = focus.matching('EU research and innovation procurement policy', summary, backfill=True)
        self.assertIsNotNone(result)
        self.assertNotIn('Austria', result['countries'].split('; '))
        self.assertNotIn('Austria', [p for g, p, _, _ in focus.aboutness_locations(
            'EU research and innovation procurement policy', summary)])

    def test_austria_subject_is_retained_even_at_same_publisher(self):
        summary = ('This initiative strengthens research security in Austria. '
                   'It supports Austrian research institutions and university policy, '
                   'including research governance and international scientific cooperation.')
        result = focus.matching('Austrian initiative to strengthen research security', summary, backfill=True)
        self.assertIn('Austria', result['countries'].split('; '))

    def test_publisher_country_is_not_substantive_aboutness(self):
        result = focus.regional_matching(
            'European research security strategy and scientific cooperation',
            'Published by ERA Portal Austria. The study evaluates the European research area.',
            allowed_topics={'Research security / dual use':'research security'},
            expected_region='Austria', expected_topic='Research security / dual use')
        self.assertIsNone(result)

    def test_genuine_country_topic_not_eu_requirement(self):
        candidate = focus.regional_matching(
            'Biodiversity monitoring research in Kenya',
            'Research identifies new ecosystem observation and biodiversity data capacity in Kenya.',
            allowed_topics={'Biodiversity':'biodiversity'},
            expected_region='Kenya', expected_topic='Biodiversity')
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate['aboutness_basis'], 'title')
        self.assertIn('Could', candidate['future_ri_question'])
        self.assertNotIn('EU-relevant', candidate['match_reason'])
        chips = focus.regional_matching(
            'Microchip manufacturing and research infrastructure in Taiwan',
            'Taiwanese semiconductor researchers are evaluating new advanced packaging capabilities.',
            allowed_topics={'Semiconductors': 'semiconductors'},
            expected_region='Taiwan', expected_topic='Semiconductors')
        self.assertIsNotNone(chips)
        self.assertIn('semiconductor', chips['future_ri_question'].lower())

    def test_place_is_not_inherited_from_an_unrelated_topic_clause(self):
        unrelated = focus.regional_matching(
            'Biodiversity research and ecosystem monitoring in Brazil',
            'The research studies biodiversity observation in Brazil. '
            'Separate semiconductor manufacturing investment is reported in India.',
            allowed_topics={'Biodiversity':'biodiversity'},
            expected_region='India', expected_topic='Biodiversity')
        self.assertIsNone(unrelated)
        related = focus.regional_matching(
            'Biodiversity research and ecosystem monitoring in Brazil',
            'The research studies biodiversity observation in Brazil. '
            'Scientists study biodiversity monitoring policy in India.',
            allowed_topics={'Biodiversity':'biodiversity'},
            expected_region='India', expected_topic='Biodiversity')
        self.assertIsNotNone(related)

    def test_topic_specific_location_tags_exclude_unrelated_other_subjects(self):
        matched = focus.regional_matching(
            'Biodiversity research and ecosystem monitoring in Brazil',
            'The study examines biodiversity infrastructure in Brazil. '
            'Semiconductor research policy in India is a separate development.',
            allowed_topics={'Biodiversity': 'biodiversity'},
            expected_region='Brazil', expected_topic='Biodiversity')
        self.assertIsNotNone(matched)
        self.assertEqual(matched['countries'], 'Brazil')
        self.assertEqual(matched['regions'], 'Americas')

    def test_foreign_publishers_not_excluded_foreign_study_keeps_subject(self):
        for source_country, title in [
            ('Austria', 'Austrian researchers study biodiversity monitoring in Kenya'),
            ('Sweden', 'Swedish scientists report on biodiversity data in Kenya'),
            ('Japan', 'Japanese research institute evaluates biodiversity in Kenya')]:
            with self.subTest(source_country=source_country):
                got=focus.regional_matching(title,
                    'Researchers analyse biodiversity research capacity in Kenya.',
                    allowed_topics={'Biodiversity':'biodiversity'},
                    expected_region='Kenya',expected_topic='Biodiversity')
                self.assertIsNotNone(got)
                self.assertIn('Kenya',got['countries'])
                self.assertNotIn(source_country,got['countries'])

    def test_trailing_foreign_institute_attribution_is_not_a_country_tag(self):
        got=focus.aboutness_locations(
            'Biodiversity monitoring research in Kenya by an Austrian university')
        self.assertEqual({x[1] for x in got},{'Kenya'})
        genuine=focus.aboutness_locations(
            'Austrian universities invest in biotechnology infrastructure in Austria')
        self.assertIn('Austria',{x[1] for x in genuine})

    def test_relevance_work_accepts_austrian_publisher_about_kenya(self):
        work={'type':'report','title':['Biodiversity research infrastructure in Kenya'],
              'abstract':'<p>Researchers evaluate Kenyan biodiversity monitoring infrastructure.</p>',
              'published':{'date-parts':[[2026,1,12]]},
              'DOI':'10.1234/kenya-ecology','publisher':'Austrian Academy of Sciences'}
        got=focus.relevance_work('crossref',work,
               allowed_topics={'Biodiversity':'biodiversity'},
               expected_region='Kenya',expected_topic='Biodiversity')
        self.assertIsNotNone(got)
        self.assertEqual(got[2]['source'],'Austrian Academy of Sciences')
        self.assertEqual(got[2]['focus_region'],'Kenya')
        self.assertEqual(got[2]['focus_group'],'Africa')

    def test_global_backfill_removes_eu_only_and_prioritizes_external_setting(self):
        eu_only=focus.matching('Austria research security programme',
             'Austrian institutions develop research policy.',backfill=True)
        self.assertIsNone(focus.external_focus_match(eu_only))
        both=focus.matching('EU India science diplomacy and research policy cooperation',
             'Policy cooperation strengthens research capacity in India.',backfill=True)
        outside=focus.external_focus_match(both)
        self.assertIsNotNone(outside)
        self.assertEqual(outside['countries'],'India')
        self.assertEqual(outside['regions'],'Asia & Pacific')

    def test_online_query_targets_external_places_only(self):
        plan=list(focus.focused_search_plan(11,focus={'Biodiversity':'biodiversity',
                                                     'Semiconductors':'semiconductors'}))
        self.assertTrue(plan)
        self.assertTrue(all(group!='EU / UK' for group,*_ in plan))
        self.assertFalse(any(place in {'Austria','United Kingdom','European Union'}
                             for _,place,*_ in plan))

    def test_retired_eu_radar_admission_cannot_run_accidentally(self):
        with self.assertRaisesRegex(RuntimeError, 'NOT pass through ordinary EU Radar'):
            focus.scan(Path('/tmp/any-global-batch.json'))

    def test_biodiversity_topic_activated_only_from_main_radar(self):
        found = focus.focus_areas(raw={'strand_a': [{'title':
            'Biodiversity observation research and innovation science policy',
            'summary':'Conservation science governance for future ecosystem monitoring.'}]})
        self.assertIn('Biodiversity', found)
        self.assertNotIn('Semiconductors', found)

    def test_old_publisher_based_archive_never_gets_country_tag(self):
        from unittest.mock import patch
        legacy = {'candidates': [{'candidate_id':'REL-older', 'title':
            'Open research governance in Europe', 'source':'ERA Portal Austria',
            'focus_region':'Austria', 'focus_group':'EU / UK', 'focus_issue':'Science policy',
            'date':'2026-01-15', 'url':'https://doi.org/10.1234/old',
            'doi':'10.1234/old'}]}
        mock = {'radar_active.json':{},'radar.json':{},'reader_text.json':{},
                'deep_scan_work_state.json':{},'admission_state.json':{},
                'Relevance Stuff/regional_discoveries.json':legacy}
        with patch.object(focus, 'load', side_effect=lambda name, default: mock.get(name, default)):
            report = focus.compile_records()
        self.assertEqual(report['regional_leads'], [])
        self.assertEqual(report['statistics']['eu_uk_legacy_leads_excluded_from_global_view'], 1)


class DeepScanTests(unittest.TestCase):
    @staticmethod
    def lead():
        return {'candidate_id':'REL-test', 'title':'Biodiversity monitoring research in Kenya',
                'date':'2026-08-12', 'source':'International Science Review',
                'doi':'10.1234/kenya', 'url':'https://doi.org/10.1234/kenya',
                'focus_region':'Kenya', 'focus_group':'Africa',
                'focus_issue':'Biodiversity', 'focus_score':90,
                'aboutness_basis':'title',
                'geographic_evidence':'Biodiversity monitoring research in Kenya'}

    @staticmethod
    def result(lead):
        return {'candidate_id':lead['candidate_id'], 'decision':'keep',
                'source_verification': {'identity_verified':True,
                    'primary_url':'https://doi.org/10.1234/kenya',
                    'source_type':'scholarly_article',
                    'source_integrity':'independent_credible',
                    'propaganda_or_influence_risk':'none_identified',
                    'basis':'Checked publisher full text and article metadata, methods, and substantive country findings.',
                    'independent_corrob_urls':[]},
                'aboutness': {'place':'Kenya','is_substantive':True,
                    'publisher_country_only':False,
                    'basis':'The analysis measures biodiversity data production in Kenya.',
                    'verified_excerpt':'The article studies Kenyan ecosystem observation capacity.'},
                'topic': {'label':'Biodiversity', 'is_relevant':True,
                    'basis':'The primary article evaluates scientific biodiversity monitoring capacity.'},
                'futures': {'classification':'mixed',
                    'mechanism':'Biodiversity monitoring research infrastructure in Kenya.',
                    'why_could_matter':'This could contribute ecological data for future conservation science.',
                    'uncertainty':'Research outcomes and funding are not yet established.',
                    'research_question':'Could Kenya become a regional biodiversity data research hub?'}}

    def test_global_review_does_not_queue_eu_uk_study_region(self):
        lead = self.lead()
        eu_only = {**lead, 'focus_region': 'Austria', 'focus_group': 'EU / UK'}
        self.assertFalse(review.valid_v4_lead(eu_only))
        foreign_publisher = {**lead, 'source': 'Austrian Academy of Sciences'}
        self.assertTrue(review.valid_v4_lead(foreign_publisher))

    def test_keep_requires_no_eu_but_strict_source_integrity(self):
        l=self.lead()
        self.assertEqual(review.validate_result(self.result(l),l)['focus_region'], 'Kenya')
        for change in ({'source_integrity':'unreliable'},
                       {'propaganda_or_influence_risk':'suspected'},
                       {'propaganda_or_influence_risk':'confirmed'},
                       {'identity_verified':False}):
            entry=self.result(l)
            entry['source_verification'].update(change)
            with self.assertRaises(ValueError):
                review.validate_result(entry,l)
        entry=self.result(l)
        entry['aboutness']['publisher_country_only']=True
        with self.assertRaises(ValueError):
            review.validate_result(entry,l)
        entry=self.result(l)
        entry['aboutness']['place']='Austria'
        with self.assertRaises(ValueError):
            review.validate_result(entry,l)

    def test_package_and_transactional_review_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            base=root/'deep_scan'
            archive=root/'regional_discoveries.json'
            archive.write_text(json.dumps({'candidates':[self.lead()]}))
            (base/'inbox').mkdir(parents=True)
            with patch.multiple(review, ARCHIVE=archive,
                                BASE=base, MANIFEST=base/'pending_manifest.json',
                                VERIFIED=base/'verified_findings.json',
                                REVIEW=base/'review_archive.json',
                                INBOX=base/'inbox', PROCESSED=base/'processed_inbox'):
                manifest=review.prepare(artifact=root/'review.zip')
                self.assertEqual(len(manifest['jobs']),1)
                self.assertEqual(review.prepare()['package_id'], manifest['package_id'])
                file=base/'inbox'/'review.json'
                good=self.result(self.lead())
                file.write_text(json.dumps({'format':review.RESULT_FORMAT,
                    'package_id':manifest['package_id'], 'results':[good]}))
                self.assertEqual(review.import_inbox(),1)
                self.assertEqual(review.read(review.VERIFIED,{})['records'][0]['focus_region'],'Kenya')
                self.assertEqual(review.import_inbox(),0)
                self.assertEqual(review.prepare()['jobs'],[])

    def test_additional_packages_skip_original_and_each_other_and_import_independently(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / 'deep_scan'
            archive = root / 'regional_discoveries.json'
            leads = []
            for index in range(5):
                lead = {**self.lead(), 'candidate_id': f'REL-{index}',
                        'doi': f'10.1234/kenya{index}',
                        'url': f'https://doi.org/10.1234/kenya{index}',
                        'focus_score': 90 - index}
                leads.append(lead)
            archive.write_text(json.dumps({'candidates': leads}))
            (base / 'inbox').mkdir(parents=True)
            with patch.multiple(review, ARCHIVE=archive, BASE=base,
                                PACKAGES=base/'packages', MANIFEST=base/'pending_manifest.json',
                                VERIFIED=base/'verified_findings.json',
                                REVIEW=base/'review_archive.json', INBOX=base/'inbox',
                                PROCESSED=base/'processed_inbox'):
                original = review.prepare(batch_size=2)
                first = review.prepare(batch_size=2, additional=True, artifact=root/'first.zip')
                second = review.prepare(batch_size=2, additional=True, artifact=root/'second.zip')
                self.assertEqual([len(x['jobs']) for x in (original, first, second)], [2, 2, 1])
                sets = [{x['candidate_id'] for x in m['jobs']} for m in (original, first, second)]
                self.assertEqual(len(set.union(*sets)), 5)
                self.assertEqual(sum(map(len, sets)), 5)
                self.assertEqual(review.read(review.MANIFEST,{})['package_id'],original['package_id'])
                self.assertEqual(len(list((base/'packages').glob('*.json'))),2)
                empty = review.prepare(additional=True)
                self.assertEqual(empty['jobs'],[])
                self.assertEqual(len(list((base/'packages').glob('*.json'))),2)
                for name, manifest in [('first',first), ('original',original), ('second',second)]:
                    results = [{**self.result(lead), 'candidate_id':lead['candidate_id']}
                               for lead in manifest['jobs']]
                    (base/'inbox'/f'{name}.json').write_text(json.dumps({
                        'format': review.RESULT_FORMAT, 'package_id': manifest['package_id'],
                        'results': results}))
                self.assertEqual(review.import_inbox(),5)
                self.assertEqual(len(review.read(review.VERIFIED,{})['records']),5)
                self.assertEqual(len(list((base/'processed_inbox').glob('*.json'))),3)
                self.assertEqual(review.prepare()['jobs'],[])

    def test_invalid_review_file_never_changes_persisted_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);inbox=root/'inbox';inbox.mkdir()
            lead=self.lead()
            bad=self.result(lead)
            bad['source_verification']['propaganda_or_influence_risk']='confirmed'
            manifest={'package_id':'rfds-test', 'jobs':[lead]}
            (root/'manifest.json').write_text(json.dumps(manifest))
            (inbox/'bad.json').write_text(json.dumps({
                'format':review.RESULT_FORMAT, 'package_id':'rfds-test', 'results':[bad]}))
            with patch.multiple(review, MANIFEST=root/'manifest.json',
                                VERIFIED=root/'verified.json', REVIEW=root/'reviews.json',
                                INBOX=inbox, PROCESSED=root/'processed'):
                with self.assertRaises(ValueError):
                    review.import_inbox()
                self.assertFalse((root/'verified.json').exists())
                self.assertTrue((inbox/'bad.json').exists())


if __name__=='__main__':
    unittest.main()
