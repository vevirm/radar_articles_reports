import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import scripts.scan_radar as sr


class V15ScanRepairTests(unittest.TestCase):
    def test_valid_live_radar_does_not_walk_git_history(self):
        sample = {
            "last_updated": "2026-08-20T01:53Z",
            "first_scan_complete": True,
            "strand_a": [{"title": "A", "date": "2026-08-01", "source_tier": "Tier 1"}],
            "strand_b": [],
            "strand_c": [],
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "radar.json"
            p.write_text(json.dumps(sample), encoding="utf-8")
            with mock.patch.object(sr, "OUT_PATH", p), \
                 mock.patch.object(sr, "_recover_radar_from_git", side_effect=AssertionError("git recovery should not run")), \
                 mock.patch.object(sr, "_augment_with_git_history", side_effect=AssertionError("history union should not run")):
                got = sr.load_previous()
        self.assertEqual(got["strand_a"][0]["title"], "A")

    def test_malformed_saved_rows_are_ignored_not_fatal(self):
        sample = {
            "last_updated": "2026-08-20T01:53Z",
            "first_scan_complete": True,
            "strand_a": [None, "bad", {"title": "Keep A", "date": "2026-08-01", "source_tier": None}],
            "strand_b": [42, {"title": "Keep B", "date": "2026-08-02"}],
            "strand_c": [[], {"headline": "Keep C", "source": "Reuters", "date": "2026-08-19T12:00Z"}],
        }
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "radar.json"
            p.write_text(json.dumps(sample), encoding="utf-8")
            with mock.patch.object(sr, "OUT_PATH", p):
                got = sr.load_previous()
        self.assertEqual([x["title"] for x in got["strand_a"]], ["Keep A"])
        self.assertEqual([x["title"] for x in got["strand_b"]], ["Keep B"])
        self.assertEqual([x["headline"] for x in got["strand_c"]], ["Keep C"])
        self.assertIsInstance(sr.internalize_previous(got["strand_a"][0]), dict)

    def test_main_preserves_live_corpus_when_all_network_stages_fail(self):
        sample = {
            "last_updated": "2026-08-20T01:53Z",
            "first_scan_complete": True,
            "source_expansion_version": "old-version",
            "strand_a": [{
                "title": "Existing A", "authors": "X", "source": "X", "date": "2026-08-01",
                "link": "https://example.org/a", "type": "institutional report", "strand": "A",
                "eu_relevance": "direct", "summary": "EU research security and innovation policy.",
                "relevance_note": "kept", "source_tier": None, "first_seen": "2026-08-01T00:00Z"
            }, None],
            "strand_b": [],
            "strand_c": [],
        }
        def boom(*args, **kwargs):
            raise RuntimeError("network down")
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "radar.json"
            p.write_text(json.dumps(sample), encoding="utf-8")
            with mock.patch.object(sr, "OUT_PATH", p), \
                 mock.patch.object(sr, "collect_openalex", side_effect=boom), \
                 mock.patch.object(sr, "collect_crossref", side_effect=boom), \
                 mock.patch.object(sr, "collect_institutions", side_effect=boom), \
                 mock.patch.object(sr, "collect_news", side_effect=boom), \
                 mock.patch.dict(sr.CONFIG, {"scan_budget_seconds": 30}, clear=False):
                rc = sr.main()
            data = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(rc, 0)
            self.assertEqual([x["title"] for x in data["strand_a"]], ["Existing A"])
            self.assertEqual(data["scan_health"], "degraded")
            self.assertFalse(p.with_suffix(".json.tmp").exists())

    def test_packaged_scanner_budget_fits_active_90_minute_workflow(self):
        self.assertLessEqual(int(sr.CONFIG["scan_budget_seconds"]), 3300)
        self.assertGreaterEqual(int(sr.CONFIG["scan_budget_seconds"]), 3000)

    def test_active_workflow_is_zero_config_and_nonfatal_pages(self):
        workflow = (sr.ROOT / ".github" / "workflows" / "radar-scan.yml").read_text(encoding="utf-8")
        self.assertNotIn("OPENALEX_API_KEY", workflow)
        self.assertNotIn("CROSSREF_MAILTO", workflow)
        self.assertIn("timeout-minutes: 90", workflow)
        self.assertIn("continue-on-error: true", workflow)


if __name__ == "__main__":
    unittest.main()
