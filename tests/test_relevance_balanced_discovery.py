"""Regression checks: sparse-topic discovery must retain balanced coverage."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import relevance_focus as focus


class BalancedDiscoveryTests(unittest.TestCase):
    def test_all_24_priorities_get_first_wave_opportunity(self):
        labels = set(focus.FOCUS_TRACK)
        self.assertEqual(len(labels), 24)
        for slot in (0, 5, 19):
            first_wave = []
            seen = set()
            for row in focus.focused_search_plan(slot):
                topic = row[2]
                if topic in seen and len(seen) == len(labels):
                    break
                seen.add(topic)
                first_wave.append(row)
                if len(seen) == len(labels) and len(first_wave) >= 68:
                    break
            self.assertEqual(seen, labels)

    def test_policy_order_rotates_whole_catalogue(self):
        for slot in (0, 5, 19):
            topics = list(focus.focus_areas())
            expected_first = topics[slot % len(topics)]
            self.assertEqual(next(focus.focused_search_plan(slot))[2], expected_first)

    def test_regional_anchor_does_not_add_extra_requests(self):
        # First wave: 10 critical techs x 2 geography lanes and
        # 14 regional themes x 1 geography lane, each with 2 providers.
        for slot in (0, 1, 3):
            rows = list(focus.focused_search_plan(slot))
            first_wave = rows[:68]
            from collections import Counter
            counts = Counter(row[2] for row in first_wave)
            for topic, track in focus.FOCUS_TRACK.items():
                self.assertEqual(counts[topic], 4 if track == 'critical_technology' else 2)
            self.assertTrue(all(focus.priority_region_match(r[2], r[0], r[1])
                                for r in first_wave if focus.FOCUS_TRACK[r[2]] != 'critical_technology'))

    def test_regional_subject_still_checked(self):
        self.assertIsNone(focus.regional_matching(
            'Marine biodiversity research in Australia',
            'Australian scientists study marine biodiversity and oceanography.',
            expected_topic='ASEAN: Marine science'))
        self.assertIsNotNone(focus.regional_matching(
            'Marine biodiversity research in Indonesia',
            'Indonesian researchers study oceanographic monitoring systems.',
            expected_topic='ASEAN: Marine science'))

if __name__ == '__main__':
    unittest.main()
