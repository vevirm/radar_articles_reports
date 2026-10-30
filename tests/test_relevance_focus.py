"""Deterministic contract tests for the standalone relevance subset and discovery route."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from relevance_focus import GEOGRAPHY, ISSUES, matching


class RelevanceFocusTests(unittest.TestCase):
    def test_enlargement_names_complete(self):
        self.assertEqual(set(GEOGRAPHY['Europe — enlargement']), {
            'Albania','Bosnia and Herzegovina','Georgia','Kosovo','Moldova',
            'Montenegro','North Macedonia','Serbia','Ukraine','Türkiye'})

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


if __name__ == '__main__': unittest.main()
