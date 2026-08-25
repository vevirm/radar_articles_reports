import datetime as dt
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    sys.modules["feedparser"] = types.ModuleType("feedparser")

import scripts.scan_radar as sr

ROOT = Path(__file__).resolve().parents[1]


class Resp:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}
    def json(self):
        return self._payload


class V1758KeylessDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.old_deadline = sr.SCAN_DEADLINE_MONO
        sr.SCAN_DEADLINE_MONO = None
    def tearDown(self):
        sr.SCAN_DEADLINE_MONO = self.old_deadline

    def test_crossref_uses_relevance_newest_and_upper_date_bound(self):
        calls = []
        rows = 3
        def fake_get(url, params=None, timeout=None):
            calls.append(dict(params or {}))
            return Resp(200, {"message": {"items": [{"title": [f"x{i}"]} for i in range(rows)]}})
        with mock.patch.object(sr.SESSION, 'get', side_effect=fake_get), \
             mock.patch.object(sr, 'candidate_from_crossref', return_value=None), \
             mock.patch.object(sr.time, 'sleep', return_value=None), \
             mock.patch.dict(sr.CONFIG, {'crossref_rows_per_query': rows, 'crossref_depth_pages_max': 2, 'crossref_public_min_interval_seconds': 0}, clear=False):
            depth = {}
            sr.collect_crossref(dt.date(2026, 4, 21), [], ['test query'], [], broad_depth_state=depth)
        self.assertGreaterEqual(len(calls), 3)
        self.assertIn('until-pub-date:', calls[0]['filter'])
        self.assertNotIn('sort', calls[0])
        self.assertEqual(calls[1].get('sort'), 'published')
        self.assertEqual(calls[1].get('order'), 'desc')
        self.assertEqual(calls[2].get('offset'), rows)
        self.assertNotIn('sort', calls[2])

    def test_crossref_future_date_is_rejected(self):
        future = dt.date.today() + dt.timedelta(days=30)
        item = {
            'title': ['European research security and strategic autonomy'],
            'published': {'date-parts': [[future.year, future.month, future.day]]},
            'container-title': ['Research Policy'],
            'type': 'journal-article',
            'abstract': 'European Union research and innovation policy addresses economic security and strategic autonomy.',
        }
        with mock.patch.object(sr, 'quality_from_crossref', return_value=(True, 2, 2.0, 'Research Policy', 'Tier 2', 'peer-reviewed article')):
            self.assertIsNone(sr.candidate_from_crossref(item, dt.date.today() - dt.timedelta(days=120)))

    def test_openalex_is_keyless_and_date_is_bounded(self):
        calls = []
        def fake_get(url, params=None, timeout=None):
            calls.append(dict(params or {}))
            return Resp(200, {'results': []})
        with mock.patch.object(sr.SESSION, 'get', side_effect=fake_get), \
             mock.patch.dict(sr.CONFIG, {'openalex_public_min_interval_seconds': 0}, clear=False):
            sr.collect_openalex(dt.date.today() - dt.timedelta(days=30), [], ['test query'])
        self.assertNotIn('api_key', calls[0])
        self.assertNotIn('mailto', calls[0])
        self.assertIn('to_publication_date:', calls[0]['filter'])

    def test_openalex_429_does_not_retry(self):
        calls = []
        def fake_get(url, params=None, timeout=None):
            calls.append(1)
            return Resp(429, {})
        warnings = []
        with mock.patch.object(sr.SESSION, 'get', side_effect=fake_get), \
             mock.patch.object(sr.time, 'sleep', return_value=None), \
             mock.patch.dict(sr.CONFIG, {'openalex_public_min_interval_seconds': 0, 'scholarly_public_retries': 4, 'openalex_public_workers': 1}, clear=False):
            sr.collect_openalex(dt.date.today() - dt.timedelta(days=30), warnings, ['test query'])
        self.assertEqual(len(calls), 1)
        self.assertTrue(any('429' in w and 'continuing with Crossref' in w for w in warnings))

    def test_workflow_uses_no_secrets(self):
        workflow = (ROOT / '.github/workflows/radar-scan.yml').read_text()
        self.assertNotIn('secrets.', workflow)
        self.assertNotIn('OPENALEX_API_KEY', workflow)

    def test_versions_are_not_bumped(self):
        cfg = json.loads((ROOT / 'radar_config.json').read_text())
        self.assertEqual(cfg['incremental_state_version'], 'v17.2-persistent-source-cursors')
        self.assertEqual(cfg['source_expansion_version'], 'v17.5.2-gap-report-recall')
        self.assertEqual(cfg['quality_profile_version'], 'v17.9.0-source-aware-aboutness-matrix-rubric')


if __name__ == '__main__':
    unittest.main()
