"""Deterministic contract tests for the standalone relevance subset and discovery route."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from relevance_focus import GEOGRAPHY, ISSUES, matching, compile_records, COUNTRY_POLICY_ISSUE


class RelevanceFocusTests(unittest.TestCase):
    def test_enlargement_names_complete(self):
        self.assertEqual(set(GEOGRAPHY['Europe — enlargement']), {
            'Albania','Bosnia and Herzegovina','Georgia','Kosovo','Moldova',
            'Montenegro','North Macedonia','Serbia','Ukraine','Türkiye','Western Balkans'})

    def test_science_diplomacy_matches(self):
        r=matching('Science diplomacy and the EU–India research partnership',
                   'The study describes international scientific collaboration with India and European universities.')
        self.assertIsNotNone(r)
        self.assertIn('India',r['countries'])
        self.assertIn('Science diplomacy',r['issues'])

    def test_deep_ocean_without_nation_matches(self):
        r=matching('Future of high seas biodiversity beyond national jurisdiction',
                   'Research and innovation scenarios for science governance of the deep sea.')
        self.assertIsNotNone(r)
        self.assertIn('Ocean / deep sea beyond national jurisdiction',r['issues'])

    def test_generic_eu_technology_is_excluded(self):
        self.assertIsNone(matching('EU AI capabilities', 'Analysis of European technology trends.'))

    def test_university_word_alone_does_not_qualify(self):
        self.assertIsNone(matching('University research in Canada',
                                   'A university reports changes in laboratory equipment.'))

    def test_who_pronoun_is_not_world_health_organisation(self):
        r=matching('Who sets up a bridge for China research partnerships?',
                   'Technology policy collaboration between China and Europe.')
        self.assertIsNotNone(r)
        self.assertNotIn('Science-based international organisations',r['issues'])

    def test_actual_who_organisation_matched(self):
        r=matching('WHO governance during US withdrawal',
                   'Future science diplomacy and research policy decisions at the World Health Organization.')
        self.assertIsNotNone(r)
        self.assertIn('Science-based international organisations',r['issues'])

    def test_explicit_country_policy_without_narrow_issue_backfills(self):
        title = 'China revises science policy for foreign researchers'
        body = 'This research assesses governance choices for public research institutions.'
        self.assertIsNone(matching(title,body))
        r = matching(title,body,backfill=True)
        self.assertIsNotNone(r)
        self.assertIn('China',r['countries'])
        self.assertIn(COUNTRY_POLICY_ISSUE,r['issues'])

    def test_incidental_country_in_late_body_not_backfilled(self):
        title = 'Innovation governance trends in European universities'
        body = ('An assessment of policy in Europe. ' + 'A generic description of European governance. '*50 +
                ' China is briefly mentioned in an appendix.')
        self.assertIsNone(matching(title,body,backfill=True))

    def test_stored_reader_only_verified_keep_surfaces(self):
        key = 'link:https://example.org/moldova-science'
        data = {
            'radar_active.json': {}, 'radar.json': {}, 'historical/historical.json': {'items': []},
            'deep_scan_work_state.json': {'records': {key: {
                'status': 'verified', 'title': 'Moldova research innovation governance and EU cooperation',
                'date': '2026-01-05', 'url': 'https://example.org/moldova-science'}}},
            'admission_state.json': {'records': {key: {'decision': 'keep'}}},
            'reader_text.json': {'records': {key: {
                'profile': 'deep-reader-v2-authoritative',
                'reader_what': 'Moldova strengthens research policy partnerships with Europe.',
                'verification': {'identity_verified': True}}}}
        }
        with patch('relevance_focus.load', side_effect=lambda name, default: data.get(name,default)):
            out = compile_records()
        self.assertEqual(len(out['verified']), 1)
        self.assertEqual(len(out['pending']), 0)
        self.assertEqual(out['verified'][0]['source_location'], 'Stored Deep Scan / Reader')

    def test_stored_reader_only_dropped_never_promoted(self):
        key = 'link:https://example.org/moldova-science'
        data = {
            'radar_active.json': {}, 'radar.json': {}, 'historical/historical.json': {'items': []},
            'deep_scan_work_state.json': {'records': {key: {
                'status': 'verified', 'title': 'Moldova research innovation governance and EU cooperation',
                'url': 'https://example.org/moldova-science'}}},
            'admission_state.json': {'records': {key: {'decision': 'drop'}}},
            'reader_text.json': {'records': {key: {
                'profile': 'deep-reader-v2-authoritative',
                'verification': {'identity_verified': True}}}}
        }
        with patch('relevance_focus.load', side_effect=lambda name, default: data.get(name,default)):
            out = compile_records()
        self.assertEqual(out['verified'], [])
        self.assertEqual(out['pending'], [])

    def test_mixed_case_url_uses_authoritative_keep_decision(self):
        # Opaque Google News IDs and many publisher URL paths are case-sensitive.
        url = 'https://news.google.com/rss/articles/CbMiAbC123?oc=5'
        key = 'link:' + url
        item = {'title': 'EU China research innovation policy and science diplomacy',
                'url': url, 'date': '2026-04-08', 'summary': 'China research cooperation and European policy'}
        data = {
            'radar_active.json': {'strand_c': [item]}, 'radar.json': {'strand_c': [item]},
            'historical/historical.json': {'items': []},
            'deep_scan_work_state.json': {'records': {key: {'status': 'verified', 'title': item['title'], 'url': url}}},
            'admission_state.json': {'records': {key: {'decision': 'keep'}}},
            'reader_text.json': {'records': {key: {
                'profile': 'deep-reader-v2-authoritative',
                'verification': {'identity_verified': True}}}}
        }
        with patch('relevance_focus.load', side_effect=lambda name, default: data.get(name, default)):
            out = compile_records()
        self.assertEqual(len(out['verified']), 1)
        self.assertEqual(len(out['pending']), 0)

    def test_mixed_case_url_never_readmits_existing_drop(self):
        url = 'https://news.google.com/rss/articles/CbMiAbC123?oc=5'
        key = 'link:' + url
        item = {'title': 'EU China research innovation policy and science diplomacy',
                'url': url, 'date': '2026-04-08', 'summary': 'China research cooperation and European policy'}
        data = {
            'radar_active.json': {}, 'radar.json': {'strand_c': [item]},
            'historical/historical.json': {'items': []},
            'deep_scan_work_state.json': {'records': {key: {'status': 'verified', 'title': item['title'], 'url': url}}},
            'admission_state.json': {'records': {key: {'decision': 'drop'}}},
            'reader_text.json': {'records': {key: {
                'profile': 'deep-reader-v2-authoritative',
                'verification': {'identity_verified': True}}}}
        }
        with patch('relevance_focus.load', side_effect=lambda name, default: data.get(name, default)):
            out = compile_records()
        self.assertEqual(out['verified'], [])
        self.assertEqual(out['pending'], [])

    def test_stakeholder_alone_not_backfilled(self):
        self.assertIsNone(matching('University research in Canada','A university laboratory upgraded its equipment.',backfill=True))



class RegionalDiscoveryTests(unittest.TestCase):
    """The only new discovery lane: corpus-grounded, one-region, source-gated."""

    @staticmethod
    def _india_openalex():
        text = 'An evaluation of clinical trials and biomedical research investment in India.'
        index = {}
        for i, word in enumerate(text.split()):
            index.setdefault(word, []).append(i)
        return {
            'display_name': 'Biomedical research in India: current capacity and future investment',
            'abstract_inverted_index': index, 'type': 'article', 'is_retracted': False,
            'publication_date': '2025-03-11', 'doi': 'https://doi.org/10.1234/biomed-india-2025',
            'primary_location': {'source': {'display_name': 'International Health Policy Review'}},
        }

    def test_topics_come_from_actual_main_radar_results(self):
        from relevance_focus import focus_areas
        raw = {'strand_a': [
            {'title': 'Biomedical research and clinical research priorities for Europe',
             'summary': 'Clinical research funding and health research capacity.'}
        ], 'strand_b': [], 'strand_c': []}
        areas = focus_areas(raw=raw)
        self.assertIn('Health research', areas)
        self.assertNotIn('Artificial intelligence', areas)
        self.assertNotIn('Quantum', areas)

    def test_india_only_article_qualifies_through_existing_eu_relevant_issue(self):
        from relevance_focus import relevance_work
        entry = relevance_work('openalex', self._india_openalex(),
                               allowed_topics={'Health research': 'biomedical research'},
                               expected_region='India', expected_topic='Health research')
        self.assertIsNotNone(entry)
        _, _, result = entry
        self.assertEqual(result['focus_region'], 'India')
        self.assertEqual(result['focus_issue'], 'Health research')
        self.assertNotIn('Europe', result['title'])
        self.assertIn('active Main Radar', result['curator_note'])
        self.assertEqual(result['url'], 'https://doi.org/10.1234/biomed-india-2025')

    def test_no_unrelated_india_theme_is_allowed(self):
        from relevance_focus import relevance_work
        wrong = dict(self._india_openalex())
        wrong['display_name'] = 'Artificial intelligence technology policy in India'
        wrong['abstract_inverted_index'] = {}
        self.assertIsNone(relevance_work(
            'openalex', wrong, allowed_topics={'Health research': 'biomedical research'},
            expected_region='India', expected_topic='Health research'))

    def test_region_must_be_substantive_not_abstract_tail_or_affiliation(self):
        from relevance_focus import relevance_work
        item = dict(self._india_openalex())
        item['display_name'] = 'Biomedical research governance reforms in Germany'
        item['abstract_inverted_index'] = {
            'Biomedical': [0], 'research': [1], 'reform': [2], 'Germany': [3],
            'discussion': list(range(4, 440)), 'India': [440],
        }
        self.assertIsNone(relevance_work('openalex', item,
                          allowed_topics={'Health research': 'biomedical research'},
                          expected_region='India', expected_topic='Health research'))
        item['display_name'] = 'Biomedical research governance worldwide'
        item['abstract_inverted_index'] = {}
        item['primary_location'] = {'source': {'display_name': 'Indian Journal of Science'}}
        self.assertIsNone(relevance_work('openalex', item,
                          allowed_topics={'Health research': 'biomedical research'},
                          expected_region='India', expected_topic='Health research'))

    def test_source_integrity_filters_retractions_preprints_missing_doi_venue(self):
        from relevance_focus import relevance_work
        base = self._india_openalex()
        for change in ({'type': 'preprint'}, {'is_retracted': True},
                       {'doi': ''}, {'primary_location': {'source': None}}):
            bad = {**base, **change}
            self.assertIsNone(relevance_work('openalex', bad,
                              allowed_topics={'Health research': 'biomedical research'},
                              expected_region='India', expected_topic='Health research'))

    def test_plan_covers_world_and_separate_time_lenses(self):
        from relevance_focus import focused_search_plan
        plans = list(focused_search_plan(5, focus={'Health research': 'biomedical research'}))
        regions = {p[0] for p in plans}
        times = {p[3] for p in plans}
        self.assertIn('EU / UK', regions)
        self.assertIn('Asia & Pacific', regions)
        self.assertIn('Africa', regions)
        self.assertIn('Americas', regions)
        self.assertEqual(times, {'Current state / developments',
                                 'Possible future / scenarios'})
        self.assertFalse(any('history evolution trends' in p[4] for p in plans))
        self.assertTrue(any('India' in p[4] for p in plans))
        self.assertTrue(any('biomedical research India' in p[4] for p in plans))
        self.assertEqual(len({(p[4], p[5]) for p in plans}), len(plans))
        self.assertTrue(all(p[-1] == 1 for p in plans))

    def test_balancing_keeps_india_but_prevents_external_flood(self):
        from relevance_focus import balanced_candidates, OUTSIDE_EU_UK_SHARE
        picked = {}
        for i in range(60):
            item = {'candidate_id': f'EU-{i}', 'focus_group': 'EU / UK',
                    'focus_region': 'Germany' if i % 2 else 'France',
                    'focus_issue': 'Health research' if i % 2 else 'Biotechnology'}
            picked[f'core:{i}'] = (90, 'EU / UK', item)
        for i in range(80):
            item = {'candidate_id': f'EXT-{i}', 'focus_group': 'Asia & Pacific',
                    'focus_region': 'India', 'focus_issue': 'Health research'}
            picked[f'ext:{i}'] = (99, 'Asia & Pacific', item)
        selected = balanced_candidates(picked, 30)
        external = [x for x in selected if x['focus_group'] != 'EU / UK']
        self.assertTrue(external)
        self.assertTrue(all(x['focus_region'] == 'India' for x in external))
        self.assertLessEqual(len(external), int(30 * OUTSIDE_EU_UK_SHARE))
        self.assertEqual(len(selected), 30)
        external_only = {k: v for k, v in picked.items() if k.startswith('ext:')}
        solo = balanced_candidates(external_only, 30)
        self.assertGreater(len(solo), 0)
        self.assertLessEqual(len(solo), 6)

    def test_publication_cutoff_rejects_old_and_undated_discoveries(self):
        from relevance_focus import relevance_work, publication_date_in_scope, temporal_lens
        self.assertFalse(publication_date_in_scope('2024-12-31'))
        self.assertTrue(publication_date_in_scope('2025-01-01'))
        self.assertTrue(publication_date_in_scope('2025'))
        self.assertFalse(publication_date_in_scope(''))
        self.assertFalse(publication_date_in_scope('2025-02-30'))
        self.assertNotIn('historical', temporal_lens('Past capacity and science research evolution').lower())
        for previous_date in ('2024-12-31', '2010-01-01', ''):
            old = {**self._india_openalex(), 'publication_date': previous_date}
            self.assertIsNone(relevance_work('openalex', old,
                allowed_topics={'Health research': 'biomedical research'},
                expected_region='India', expected_topic='Health research'))

    def test_crossref_report_with_doi_publisher_and_regional_issue(self):
        from relevance_focus import relevance_work
        work = {'type': 'report', 'title': ['Biomedical research in India: future research capacity'],
                'abstract': '<jats:p>Health research capacity and innovation strategy in India.</jats:p>',
                'DOI': '10.1111/global-biomed-india', 'published': {'date-parts': [[2025, 2, 4]]},
                'publisher': 'International Science Policy Institute'}
        result = relevance_work('crossref', work,
                                allowed_topics={'Health research': 'biomedical research'},
                                expected_region='India', expected_topic='Health research')
        self.assertIsNotNone(result)
        self.assertEqual(result[2]['publication_type'], 'report')
        work['published'] = {'date-parts': [[2024, 12, 31]]}
        self.assertIsNone(relevance_work('crossref', work,
                            allowed_topics={'Health research': 'biomedical research'},
                            expected_region='India', expected_topic='Health research'))
        work.pop('published')
        work['created'] = {'date-parts': [[2026, 2, 4]]}
        self.assertIsNone(relevance_work('crossref', work,
                            allowed_topics={'Health research': 'biomedical research'},
                            expected_region='India', expected_topic='Health research'))
        work['published'] = {'date-parts': [[2025, 2, 4]]}
        work['type'] = 'posted-content'
        self.assertIsNone(relevance_work('crossref', work,
                            allowed_topics={'Health research': 'biomedical research'},
                            expected_region='India', expected_topic='Health research'))

    def test_discover_uses_required_metadata_and_archives_unadmitted_leads(self):
        import json
        import tempfile
        from relevance_focus import discover, load

        class Response:
            status_code = 200
            ok = True
            def json(self):
                return {'results': [RegionalDiscoveryTests._india_openalex()]}

        class Session:
            def __init__(self):
                self.headers = {}
                self.requests = []
            def get(self, url, params, timeout):
                self.requests.append((url, params, timeout))
                return Response()

        session = Session()
        vocabulary = load('topic_vocabulary.json', [])
        current = [10.0]
        with tempfile.TemporaryDirectory() as td:
            target, archive = Path(td) / 'temp_batch.json', Path(td) / 'regional.json'
            one_plan = iter([('Asia & Pacific', 'India', 'Health research',
                              'Current state / developments',
                              'biomedical research India',
                              'openalex', 1)])
            with patch('relevance_focus.focus_areas', return_value={'Health research':'biomedical research'}), \
                 patch('relevance_focus.load', side_effect=lambda name,default: vocabulary if name == 'topic_vocabulary.json' else {}), \
                 patch('relevance_focus.focused_search_plan', return_value=one_plan):
                discover(target, max_seconds=5, session=session,
                         clock=lambda: current[0], pause=lambda delay: current.__setitem__(0,current[0]+delay),
                         archive_path=archive)
            document = json.loads(target.read_text())
            stored = json.loads(archive.read_text())
            self.assertEqual(stored['archive_mode'], 'cumulative-doi-deduplicated')
            self.assertEqual(stored['work_count'], 1)
            self.assertEqual(stored['latest_batch_work_count'], 1)
            self.assertEqual(stored['candidates'][0]['doi'], document['candidates'][0]['doi'])
            self.assertEqual(len(document['candidates']), 1)
            self.assertEqual(document['candidates'][0]['focus_region'], 'India')
            url, query, _ = session.requests[0]
            self.assertIn('openalex', url)
            self.assertIn('type,is_retracted', query['select'])
            self.assertIn('from_publication_date:2025-01-01', query['filter'])
            self.assertEqual(document['policy']['outside_eu_uk_capacity_ceiling'], 0.4)
            self.assertEqual(document['policy']['earliest_publication_date'], '2025-01-01')

    def test_backfill_output_excludes_older_and_historical_without_mutating_sources(self):
        from relevance_focus import compile_records
        old = {'title': 'EU China research innovation policy and science diplomacy',
               'date': '2024-12-31', 'url': 'https://example.org/old'}
        recent = {'title': 'EU India science diplomacy and research policy cooperation',
                  'date': '2025-01-01', 'url': 'https://example.org/new'}
        files = {
            'radar_active.json': {'strand_a': [old, recent]},
            'radar.json': {'strand_a': [old, recent]},
            'historical/historical.json': {'items': [{**old, 'date': '2026-04-01'}]},
            'deep_scan_work_state.json': {'records': {}},
            'admission_state.json': {'records': {}},
            'reader_text.json': {'records': {}},
            'Relevance Stuff/regional_discoveries.json': {'candidates': [
                {'title':'old indexed lead', 'date':'2024-11-20'},
                {'title':'recent indexed lead', 'date':'2025-02-20'},
                {'title':'undated indexed lead'},
            ]},
        }
        with patch('relevance_focus.load', side_effect=lambda name,default: files.get(name,default)) as loader:
            output = compile_records()
        self.assertEqual([r['title'] for r in output['pending']], [recent['title']])
        self.assertEqual([r['title'] for r in output['regional_leads']], ['recent indexed lead'])
        self.assertGreater(output['statistics']['source_rows_before_2025_or_undated'], 0)
        self.assertFalse(any(c.args[0] == 'historical/historical.json' for c in loader.call_args_list))
        self.assertEqual(files['radar_active.json']['strand_a'], [old, recent])


    def test_doi_identity_normalizes_provider_links_and_preserves_legacy_leads(self):
        from relevance_focus import doi_identity, lead_identity
        self.assertEqual(doi_identity({'doi': 'HTTPS://DOI.ORG/10.1234/ABC/'}), '10.1234/abc')
        self.assertEqual(doi_identity({'url': 'https://dx.doi.org/10.1234/abc'}), '10.1234/abc')
        self.assertEqual(lead_identity({'candidate_id': 'REL-legacy'}), 'id:REL-legacy')

    def test_cumulative_archive_retains_old_batches_and_collapses_duplicate_dois(self):
        from relevance_focus import cumulative_discoveries
        first = {'batch_id': 'first', 'candidates': [
            {'title': 'India study', 'doi': '10.1234/INDIA', 'date': '2025-01-10'}],
            'discovery_stats': {}}
        latest = {'batch_id': 'latest', 'candidates': [
            {'title': 'Brazil study', 'doi': '10.1234/BRAZIL', 'date': '2026-03-10'}],
            'discovery_stats': {}}
        fresh = {'batch_id': 'fresh', 'candidates': [
            {'title': 'Canada study', 'doi': '10.1234/CANADA', 'date': '2026-04-10'},
            {'title': 'Duplicate India study', 'url': 'https://doi.org/10.1234/india'}],
            'discovery_stats': {'successful_requests': 8}}
        cumulative = cumulative_discoveries(latest, fresh, slot=101,
                                            older_snapshots=[first, latest])
        self.assertEqual(cumulative['work_count'], 3)
        self.assertEqual(cumulative['latest_batch_work_count'], 2)
        self.assertEqual(cumulative['rotation_index'], 101)
        self.assertEqual([x['title'] for x in cumulative['candidates']],
                         ['India study', 'Brazil study', 'Canada study'])
        self.assertEqual(cumulative['candidates'][0]['first_seen_batch_id'], 'first')
        self.assertEqual(latest['candidates'][0]['title'], 'Brazil study')

    def test_rotation_advances_every_successful_run_and_legacy_timestamp(self):
        from relevance_focus import next_rotation_slot
        from datetime import datetime, timezone
        now = datetime(2026, 11, 9, 14, 0, tzinfo=timezone.utc)
        self.assertEqual(next_rotation_slot({'rotation_index': 150}, now), 151)
        previous = {'compiled_at': '2026-11-09T13:38:53+00:00'}
        self.assertEqual(next_rotation_slot(previous, now),
                         int(datetime(2026, 11, 9, 13, 38, tzinfo=timezone.utc).timestamp() // 14400) + 1)
        self.assertEqual(next_rotation_slot({}, now), int(now.timestamp() // 14400))

    def test_discovery_remembers_previous_doi_and_only_emits_new_batch(self):
        import json
        import tempfile
        from relevance_focus import discover, load
        vocabulary = load('topic_vocabulary.json', [])

        original = self._india_openalex()
        canada = {**original, 'display_name': 'Biomedical research in Canada',
                  'doi': 'https://doi.org/10.1234/biomed-canada-2026',
                  'publication_date': '2026-02-05'}
        canada['abstract_inverted_index'] = {word: [i] for i, word in
                 enumerate('Biomedical research investment and clinical trials in Canada'.split())}
        class Response:
            ok = True
            status_code = 200
            def json(self):
                return {'results': [original, canada]}
        class Session:
            def __init__(self): self.headers = {}
            def get(self, url, params, timeout): return Response()
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'batch.json'
            archive = Path(tmp) / 'archive.json'
            prior = {'batch_id': 'older', 'compiled_at': '2026-11-09T13:38:53+00:00',
                     'candidates': [{'title': original['display_name'],
                                     'doi': '10.1234/BIOMED-INDIA-2025',
                                     'date': '2025-03-11'}]}
            archive.write_text(json.dumps(prior))
            plan_slots = []
            def fake_plan(slot, focus=None):
                plan_slots.append(slot)
                return iter([('Asia & Pacific', 'India', 'Health research',
                              'Current state / developments',
                              'biomedical research India', 'openalex', 1)])
            # Two identical searches: only Canada should be newly sent to Radar.
            # An additional new country is deliberately NOT matched by an India
            # query; use one expected region for both candidate titles instead.
            canada['display_name'] = 'Biomedical research investment in India and Canada'
            canada['abstract_inverted_index'] = {word: [i] for i, word in
                 enumerate('Biomedical research and clinical trials in India and Canada'.split())}
            for run_no in range(2):
                t = [5.0]
                with patch('relevance_focus.focus_areas', return_value={'Health research':'biomedical research'}), \
                     patch('relevance_focus.focused_search_plan', side_effect=fake_plan), \
                     patch('relevance_focus.historical_discovery_snapshots', return_value=[]), \
                     patch('relevance_focus.load', side_effect=lambda n, d: vocabulary if n == 'topic_vocabulary.json' else {}):
                    discover(target, max_seconds=5, archive_path=archive,
                             session=Session(), clock=lambda: t[0],
                             pause=lambda d: t.__setitem__(0, t[0]+d))
                emitted = json.loads(target.read_text())['candidates']
                stored = json.loads(archive.read_text())
                self.assertEqual(len(emitted), 1 if run_no == 0 else 0)
                self.assertEqual(len(stored['candidates']), 2)
                self.assertEqual(stored['work_count'], 2)
            self.assertEqual(plan_slots[1], plan_slots[0] + 1)

    def test_legacy_git_snapshots_are_recovered_in_original_order(self):
        import json
        import subprocess
        import tempfile
        from relevance_focus import historical_discovery_snapshots
        with tempfile.TemporaryDirectory() as tmp:
            def git(*args):
                subprocess.run(['git', '-C', tmp, *args], check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            git('init', '-q')
            git('config', 'user.name', 'Test')
            git('config', 'user.email', 'test@example.org')
            path = Path(tmp) / 'Relevance Stuff' / 'regional_discoveries.json'
            path.parent.mkdir(parents=True)
            for batch in ('first', 'second'):
                path.write_text(json.dumps({'batch_id': batch, 'candidates': [
                    {'title': batch, 'doi': '10.1234/' + batch}]}))
                git('add', '--', 'Relevance Stuff/regional_discoveries.json')
                git('commit', '-qm', batch)
            with patch('relevance_focus.ROOT', Path(tmp)):
                recovered = historical_discovery_snapshots()
            self.assertEqual([x['batch_id'] for x in recovered], ['first', 'second'])

    def test_archive_rejects_malformed_json_without_erasing_it(self):
        import tempfile
        from relevance_focus import read_discovery_archive
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'regional.json'
            p.write_text('NOT JSON')
            with self.assertRaises(ValueError):
                read_discovery_archive(p)
            self.assertEqual(p.read_text(), 'NOT JSON')

    def test_one_hit_backfill_keeps_verified_standard_and_no_synthetic_promotion(self):
        # The independent one-hit backfill still requires the same KEEP and
        # authoritative reader identity checks, regardless of region searching.
        from relevance_focus import compile_records
        key = 'link:https://doi.org/10.1234/test-india'
        files = {
            'radar_active.json': {}, 'radar.json': {}, 'historical/historical.json': {'items': []},
            'deep_scan_work_state.json': {'records': {key: {
                'status': 'verified', 'title': 'India biomedical research policy and science diplomacy',
                'url': key[5:]}}},
            'admission_state.json': {'records': {key: {'decision': 'drop'}}},
            'reader_text.json': {'records': {key: {'profile':'deep-reader-v2-authoritative',
                                                  'verification': {'identity_verified': True}}}},
            'Relevance Stuff/regional_discoveries.json': {'candidates': [{
                'candidate_id':'REL-123', 'title':'Biomedical research in India',
                'focus_region':'India', 'focus_group':'Asia & Pacific',
                'date':'2025-06-08', 'url':'https://doi.org/10.1234/test-india'}]},
        }
        with patch('relevance_focus.load', side_effect=lambda n,d: files.get(n,d)):
            report = compile_records()
        self.assertEqual(report['verified'], [])
        self.assertEqual(report['pending'], [])
        self.assertEqual(len(report['regional_leads']), 1)
        self.assertEqual(report['regional_leads'][0]['radar_check_status'], 'indexed_lead_not_verified')

if __name__ == '__main__': unittest.main()
