import datetime as dt
import unittest
from unittest import mock

import scripts.scan_radar as sr


class Response:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = {}

    def json(self):
        return self._payload


class PriorityPeopleRotationTests(unittest.TestCase):
    def test_curated_file_contains_137_unique_people_and_broad_domains(self):
        people = sr.load_priority_people()
        self.assertEqual(len(people), 137)
        self.assertEqual(len({sr.folded_person_name(x['name']) for x in people}), 137)
        self.assertGreaterEqual(len({x['category'] for x in people}), 15)

    def test_rotation_interleaves_categories_instead_of_scanning_one_field_first(self):
        state = sr.initial_scan_state({})
        plan = sr.priority_people_rotation_plan(state, limit=16)
        self.assertEqual(len(plan['people']), 16)
        self.assertEqual(len(plan['categories']), 16)
        self.assertIn('AI & machine learning', plan['categories'])
        self.assertIn('Quantum technologies', plan['categories'])
        self.assertIn('Biotech & health', plan['categories'])

    def test_old_scan_state_is_extended_without_resetting_normal_rotation(self):
        previous = {
            'scan_state': {
                'version': sr.INCREMENTAL_STATE_VERSION,
                'source_expansion_version': sr.SOURCE_EXPANSION_VERSION,
                'openalex_cursor': 41,
                'crossref_broad_cursor': 17,
                'crossref_priority_cursor': 99,
                'institution_cursor': 11,
            }
        }
        state = sr.initial_scan_state(previous)
        self.assertEqual(state['openalex_cursor'], 41)
        self.assertEqual(state['crossref_broad_cursor'], 17)
        self.assertEqual(state['institution_cursor'], 11)
        self.assertEqual(state['priority_people_cursor'], 0)
        self.assertEqual(state['priority_people_openalex_author_ids'], {})

    def test_context_fallback_uses_affiliation_and_topic_not_only_person_name(self):
        person = {
            'name': 'Example Researcher',
            'category': 'Quantum technologies',
            'affiliation_hint': 'QuTech / TU Delft',
            'topic_hints': ['quantum networks', 'NV centres'],
        }
        q = sr.priority_person_context_query(person)
        self.assertIn('QuTech', q)
        self.assertIn('quantum networks', q)
        self.assertIn('Europe research innovation', q)
        self.assertNotIn('Example Researcher', q)

    def test_exact_author_lane_uses_openalex_author_id_and_crossref_query_author(self):
        person = {
            'name': 'Bernhard Schölkopf',
            'category': 'AI & machine learning',
            'affiliation_hint': 'MPI Intelligent Systems, Tübingen',
            'topic_hints': ['causal inference', 'kernel methods'],
        }
        calls = []

        def fake_get(url, params=None, timeout=None, **kwargs):
            params = dict(params or {})
            calls.append((url, params))
            if url.endswith('/authors'):
                return Response(200, {
                    'results': [{
                        'display_name': 'Bernhard Schölkopf',
                        'id': 'https://openalex.org/A123456789',
                        'works_count': 500,
                        'last_known_institutions': [{'display_name': 'Max Planck Institute for Intelligent Systems'}],
                    }]
                })
            if 'api.openalex.org/works' in url:
                return Response(200, {'results': [{'display_name': 'OA work'}]})
            if 'api.crossref.org/works' in url:
                return Response(200, {'message': {'items': [{
                    'title': ['CR work'],
                    'author': [{'given': 'Bernhard', 'family': 'Schölkopf'}],
                    'DOI': '10.1000/example',
                }]}})
            raise AssertionError(url)

        stats = {}
        state = {}
        with mock.patch.object(sr.SESSION, 'get', side_effect=fake_get), \
             mock.patch.object(sr, 'candidate_from_openalex', return_value={'title': 'OA admitted'}), \
             mock.patch.object(sr, 'candidate_from_crossref', return_value={'title': 'CR admitted'}), \
             mock.patch.object(sr, 'dedupe_candidates', side_effect=lambda rows: rows):
            out = sr.collect_priority_people([person], dt.date(2026, 4, 21), [], state=state, execution_stats=stats)

        self.assertEqual(len(out), 2)
        oa_work_calls = [p for u, p in calls if 'api.openalex.org/works' in u]
        self.assertTrue(any('A123456789' in p.get('filter', '') for p in oa_work_calls))
        cr_calls = [p for u, p in calls if 'api.crossref.org/works' in u]
        self.assertEqual(cr_calls[0]['query.author'], 'Bernhard Schölkopf')
        self.assertEqual(stats['priority_people_context_queries'], [])
        self.assertIn('Bernhard Schölkopf', stats['priority_people_executed'])

    def test_zero_exact_hits_create_bounded_substantive_context_query(self):
        person = {
            'name': 'Example Researcher',
            'category': 'Advanced materials',
            'affiliation_hint': 'EPFL / PSI',
            'topic_hints': ['computational materials discovery', 'MARVEL'],
        }

        def fake_get(url, params=None, timeout=None, **kwargs):
            if url.endswith('/authors'):
                return Response(200, {'results': []})
            if 'api.crossref.org/works' in url:
                return Response(200, {'message': {'items': []}})
            raise AssertionError(url)

        stats = {}
        with mock.patch.object(sr.SESSION, 'get', side_effect=fake_get):
            out = sr.collect_priority_people([person], dt.date(2026, 4, 21), [], state={}, execution_stats=stats)
        self.assertEqual(out, [])
        self.assertEqual(len(stats['priority_people_context_queries']), 1)
        self.assertIn('EPFL', stats['priority_people_context_queries'][0])
        self.assertIn('computational materials discovery', stats['priority_people_context_queries'][0])


if __name__ == '__main__':
    unittest.main()
