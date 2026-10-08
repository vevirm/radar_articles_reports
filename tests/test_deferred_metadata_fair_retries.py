"""Regression tests for anti-starvation of persistent metadata recovery."""
import datetime as dt
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SCAN = Path(__file__).resolve().parents[1] / 'scripts' / 'scan_radar.py'
spec = importlib.util.spec_from_file_location('radar_retry_test', SCAN)
radar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(radar)


class DeferredMetadataFairnessTests(unittest.TestCase):
    def test_recent_failure_does_not_starve_new_row(self):
        now = dt.datetime(2026, 10, 8, tzinfo=dt.timezone.utc)
        items = [
            {'key': 'stuck', 'attempts': 9, 'last_attempted': '2026-10-07T12:00:00+00:00'},
            {'key': 'new', 'attempts': 0},
            {'key': 'due', 'attempts': 1, 'last_attempted': '2026-10-07T00:00:00+00:00'},
        ]
        self.assertEqual([r['key'] for r in radar.order_deferred_metadata_retries(items, now)], ['new', 'due'])

    def test_queue_preserved_and_later_entries_retried_under_cap(self):
        old = [{'key': f'fail-{i}', 'provider': 'crossref', 'raw': {'DOI': f'10.1234/{i}'},
                'attempts': 8, 'last_attempted': dt.datetime.now(dt.timezone.utc).isoformat()}
               for i in range(20)]
        fresh = {'key': 'new', 'provider': 'crossref', 'raw': {'DOI': '10.1234/new'}, 'attempts': 0}
        state = {'deferred_metadata_queue': old + [fresh]}
        with patch.object(radar, 'candidate_from_crossref', return_value=None), \
             patch.object(radar, 'recover_scholarly_abstract', return_value=('', '')) as fetch, \
             patch.dict(radar.CONFIG, {'deferred_metadata_recovery_per_scan': 1,
                                       'network_reserve_seconds': 0}):
            radar.recover_persistent_metadata_queue(state, [], None)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(fetch.call_args.args[0], '10.1234/new')
        self.assertEqual(len(state['deferred_metadata_queue']), 21)
        self.assertEqual(state['deferred_metadata_retry_stats']['retrieval_attempted'], 1)


if __name__ == '__main__':
    unittest.main()
