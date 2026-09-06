import importlib.util
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_scan_v172048", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}
        self.headers = {}
        self.url = "https://api.crossref.org/works"

    def json(self):
        return self._data


class IncrementalEngineTests(unittest.TestCase):
    def test_legacy_current_target_backfill_is_completed_without_deleting_corpus(self):
        previous = {
            "last_updated": "2026-09-06T05:11Z",
            "source_expansion_version": "v17.5.2-gap-report-recall",
            "recall_profile_version": scan.RECALL_PROFILE_VERSION,
            "strand_a": [{"title": "keep old important work"}],
            "scan_state": {
                "version": scan.INCREMENTAL_STATE_VERSION,
                "source_expansion_version": scan.SOURCE_EXPANSION_VERSION,
                "backfill": {"openalex": False, "crossref_broad": False, "crossref_priority": False, "institutions": True},
                "completed_cycles": {"openalex": 4, "crossref_broad": 5, "crossref_priority": 3, "institutions": 43},
                "cycle_failed": {"openalex": True, "crossref_broad": True, "crossref_priority": True, "institutions": False},
                "openalex_cursor": 216,
                "crossref_broad_cursor": 176,
                "crossref_priority_cursor": 2382,
                "institution_cursor": 58,
            },
        }
        state = scan.initial_scan_state(previous)
        self.assertEqual(state["backfill"], {"openalex": True, "crossref_broad": True, "crossref_priority": True, "institutions": True})
        self.assertTrue(state["source_expansion_legacy_completion_migrated"])
        self.assertEqual(state["openalex_cursor"], 216)
        self.assertEqual(previous["strand_a"][0]["title"], "keep old important work")

    def test_future_source_expansion_does_not_reset_every_family_to_four_month_backfill(self):
        previous = {
            "last_updated": "2026-09-06T05:11Z",
            "source_expansion_version": "older-target",
            "recall_profile_version": scan.RECALL_PROFILE_VERSION,
            "scan_state": {
                "version": scan.INCREMENTAL_STATE_VERSION,
                "source_expansion_version": "older-target",
                "backfill": {"openalex": True, "crossref_broad": True, "crossref_priority": True, "institutions": True},
                "completed_cycles": {"openalex": 2, "crossref_broad": 2, "crossref_priority": 2, "institutions": 2},
                "cycle_failed": {"openalex": False, "crossref_broad": False, "crossref_priority": False, "institutions": False},
            },
        }
        state = scan.initial_scan_state(previous)
        self.assertEqual(state["backfill"], {"openalex": True, "crossref_broad": True, "crossref_priority": True, "institutions": True})
        self.assertFalse(state["source_expansion_backfill_reopened"])
        self.assertTrue(state["source_expansion_bounded_refresh"])

    def test_recall_profile_change_preserves_rotation_instead_of_global_reset(self):
        previous = {
            "last_updated": "2026-09-06T05:11Z",
            "source_expansion_version": scan.SOURCE_EXPANSION_VERSION,
            "recall_profile_version": "older-recall-profile",
            "scan_state": {
                "version": scan.INCREMENTAL_STATE_VERSION,
                "source_expansion_version": scan.SOURCE_EXPANSION_VERSION,
                "backfill": {"openalex": True, "crossref_broad": True, "crossref_priority": True, "institutions": True},
                "completed_cycles": {"openalex": 3, "crossref_broad": 3, "crossref_priority": 3, "institutions": 3},
                "cycle_failed": {"openalex": False, "crossref_broad": False, "crossref_priority": False, "institutions": False},
                "openalex_cursor": 41,
                "crossref_broad_cursor": 52,
                "institution_cursor": 63,
            },
        }
        state = scan.initial_scan_state(previous)
        self.assertEqual(state["openalex_cursor"], 41)
        self.assertEqual(state["crossref_broad_cursor"], 52)
        self.assertEqual(state["institution_cursor"], 63)
        self.assertEqual(state["backfill"], {"openalex": True, "crossref_broad": True, "crossref_priority": True, "institutions": True})
        self.assertFalse(state["recall_reset_this_run"])
        self.assertTrue(state["recall_profile_changed_this_run"])

    def test_source_first_journal_uses_incremental_from_date_not_global_four_month_floor(self):
        seen_filters = []

        def fake_get(url, *args, **kwargs):
            params = kwargs.get("params") or {}
            if "api.crossref.org/works" in url:
                seen_filters.append(str(params.get("filter", "")))
                return FakeResponse(200, {"message": {"items": []}})
            raise AssertionError(url)

        from_date = scan.dt.date(2026, 8, 23)
        old_floor = scan.DATE_FLOOR
        scan.DATE_FLOOR = scan.dt.date(2026, 5, 6)
        try:
            with mock.patch.object(scan.SESSION, "get", side_effect=fake_get), mock.patch.dict(scan.CONFIG, {
                "crossref_public_min_interval_seconds": 0,
                "scholarly_public_retries": 0,
                "crossref_source_first_depth_pages_max": 1,
            }, clear=False):
                scan.collect_crossref(
                    from_date,
                    [],
                    queries_override=[],
                    priority_tasks_override=[],
                    source_sweep_journals_override=["Research Policy"],
                    stage_deadline=time.monotonic() + 5,
                    execution_stats={},
                )
        finally:
            scan.DATE_FLOOR = old_floor
        self.assertTrue(seen_filters)
        self.assertTrue(all("from-pub-date:2026-08-23" in x for x in seen_filters), seen_filters)
        self.assertTrue(all("from-pub-date:2026-05-06" not in x for x in seen_filters), seen_filters)

    def test_snowball_seeds_are_doi_scholarly_and_rotate(self):
        items = []
        for i in range(30):
            items.append({
                "title": f"European research policy evidence paper {i}",
                "date": "2026-09-01",
                "link": f"https://doi.org/10.1234/paper-{i}",
                "type": "peer-reviewed article",
                "source_tier": "Tier 2",
                "eu_relevance": "direct",
                "strand": "A",
            })
        # These used to outrank the papers merely for being Tier 1.
        for i in range(8):
            items.append({
                "title": f"EU institutional announcement {i}",
                "date": "2026-09-05",
                "link": f"https://example.eu/news/{i}",
                "type": "official notice",
                "source_tier": "Tier 1",
                "eu_relevance": "direct",
                "strand": "A",
            })
        old_floor = scan.DATE_FLOOR
        scan.DATE_FLOOR = scan.dt.date(2026, 5, 6)
        try:
            state = {"citation_snowball_seed_cursor": 0}
            first = scan._snowball_seed_pool({"strand_a": items}, [], state)
            second = scan._snowball_seed_pool({"strand_a": items}, [], state)
        finally:
            scan.DATE_FLOOR = old_floor
        self.assertTrue(first)
        self.assertTrue(all(scan._snowball_seed_doi(x) for x in first))
        self.assertTrue(all("announcement" not in x["title"].lower() for x in first))
        self.assertNotEqual({x["title"] for x in first}, {x["title"] for x in second})

    def test_budget_and_low_yield_controller_are_bounded(self):
        cfg = scan.CONFIG
        available = int(cfg["scan_budget_seconds"]) - int(cfg["low_yield_reserved_seconds"]) - int(cfg["network_reserve_seconds"])
        self.assertLessEqual(int(cfg["openalex_stage_seconds"]), available)
        self.assertLessEqual(int(cfg["crossref_stage_seconds"]), available)
        self.assertLessEqual(int(cfg["institution_stage_seconds"]), available)
        self.assertLessEqual(int(cfg["low_yield_reserved_seconds"]), 300)
        self.assertLessEqual(int(cfg["low_yield_fresh_rotation_max_waves"]), 2)
        self.assertFalse(cfg.get("legacy_a_recall_recovery_enabled"))

    def test_priority_journal_depth_contains_flagship_ri_venues(self):
        depth = set(scan.CONFIG.get("journal_depth_watchlist", []))
        for journal in (
            "Research Policy",
            "Technological Forecasting and Social Change",
            "Futures",
            "Technology in Society",
        ):
            self.assertIn(journal, depth)

    def test_workflow_contract_is_browser_upload_safe(self):
        # The release package is verified separately with check_workflow_contract.py --strict.
        # This regression deliberately must *not* kill a live scan when GitHub's browser
        # uploader leaves hidden .github/workflows YAML at the recognized legacy revision.
        # That exact deployment mismatch caused several pre-scan failures in earlier builds.
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_workflow_contract.py")],
            cwd=ROOT, text=True, capture_output=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        main = (ROOT / ".github/workflows/radar-scan.yml").read_text(encoding="utf-8")
        preferred = (
            "cron: '17 0,4,8,12,16,20 * * *'" in main
            and "group: ri-research-scanners" in main
            and "age_hours >= 6.0" not in main
        )
        if preferred:
            self.assertNotIn("Launch one fresh 20-minute rescue scan", main)
        else:
            guard = (ROOT / "scripts/scanner_run_guard.py").read_text(encoding="utf-8")
            checker = (ROOT / "scripts/check_workflow_contract.py").read_text(encoding="utf-8")
            self.assertIn("def defer_if_peer_scanner_active", guard)
            self.assertIn("Compatibility mode: workflow mismatches are warnings", checker)


if __name__ == "__main__":
    unittest.main()
