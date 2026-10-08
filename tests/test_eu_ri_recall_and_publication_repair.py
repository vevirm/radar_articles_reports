"""Deterministic tests for European/EU research-and-innovation Radar publication/recovery."""
import datetime as dt
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('radar_euri_repair', ROOT / 'scripts/scan_radar.py')
radar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(radar)


class EURIRepairTests(unittest.TestCase):
    def test_migration_keeps_old_private_backlog_and_ledger(self):
        legacy = {'version': 'v24.7.5-relative-publication-8-1-3',
                  'published': {'A': 177, 'B': 64, 'C': 313},
                  'pending_b': [{'title': 'A prior accepted research method'}],
                  'pending_c': [{'headline': 'A prior accepted European R&I event'}]}
        state = {'relative_mix_publication': legacy}
        converted = radar.relative_mix_publication_state(state)
        self.assertEqual(len(converted['pending_b']), 1)
        self.assertEqual(len(converted['pending_c']), 1)
        self.assertEqual(converted['published']['C'], 313)
        self.assertEqual(converted['migrated_from_version'], 'v24.7.5-relative-publication-8-1-3')
        self.assertNotEqual(converted['version'], 'v24.7.5-relative-publication-8-1-3')

    def test_high_c_ledger_cannot_veto_ordinary_eligible_c(self):
        row = {'headline': 'EU research funding capacity changes', 'date': '2026-10-08',
               'c_admission_route': 'event', 'event_status': 'OBSERVED',
               'link': 'https://www.europarl.europa.eu/test', 'source': 'European Parliament'}
        with patch.object(radar, 'exceptional_c_release_decision', return_value={'eligible': False}), \
             patch.object(radar, '_c_publication_rank_key', return_value=(0, 0, 0)):
            selected, deferred, stats = radar.select_relative_c_release(
                [row], {'A': 177, 'B': 64, 'C': 313}, 0)
        self.assertEqual(len(selected), 1)
        self.assertEqual(deferred, [])
        self.assertTrue(stats['relative_target_is_diagnostic_only'])

    def test_retry_order_alternates_due_failures_and_old_untried(self):
        now = dt.datetime(2026, 10, 8, tzinfo=dt.timezone.utc)
        rows = [
            {'key': 'fresh-2', 'attempts': 0, 'first_seen': '2026-10-07T00:00:00Z'},
            {'key': 'old-retry', 'attempts': 1, 'last_attempted': '2026-10-06T00:00:00Z'},
            {'key': 'fresh-1', 'attempts': 0, 'first_seen': '2026-10-05T00:00:00Z'},
        ]
        ordered = radar.order_deferred_metadata_retries(rows, now)
        self.assertEqual([r['key'] for r in ordered], ['fresh-1', 'old-retry', 'fresh-2'])

    def test_rediscovery_preserves_failure_clock_and_first_seen(self):
        old = {'key': 'crossref:doi', 'provider': 'crossref',
               'raw': {'DOI': 'doi'}, 'attempts': 4,
               'last_attempted': '2026-10-06T11:00:00Z', 'last_seen': '2026-10-07T00:00:00Z',
               'first_seen': '2026-09-20T00:00:00Z'}
        fresh = {'key': 'crossref:doi', 'provider': 'crossref',
                 'raw': {'DOI': 'doi', 'abstract': ''}, 'attempts': 0,
                 'last_seen': '2026-10-08T00:00:00Z'}
        rows = radar.compact_deferred_metadata_queue([old, fresh], 100)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['attempts'], 4)
        self.assertEqual(rows[0]['first_seen'], '2026-09-20T00:00:00Z')
        self.assertEqual(rows[0]['last_attempted'], old['last_attempted'])

    def test_queue_cap_keeps_old_and_fresh_doi_rows(self):
        rows = [
            {'key': f'crossref:{i}', 'provider': 'crossref',
             'raw': {'DOI': f'10.1/{i}'},
             'last_seen': f'2026-10-{i + 1:02d}T00:00:00Z',
             'first_seen': f'2026-10-{i + 1:02d}T00:00:00Z'}
            for i in range(10)
        ]
        chosen = radar.compact_deferred_metadata_queue(rows, 4)
        keys = {r['key'] for r in chosen}
        self.assertIn('crossref:0', keys)
        self.assertIn('crossref:9', keys)
        self.assertEqual(len(chosen), 4)

    def test_corrupted_no_doi_raw_does_not_crash_queue_compaction(self):
        rows = [
            {'key': 'broken', 'raw': ['unexpected', 'list'], 'last_seen': '2026-10-01'},
            {'key': 'valid', 'raw': {'DOI': '10.1234/safe'}, 'last_seen': '2026-10-08'},
        ]
        compacted = radar.compact_deferred_metadata_queue(rows, 1)
        self.assertEqual([row['key'] for row in compacted], ['valid'])

    def test_admitted_persistent_candidate_cannot_reenter_queue(self):
        radar._METADATA_DEFERRED_THIS_SCAN.clear()
        radar._METADATA_RESOLVED_THIS_SCAN.clear()
        raw = {'DOI': '10.1234/success'}
        old = {'key': 'crossref:10.1234/success', 'provider': 'crossref', 'raw': raw}
        state = {'deferred_metadata_queue': [old]}
        with patch.object(radar, 'candidate_from_crossref', return_value={'title': 'Good EU R&I paper'}), \
             patch.dict(radar.CONFIG, {'deferred_metadata_recovery_per_scan': 1}):
            admitted = radar.recover_persistent_metadata_queue(state, [])
        radar.remember_deferred_metadata('crossref', raw)
        radar.persist_current_metadata_queue(state)
        self.assertEqual(len(admitted), 1)
        self.assertEqual(state['deferred_metadata_queue'], [])
        radar._METADATA_RESOLVED_THIS_SCAN.clear()

    def test_successfully_resolved_old_key_removed_before_persist(self):
        radar._METADATA_DEFERRED_THIS_SCAN.clear()
        radar._METADATA_RESOLVED_THIS_SCAN.clear()
        old = {'key': 'crossref:10.1/valid', 'provider': 'crossref', 'raw': {'DOI': '10.1/valid'}}
        state = {'deferred_metadata_queue': [old]}
        radar.resolve_deferred_metadata('crossref', {'DOI': '10.1/valid'})
        radar.persist_current_metadata_queue(state)
        self.assertEqual(state['deferred_metadata_queue'], [])
        radar._METADATA_RESOLVED_THIS_SCAN.clear()


if __name__ == '__main__':
    unittest.main()
