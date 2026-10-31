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

    def test_stakeholder_alone_not_backfilled(self):
        self.assertIsNone(matching('University research in Canada','A university laboratory upgraded its equipment.',backfill=True))


if __name__ == '__main__': unittest.main()
