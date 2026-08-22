import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import scan_radar as radar


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.content = b""
        self.text = ""
        self.headers = headers or {"content-type": "application/json"}
        self.url = "https://example.test/"

    def json(self):
        return self._payload


class V14ZeroConfigTests(unittest.TestCase):
    def setUp(self):
        self.old_deadline = radar.SCAN_DEADLINE_MONO
        radar.SCAN_DEADLINE_MONO = None

    def tearDown(self):
        radar.SCAN_DEADLINE_MONO = self.old_deadline

    def test_openalex_attempts_full_query_universe_without_credentials(self):
        warnings = []
        calls = []
        original_a = radar.CONFIG["queries_a"]
        original_b = radar.CONFIG["queries_b"]

        def fake_get(url, params=None, timeout=None, **kwargs):
            calls.append(dict(params or {}))
            return FakeResponse(200, {"results": []})

        try:
            radar.CONFIG["queries_a"] = ["a one", "a two"]
            radar.CONFIG["queries_b"] = ["b one"]
            with mock.patch.object(radar.SESSION, "get", side_effect=fake_get), \
                 mock.patch.dict(radar.CONFIG, {"openalex_public_min_interval_seconds": 0}, clear=False):
                out = radar.collect_openalex(dt.date.today() - dt.timedelta(days=30), warnings)
        finally:
            radar.CONFIG["queries_a"] = original_a
            radar.CONFIG["queries_b"] = original_b

        self.assertEqual(out, [])
        self.assertEqual(len(calls), 3)
        self.assertTrue(all("api_key" not in params for params in calls))

    def test_crossref_uses_public_requests_without_mailto_secret(self):
        warnings = []
        calls = []
        original_a = radar.CONFIG["queries_a"]
        original_b = radar.CONFIG["queries_b"]

        def fake_get(url, params=None, timeout=None, **kwargs):
            calls.append(dict(params or {}))
            return FakeResponse(200, {"message": {"items": []}})

        try:
            radar.CONFIG["queries_a"] = ["a one"]
            radar.CONFIG["queries_b"] = ["b one"]
            with mock.patch.object(radar.SESSION, "get", side_effect=fake_get), \
                 mock.patch.dict(radar.CONFIG, {"crossref_public_min_interval_seconds": 0, "crossref_priority_journals": [], "crossref_priority_journal_queries": []}, clear=False):
                out = radar.collect_crossref(dt.date.today() - dt.timedelta(days=30), warnings)
        finally:
            radar.CONFIG["queries_a"] = original_a
            radar.CONFIG["queries_b"] = original_b

        self.assertEqual(out, [])
        self.assertEqual(len(calls), 4)
        self.assertTrue(all("mailto" not in params for params in calls))
        self.assertTrue(all("until-pub-date:" in params.get("filter", "") for params in calls))
        self.assertTrue(all("sort" not in calls[i] for i in (0, 2)))
        self.assertEqual(calls[1].get("sort"), "published")
        self.assertEqual(calls[3].get("sort"), "published")

    def test_public_openalex_unavailable_does_not_crash_stage(self):
        warnings = []
        original_a = radar.CONFIG["queries_a"]
        original_b = radar.CONFIG["queries_b"]
        try:
            radar.CONFIG["queries_a"] = ["a one", "a two"]
            radar.CONFIG["queries_b"] = []
            with mock.patch.object(radar.SESSION, "get", return_value=FakeResponse(403, {})), \
                 mock.patch.dict(radar.CONFIG, {"openalex_public_min_interval_seconds": 0}, clear=False):
                out = radar.collect_openalex(dt.date.today() - dt.timedelta(days=30), warnings)
        finally:
            radar.CONFIG["queries_a"] = original_a
            radar.CONFIG["queries_b"] = original_b
        self.assertEqual(out, [])
        self.assertTrue(any("continuing with Crossref" in w for w in warnings))

    def test_v14_marker_forces_four_month_backfill_on_upgrade(self):
        previous = {
            "last_updated": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source_expansion_version": "v13-balanced-relevance-resilient-scan",
        }
        self.assertTrue(radar.needs_source_expansion_backfill(previous))

    def test_main_survives_fatal_source_stage_errors_and_writes_radar(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "radar.json"
            boom = RuntimeError("upstream unavailable")
            with mock.patch.object(radar, "OUT_PATH", out), \
                 mock.patch.object(radar, "load_previous", return_value={}), \
                 mock.patch.object(radar, "collect_openalex", side_effect=boom), \
                 mock.patch.object(radar, "collect_crossref", side_effect=boom), \
                 mock.patch.object(radar, "collect_institutions", side_effect=boom), \
                 mock.patch.object(radar, "collect_news", side_effect=boom), \
                 mock.patch.dict(radar.CONFIG, {"scan_budget_seconds": 30}, clear=False):
                rc = radar.main()

            self.assertEqual(rc, 0)
            data = json.loads(out.read_text())
            self.assertEqual(data["scan_health"], "degraded")
            self.assertFalse(data["backfill_complete"])
            self.assertTrue(data["zero_config_scan"])
            self.assertEqual(data["strand_a"], [])
            self.assertEqual(data["strand_b"], [])
            self.assertEqual(data["strand_c"], [])
            self.assertEqual(data["scan_diagnostics"]["source_warning_count"], 4)
            self.assertTrue(any("fatal stage error" in w for w in data["scan_diagnostics"]["source_warnings"]))

    def test_workflow_keeps_openalex_key_optional_and_crossref_zero_config(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "radar-scan.yml").read_text()
        self.assertNotIn("OPENALEX_API_KEY", workflow)
        self.assertNotIn("CROSSREF_MAILTO", workflow)
        self.assertNotIn("secrets.CROSSREF", workflow)


if __name__ == "__main__":
    unittest.main()
