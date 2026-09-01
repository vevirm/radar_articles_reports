from pathlib import Path
import importlib.util
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "radar-scan.yml"
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

    def test_scanner_output_is_isolated_to_radar_json(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("radar.json is the ONLY persistent output of the main scanner", text)
        self.assertIn("git diff --name-only -- . ':!radar.json'", text)
        self.assertIn("grep -vx 'radar.json'", text)
        self.assertIn("Could not isolate scanner output safely. Refusing to save.", text)
        self.assertIn("git add -- radar.json", text)

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
