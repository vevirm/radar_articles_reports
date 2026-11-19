"""Regression tests for regional retrieval, balanced candidate selection and live diagnostics."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import relevance_focus as rf


class BalancedRepairTests(unittest.TestCase):
    def test_policy_catalogue_is_10_plus_14(self):
        self.assertEqual(Counter(rf.FOCUS_TRACK.values())['critical_technology'], 10)
        self.assertEqual(sum(v != 'critical_technology' for v in rf.FOCUS_TRACK.values()), 14)

    def test_single_unified_vocabulary_for_all_priorities(self):
        self.assertEqual(set(rf.FOCUS_DISCOVERY_VOCABULARY), set(rf.FOCUS_TRACK))
        for topic, terms in rf.FOCUS_DISCOVERY_VOCABULARY.items():
            self.assertTrue(terms, topic)
            self.assertEqual(len(terms), len(set(terms)), topic)
            for term in rf.FOCUS_QUERIES[topic]:
                self.assertIn(term, terms, topic)
            for term in (rf.REGIONAL_DISCOVERY_SYNONYMS.get(topic, ()) +
                         rf.TECHNOLOGY_AND_REGIONAL_DISCOVERY_SYNONYMS.get(topic, ())):
                self.assertIn(term, terms, topic)

    def test_each_priority_rotates_across_its_single_vocabulary(self):
        # Read the planned query sequence, not results from external services.
        priority = 'ASEAN: Marine science'
        terms = rf.FOCUS_DISCOVERY_VOCABULARY[priority]
        seen = set()
        for slot in range(len(terms)):
            rows = [r for r in rf.focused_search_plan(slot) if r[2] == priority]
            self.assertTrue(rows)
            seen.update(term for term in terms if any(term in r[4] for r in rows))
        self.assertEqual(seen, set(terms))

    def test_regional_queries_do_not_force_future_outlook_filter(self):
        plan = list(rf.focused_search_plan(0))
        for row in plan[:136]:
            if rf.FOCUS_TRACK[row[2]] != 'critical_technology':
                self.assertNotIn('future outlook scenarios', row[4])

    def test_source_region_not_query_country_controls_classification(self):
        # A search targeted at Thailand can return a valid Indonesia article.
        # The country must come from the publication, not the search query.
        title = 'Marine biodiversity research in Indonesia'
        body = 'This study investigates marine biodiversity in Indonesian coastal ecosystems.'
        matched = rf.regional_matching(title, body,
                                       expected_topic='ASEAN: Marine science')
        self.assertIsNotNone(matched)
        self.assertIn('Indonesia', matched['matched_locations'])
        self.assertNotIn('Thailand', matched['matched_locations'])

    def test_wrong_region_never_promoted_to_asean(self):
        self.assertIsNone(rf.regional_matching(
            'Marine biodiversity research in Australia',
            'A scientific study of marine biodiversity in coastal Australia.',
            expected_topic='ASEAN: Marine science'))
        self.assertIsNone(rf.regional_matching(
            'Marine biodiversity research in Indonesia and Australia',
            'This work studies oceanography in Australia, not Indonesian waters.',
            expected_topic='CELAC: Health'))

    def test_valid_region_not_overridden_by_unrelated_other_region(self):
        match = rf.regional_matching(
            'Marine science and oceanographic research in Indonesia and Australia',
            'Marine biodiversity research investigates Indonesian coastal waters.',
            expected_topic='ASEAN: Marine science')
        self.assertIsNotNone(match)
        self.assertEqual(match['primary_group'], 'Asia & Pacific')
        self.assertEqual(match['matched_locations'], ['Indonesia'])

    def test_candidate_cap_retains_existing_rare_priority(self):
        # Use v4 tagged rows to exercise the capped mixed EU/global branch.
        entries = {}
        topics = list(rf.FOCUS_TRACK)
        for i in range(200):
            topic = topics[i % 2] if i < 198 else topics[10 + (i - 198)]
            row = {'candidate_id': f'REL-{i:04}', 'focus_group': 'Global',
                   'focus_region': 'Global / unspecified', 'focus_issue': topic,
                   'focus_quality_revision': rf.FOCUS_QUALITY_REVISION,
                   'source': f'Journal {i}', 'title': f'Study {i}'}
            entries[str(i)] = (80, 'Global', row)
        selected = rf.balanced_candidates(entries, 30)
        self.assertEqual(len(selected), 30)
        self.assertEqual(len({r['candidate_id'] for r in selected}), 30)
        self.assertIn(topics[10], {r['focus_issue'] for r in selected})
        self.assertIn(topics[11], {r['focus_issue'] for r in selected})

    def test_first_wave_search_all_priorities(self):
        wave = list(rf.focused_search_plan(1))[:68]
        self.assertEqual(set(r[2] for r in wave), set(rf.FOCUS_TRACK))
        self.assertEqual(len(wave), 68)


if __name__ == '__main__':
    unittest.main()
