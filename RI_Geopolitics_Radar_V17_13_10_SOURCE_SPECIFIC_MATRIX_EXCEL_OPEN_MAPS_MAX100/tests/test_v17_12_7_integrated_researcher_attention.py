import unittest
from pathlib import Path

import scripts.scan_radar as sr


ROOT = Path(__file__).resolve().parents[1]


class IntegratedResearcherAttentionTests(unittest.TestCase):
    def test_public_item_strips_researcher_watch_labels(self):
        item = {
            'title': 'European research security and advanced technology',
            'summary': 'The paper examines European research security and advanced technology cooperation.',
            'strand': 'A',
            'priority_watch_people': ['Example Researcher'],
            'priority_watch_category': 'AI & machine learning',
            'priority_watch_lane': 'recurring exact-author attention',
            'priority_context_fallback': True,
            '_priority_person': 'Example Researcher',
            '_priority_origin': 'openalex',
        }
        public = sr.public_item(item)
        self.assertNotIn('priority_watch_people', public)
        self.assertNotIn('priority_watch_category', public)
        self.assertNotIn('priority_watch_lane', public)
        self.assertNotIn('priority_context_fallback', public)
        self.assertFalse(any(k.startswith('_priority') for k in public))

    def test_priority_candidate_uses_private_routing_fields_only(self):
        tagged = sr._tag_priority_candidate(
            {'title': 'A paper', 'strand': 'A'},
            {'name': 'Example Researcher', 'category': 'Quantum technologies'},
            'crossref',
        )
        self.assertEqual(tagged['_priority_origin'], 'crossref')
        self.assertEqual(tagged['_priority_person'], 'Example Researcher')
        self.assertFalse(any(k.startswith('priority_watch') for k in tagged))

    def test_no_frontend_surface_for_researcher_watch_input(self):
        for path in list(ROOT.rglob('*.html')) + list(ROOT.rglob('*.js')):
            text = path.read_text(encoding='utf-8', errors='ignore').lower()
            self.assertNotIn('priority_people', text, path.as_posix())
            self.assertNotIn('priority watch', text, path.as_posix())
            self.assertNotIn('priority_people.json', text, path.as_posix())

    def test_backend_watch_file_still_feeds_rotation(self):
        people = sr.load_priority_people()
        self.assertEqual(len(people), 137)
        plan = sr.priority_people_rotation_plan(sr.initial_scan_state({}), limit=16)
        self.assertEqual(len(plan['people']), 16)


if __name__ == '__main__':
    unittest.main()
