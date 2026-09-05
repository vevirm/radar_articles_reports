import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = ROOT / "scripts" / "scanner_run_guard.py"
spec = importlib.util.spec_from_file_location("scanner_guard_v172031", GUARD_PATH)
guard = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = guard
spec.loader.exec_module(guard)


class UploadIsDeploymentOnlyTests(unittest.TestCase):
    def test_github_push_is_deployment_only(self):
        env = {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "push"}
        with patch.dict(os.environ, env, clear=True):
            self.assertTrue(guard.deployment_only_push_event())

    def test_schedule_and_manual_dispatch_are_real_scans(self):
        for event in ("schedule", "workflow_dispatch"):
            with self.subTest(event=event):
                with patch.dict(os.environ, {"GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": event}, clear=True):
                    self.assertFalse(guard.deployment_only_push_event())

    def test_local_execution_is_not_suppressed(self):
        with patch.dict(os.environ, {"GITHUB_EVENT_NAME": "push"}, clear=True):
            self.assertFalse(guard.deployment_only_push_event())

    def test_visible_scanners_check_push_before_peer_guard(self):
        main = (ROOT / "scripts" / "scan_radar.py").read_text(encoding="utf-8")
        hist = (ROOT / "historical" / "scan_historical.py").read_text(encoding="utf-8")
        self.assertLess(main.rfind("if deployment_only_push_event():"), main.rfind('if defer_if_peer_scanner_active("main"'))
        self.assertLess(hist.rfind("if deployment_only_push_event():"), hist.rfind('if defer_if_peer_scanner_active("historical"'))

    def test_current_or_stale_workflows_are_safe_on_push(self):
        main = (ROOT / ".github" / "workflows" / "radar-scan.yml").read_text(encoding="utf-8")
        hist = (ROOT / ".github" / "workflows" / "historical-scan.yml").read_text(encoding="utf-8")
        if "cron: '17 0,4,8,12,16,20 * * *'" in main:
            self.assertNotIn("  push:", main)
        else:
            # Browser bulk uploads can leave the hidden old workflow untouched.
            # The visible scanner guard above is what makes that deployment safe.
            self.assertIn("  push:", main)
        if "cron: '53 6 * * *'" in hist:
            self.assertNotIn("  push:", hist)
        else:
            self.assertIn("  push:", hist)


if __name__ == "__main__":
    unittest.main()
