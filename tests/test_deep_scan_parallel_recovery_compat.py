"""Regression: parallel worker source-read audit labels are recognized."""
import copy
import unittest
from scripts.import_deep_scan_results import validate_v2_result

BASE = {
    'verification': {
        'identity_verified': True,
        'evidence_depth': 'full_text_or_substantive_primary',
        'verification_note': 'Matched real primary content with the source.',
        'retrieval_attempts': [
            {'step': 'supplied_url', 'outcome': 'available_in_prior_research_ledger', 'note': 'Old source ledger is not a fresh download.'},
            {'step': 'live_source_page', 'outcome': 'source_page_read', 'note': 'Primary source page was read independently.'},
        ],
        'recovered_sources': [{'kind': 'publisher_or_institution_page', 'url': 'https://example.org/study', 'evidence_used': True}],
    },
    'admission': {'decision': 'drop', 'target_strand': 'A', 'reason_code': 'OUT_OF_SCOPE', 'reason': 'The document is unrelated to research and innovation.'},
    'duplicate': {'status': 'unique', 'duplicate_of': '', 'reason': ''},
    'metadata_correction': {'fields': {}, 'unset': [], 'reason': ''},
}

class ParallelRecoveryCompat(unittest.TestCase):
    def check(self, x):
        return validate_v2_result(x, key='id:record', current_keys={'id:record'})

    def test_live_read_is_recognized(self):
        self.assertEqual(self.check(copy.deepcopy(BASE)), [])

    def test_package_content_is_recognized(self):
        x = copy.deepcopy(BASE)
        x['verification']['retrieval_attempts'][1] = {'step': 'source_material', 'outcome': 'package_text_examined', 'note': 'Matching source text was examined.'}
        self.assertEqual(self.check(x), [])

    def test_prior_ledger_alone_is_not_recovery(self):
        x = copy.deepcopy(BASE)
        x['verification']['retrieval_attempts'].pop()
        self.assertTrue(any('recovery-ladder step' in p for p in self.check(x)))

    def test_missing_evidence_still_fails(self):
        x = copy.deepcopy(BASE)
        x['verification']['recovered_sources'] = []
        self.assertTrue(any('substantive recovered source' in p for p in self.check(x)))

if __name__ == '__main__':
    unittest.main()
