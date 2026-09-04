from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ScannerSerializationWorkflowTests(unittest.TestCase):
    def test_workflows_share_one_valid_concurrency_group(self):
        main = (ROOT / ".github/workflows/radar-scan.yml").read_text(encoding="utf-8")
        hist = (ROOT / ".github/workflows/historical-scan.yml").read_text(encoding="utf-8")
        for text in (main, hist):
            self.assertIn("group: ri-research-scanners", text)
            self.assertIn("cancel-in-progress: false", text)
            self.assertNotIn("queue: max", text)
        self.assertIn("cron: '17 0,4,8,12,16,20 * * *'", main)
        self.assertIn("cron: '53 6 * * *'", hist)

    def test_historical_peer_defer_refreshes_window_only_not_corpus(self):
        path = ROOT / "historical" / "scan_historical.py"
        spec = importlib.util.spec_from_file_location("hist_serialization_test_module", path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        original_path = module.OUT_PATH
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "historical.json"
            seed = {
                "last_updated": "2026-08-31T00:00:00Z",
                "date_from": "2015-01-01",
                "date_to": "2026-02-27",
                "cutoff_exclusive": "2026-02-28",
                "main_radar_window_months": 6,
                "items": [{"id": "keep-me", "manual_curated": True}],
                "scan_state": {"topic_cursor": 7, "completed_runs": 42},
                "last_scan": {"new_items": 2, "rejection_funnel": {"x": 1}},
            }
            out.write_text(json.dumps(seed), encoding="utf-8")
            module.OUT_PATH = out
            try:
                module.refresh_window_metadata_after_peer_defer()
            finally:
                module.OUT_PATH = original_path
            result = json.loads(out.read_text(encoding="utf-8"))

        self.assertEqual(result["items"], seed["items"])
        self.assertEqual(result["scan_state"], seed["scan_state"])
        self.assertEqual(result["last_scan"], seed["last_scan"])
        self.assertEqual(result["last_updated"], seed["last_updated"])
        self.assertEqual(result["date_from"], module.DATE_FROM.isoformat())
        self.assertEqual(result["cutoff_exclusive"], module.CUTOFF_EXCLUSIVE.isoformat())
        self.assertEqual(result["date_to"], module.DATE_TO.isoformat())
        self.assertTrue(result["workflow_compatibility"]["peer_deferred_without_source_requests"])


if __name__ == "__main__":
    unittest.main()
