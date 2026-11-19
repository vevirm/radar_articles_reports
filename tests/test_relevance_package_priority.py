"""Focused safeguards for the manually prepared 60-case Relevance Deep Scan."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import relevance_focus_deep_scan as deep


class TestSixtyCaseReviewPriority(unittest.TestCase):
    @staticmethod
    def lead(candidate_id, topic, title, focus_score=50):
        return {'candidate_id': candidate_id, 'focus_issue': topic,
                'title': title, 'focus_score': focus_score,
                'geographic_evidence': ''}

    def test_strong_research_remains_first_even_with_same_topic_repetition(self):
        strong = [self.lead(f'REL-q-{i:02}', 'Critical technology: Quantum technologies',
                 f'Quantum sensor prototype research infrastructure {i}', 85)
                  for i in range(12)]
        weak = [self.lead(f'REL-w-{i:02}', 'Africa: Public health',
                f'Public health management of COVID-19 in Morocco {i}', 99)
                for i in range(12)]
        ranked = deep.balanced_review_jobs(weak + strong, 12)
        self.assertTrue(all(r['candidate_id'].startswith('REL-q-') for r in ranked))

    def test_diversity_still_breaks_close_scores(self):
        a = self.lead('REL-a', 'Critical technology: Quantum technologies',
                      'Quantum sensor prototype research infrastructure', 60)
        a2 = dict(a, candidate_id='REL-a2')
        b = self.lead('REL-b', 'Critical technology: Energy technologies',
                      'Hydrogen battery prototype research infrastructure', 59)
        ranked = deep.balanced_review_jobs([a, a2, b], 3)
        self.assertEqual(ranked[0]['candidate_id'], 'REL-a')
        self.assertEqual(ranked[1]['candidate_id'], 'REL-b')
        self.assertEqual(len(ranked), 3)

    def test_60_review_slots_are_ordered_and_not_padded(self):
        candidates = [self.lead(f'REL-{i:03}', 'Critical technology: Quantum technologies',
                       f'Quantum sensor prototype study {i}', 100 - i)
                      for i in range(70)]
        ranked = deep.balanced_review_jobs(list(reversed(candidates)), 60)
        self.assertEqual(len(ranked), 60)
        self.assertEqual([r['candidate_id'] for r in ranked],
                         [f'REL-{i:03}' for i in range(60)])
        self.assertEqual(len(deep.balanced_review_jobs(candidates[:3], 60)), 3)


if __name__ == '__main__':
    unittest.main()
