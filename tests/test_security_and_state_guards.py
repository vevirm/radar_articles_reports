from pathlib import Path
import importlib.util
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "radar-scan.yml"
HIST_WORKFLOW = ROOT / ".github" / "workflows" / "historical-scan.yml"
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"

spec = importlib.util.spec_from_file_location("radar_scan_security_test_module", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class RepositoryWriteBoundaryTests(unittest.TestCase):
    def test_checkout_does_not_persist_repository_credentials(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("persist-credentials: false", text)
        self.assertIn("Confirm no repository credential is stored before scanning", text)
        self.assertIn("^http\\..*\\.extraheader$", text)

    def test_scanner_output_has_a_safe_write_boundary_with_new_or_legacy_workflow(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("Could not isolate scanner output safely. Refusing to save.", text)
        if "node scripts/generate_stuff_workbook.js" in text:
            self.assertIn("The scanner persists radar.json plus the Stuff technical-ranking workbook", text)
            self.assertIn("':!radar.json' ':!stuff/source_merit_ranking.xlsx'", text)
            self.assertIn("radar.json|stuff/source_merit_ranking", text)
            self.assertIn("git add -- radar.json stuff/source_merit_ranking.xlsx", text)
        else:
            # Legacy hidden workflow: persist radar.json only. Stuff's live browser
            # generator builds the current XLSX from that JSON on demand.
            self.assertIn("radar.json is the ONLY persistent output", text)
            self.assertIn("git add -- radar.json", text)

    def test_main_scanner_has_fixed_four_hour_schedule_or_safe_legacy_compatibility(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        if "cron: '17 0,4,8,12,16,20 * * *'" in text:
            self.assertIn("fixed four-hour scheduled scan", text)
            self.assertNotIn("age_hours >= 6.0", text)
        else:
            self.assertTrue(scan.legacy_workflow_schedule_compatibility_active(text))
            # Compatibility is slot-aligned, not a fixed two-hour offset. A run ending
            # at 20:23 must make the old six-hour gate due exactly at 00:17, while
            # the preceding 23:17 hourly trigger remains below six hours.
            base = scan.dt.datetime(2026, 9, 1, 20, 23, tzinfo=scan.dt.timezone.utc)
            adjusted = scan.scheduler_state_completed_at(base, text)
            self.assertEqual(adjusted.isoformat(), '2026-09-01T18:17:00+00:00')
            self.assertLess((scan.dt.datetime(2026, 9, 1, 23, 17, tzinfo=scan.dt.timezone.utc) - adjusted).total_seconds(), 6 * 3600)
            self.assertEqual((scan.dt.datetime(2026, 9, 2, 0, 17, tzinfo=scan.dt.timezone.utc) - adjusted).total_seconds(), 6 * 3600)

    def test_main_and_historical_are_serialized_across_complete_rescue_cycles(self):
        main = WORKFLOW.read_text(encoding="utf-8")
        hist = HIST_WORKFLOW.read_text(encoding="utf-8")
        shared_lock = all(
            "group: ri-research-scanners" in text and
            "cancel-in-progress: false" in text
            for text in (main, hist)
        )
        self.assertTrue(shared_lock)
        self.assertNotIn("queue: max", main)
        self.assertNotIn("queue: max", hist)
        self.assertIn("cron: '17 0,4,8,12,16,20 * * *'", main)
        self.assertIn("cron: '53 6 * * *'", hist)

        # GitHub's browser bulk uploader can still leave hidden workflow YAML unchanged.
        # Visible scanner code therefore carries a safe fallback: the later legacy
        # workflow run exits before source requests instead of overlapping the peer.
        guard = (ROOT / "scripts" / "scanner_run_guard.py").read_text(encoding="utf-8")
        main_scan = SCAN_PATH.read_text(encoding="utf-8")
        hist_scan = (ROOT / "historical" / "scan_historical.py").read_text(encoding="utf-8")
        self.assertIn("def defer_if_peer_scanner_active", guard)
        self.assertIn("_main_rescue_pending", guard)
        self.assertIn("_historical_rescue_pending", guard)
        self.assertIn('defer_if_peer_scanner_active("main"', main_scan)
        self.assertIn('defer_if_peer_scanner_active("historical"', hist_scan)
        self.assertIn("refresh_window_metadata_after_peer_defer", hist_scan)

    def test_cumulative_retention_is_enforced_in_scanner_even_with_legacy_workflow(self):
        old_a = {"title": "Old accepted A", "date": "2024-01-01", "link": "https://example.org/a"}
        old_b = {"title": "Old accepted B", "date": "2024-01-01", "link": "https://example.org/b"}
        old_f = {"title": "Old frontier", "date": "2024-01-01", "link": "https://example.org/f"}
        data = {"strand_a": [old_a], "strand_b": [old_b], "frontier_evidence": [old_f], "strand_c": []}
        out, removed = scan.prune_public_window(
            data,
            scan.dt.date(2026, 5, 1),
            now=scan.dt.datetime(2026, 9, 1, 16, 0, tzinfo=scan.dt.timezone.utc),
        )
        self.assertEqual(out["strand_a"], [old_a])
        self.assertEqual(out["strand_b"], [old_b])
        self.assertEqual(out["frontier_evidence"], [old_f])
        self.assertEqual(sum(removed.values()), 0)

    def test_shipped_workflow_guards_all_prior_ab_rows_not_only_recent_dates(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        if "previously accepted cumulative item(s)" in text:
            self.assertIn("rolling date windows govern discovery priority, not retention", text)
            self.assertNotIn("still-in-window accepted item(s)", text)

    def test_push_credential_is_added_only_after_scan_and_safety_gate(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        scan_pos = text.index("- name: Run radar scan")
        isolate_pos = text.index("- name: Safety-check and isolate scanner output")
        commit_pos = text.index("- name: Commit fresh results")
        token_pos = text.index("GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}")
        extraheader_pos = text.index("git config --local http.https://github.com/.extraheader")
        self.assertLess(scan_pos, isolate_pos)
        self.assertLess(isolate_pos, commit_pos)
        self.assertGreater(token_pos, isolate_pos)
        self.assertGreater(extraheader_pos, isolate_pos)


class IncrementalStatePreservationTests(unittest.TestCase):
    def test_current_repo_does_not_trigger_full_recall_reset(self):
        previous = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        old = dict(previous.get("scan_state") or {})
        self.assertTrue(old)
        state = scan.initial_scan_state(previous)
        self.assertFalse(state.get("recall_reset_this_run"))
        # Installing this release must preserve the expensive rotation positions.
        for key in (
            "openalex_cursor",
            "crossref_broad_cursor",
            "crossref_priority_cursor",
            "crossref_source_cursor",
            "institution_cursor",
        ):
            self.assertEqual(state.get(key), old.get(key), key)

    def test_recall_profile_was_not_bumped_for_admission_only_change(self):
        config = json.loads((ROOT / "radar_config.json").read_text(encoding="utf-8"))
        previous = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        self.assertEqual(config.get("recall_profile_version"), previous.get("recall_profile_version"))
        self.assertEqual(
            config.get("recall_profile_version"),
            (previous.get("scan_state") or {}).get("recall_profile_version"),
        )


if __name__ == "__main__":
    unittest.main()
