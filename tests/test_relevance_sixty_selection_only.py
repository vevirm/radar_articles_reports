"""Regression tests specific to manual/current-focus 60-case selection."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import relevance_focus_deep_scan as deep


def lead(i, topic, title, score=70):
    return dict(candidate_id=f'REL-{i:03}', focus_issue=topic, title=title,
                focus_score=score, geographic_evidence='')


class TestSixtySelectionOnly(unittest.TestCase):
    def test_reduces_concentration_when_other_research_is_competitive(self):
        q = 'Critical technology: Advanced semiconductors'
        e = 'Critical technology: Energy technologies'
        other = 'Critical technology: Robotics and autonomous systems'
        pool = ([lead(i, q, f'Semiconductor chip prototype photolithography {i}', 80)
                 for i in range(30)] +
                [lead(i+30, e, f'Hydrogen battery prototype energy storage {i}', 80)
                 for i in range(30)] +
                [lead(i+60, other, f'Robot autonomous navigation prototype {i}', 79)
                 for i in range(20)])
        selected = deep.select_sixty_review_jobs(pool, 60)
        self.assertEqual(len(selected), 60)
        self.assertGreater(sum(r['focus_issue'] == other for r in selected),
                           sum(r['focus_issue'] == other for r in
                               deep.balanced_review_jobs(pool, 60)))

    def test_much_stronger_research_is_not_displaced_by_weak_other_topic(self):
        strong = [lead(i, 'Critical technology: Quantum technologies',
                       f'Quantum sensor prototype {i}', 95) for i in range(60)]
        weak = [lead(i+100, 'Africa: Public health',
                     f'Public health management of COVID-19 {i}', 99) for i in range(60)]
        selected = deep.select_sixty_review_jobs(strong + weak, 60)
        self.assertTrue(all(r['candidate_id'] in {s['candidate_id'] for s in strong} for r in selected))

    def test_not_padded_and_deterministic(self):
        rows = [lead(i, 'Critical technology: Energy technologies',
                     f'Hydrogen storage methods {i}', 50) for i in range(8)]
        first = deep.select_sixty_review_jobs(rows, 60)
        second = deep.select_sixty_review_jobs(list(reversed(rows)), 60)
        self.assertEqual([r['candidate_id'] for r in first],
                         [r['candidate_id'] for r in second])
        self.assertEqual(len(first), 8)

    def test_distinct_strong_works_can_still_dominate(self):
        energy = [lead(i, 'Critical technology: Energy technologies',
                       f'Hydrogen battery prototype {i}', 90) for i in range(65)]
        weak = [lead(i+100, 'Africa: Public health',
                     f'Public health management of COVID-19 {i}', 40) for i in range(20)]
        chosen = deep.select_sixty_review_jobs(energy + weak, 60)
        self.assertEqual(len(chosen), 60)
        self.assertTrue(all(r['focus_issue'] == 'Critical technology: Energy technologies'
                            for r in chosen))

    def test_automatic_selection_function_unmodified(self):
        self.assertIsNot(deep.select_sixty_review_jobs, deep.balanced_review_jobs)


if __name__ == '__main__':
    unittest.main()
