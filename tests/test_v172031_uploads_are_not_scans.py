import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = ROOT / "scripts" / "scanner_run_guard.py"
spec = importlib.util.spec_from_file_location("scanner_guard_v172032", GUARD_PATH)
guard = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = guard
spec.loader.exec_module(guard)


class UploadTriggerRoleTests(unittest.TestCase):
    def test_github_push_is_real_main_scan_but_not_historical_scan(self):
        env = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "push"}
        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(guard.deployment_only_push_event("main"))
            self.assertTrue(guard.deployment_only_push_event("historical"))

    def test_schedule_and_manual_dispatch_are_real_scans_for_both_roles(self):
        for event in ("schedule", "workflow_dispatch"):
            for role in ("main", "historical"):
                with self.subTest(event=event, role=role):
                    with patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": event}, clear=True):
                        self.assertFalse(guard.deployment_only_push_event(role))

    def test_local_execution_is_not_suppressed(self):
        with patch.dict(os.environ, {"GITHUB_EVENT_NAME": "push"}, clear=True):
            self.assertFalse(guard.deployment_only_push_event("main"))
            self.assertFalse(guard.deployment_only_push_event("historical"))

    def test_visible_scanners_use_role_aware_push_guard_before_peer_guard(self):
        main = (ROOT / "scripts" / "scan_radar.py").read_text(encoding="utf-8")
        hist = (ROOT / "historical" / "scan_historical.py").read_text(encoding="utf-8")
        self.assertIn('deployment_only_push_event("main")', main)
        self.assertIn('deployment_only_push_event("historical")', hist)
        self.assertLess(main.rfind('deployment_only_push_event("main")'), main.rfind('defer_if_peer_scanner_active("main"'))
        self.assertLess(hist.rfind('deployment_only_push_event("historical")'), hist.rfind('defer_if_peer_scanner_active("historical"'))

    def test_current_or_stale_main_workflow_allows_upload_scan(self):
        main = (ROOT / ".github" / "workflows" / "radar-scan.yml").read_text(encoding="utf-8")
        self.assertIn("  push:", main)
        if "cron: '17 0,4,8,12,16,20 * * *'" in main:
            # Current workflow: scanner output is ignored so its own radar.json commit
            # cannot recursively launch another discovery cycle.
            self.assertIn("      - radar.json", main)
        else:
            # Stale browser-uploaded workflow: non-schedule events already set run=true;
            # the role-aware Python guard must therefore allow Main push discovery.
            self.assertIn('if [[ "$EVENT_NAME" != "schedule" ]]', main)

    def test_current_historical_workflow_does_not_scan_on_whole_repo_upload(self):
        hist = (ROOT / ".github" / "workflows" / "historical-scan.yml").read_text(encoding="utf-8")
        if "cron: '53 6 * * *'" in hist:
            self.assertNotIn("  push:", hist)
        else:
            # A stale hidden workflow may still contain push; the role-aware Python guard
            # makes that invocation deployment-only before any historical source request.
            self.assertIn("  push:", hist)

    def test_stale_historical_push_cannot_block_main_upload_scan(self):
        root = ROOT
        active = [
            {
                "id": 100,
                "path": "/.github/workflows/historical-scan.yml",
                "event": "push",
                "run_started_at": "2026-09-05T10:00:00Z",
            },
            {
                "id": 101,
                "path": "/.github/workflows/radar-scan.yml",
                "event": "push",
                "run_started_at": "2026-09-05T10:00:01Z",
            },
        ]
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_REPOSITORY": "example/repo",
            "GITHUB_RUN_ID": "101",
        }
        with patch.dict(os.environ, env, clear=True), patch.object(guard, "_active_scanner_runs", return_value=active):
            self.assertFalse(guard.defer_if_peer_scanner_active("main", root))

    def test_real_historical_schedule_still_blocks_main_when_it_owns_slot(self):
        root = ROOT
        active = [
            {
                "id": 100,
                "path": "/.github/workflows/historical-scan.yml",
                "event": "schedule",
                "run_started_at": "2026-09-05T10:00:00Z",
            },
            {
                "id": 101,
                "path": "/.github/workflows/radar-scan.yml",
                "event": "push",
                "run_started_at": "2026-09-05T10:00:01Z",
            },
        ]
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_REPOSITORY": "example/repo",
            "GITHUB_RUN_ID": "101",
        }
        with patch.dict(os.environ, env, clear=True), patch.object(guard, "_active_scanner_runs", return_value=active):
            self.assertTrue(guard.defer_if_peer_scanner_active("main", root))


if __name__ == "__main__":
    unittest.main()
