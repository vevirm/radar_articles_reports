import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("scan_radar_recovery", ROOT / "scripts" / "scan_radar.py")
scan = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(scan)


class CorpusRecoveryTests(unittest.TestCase):
    def test_valid_saved_radar_accepts_populated_b(self):
        self.assertTrue(scan._valid_saved_radar({"first_scan_complete": False, "strand_a": [], "strand_b": [{"title": "x"}]}))

    def test_valid_saved_radar_rejects_pending_empty_template(self):
        self.assertFalse(scan._valid_saved_radar({"last_updated": None, "first_scan_complete": False, "strand_a": [], "strand_b": []}))

    def test_recovery_prefers_larger_cumulative_corpus(self):
        revs = subprocess.CompletedProcess(args=[], returncode=0, stdout="new\nold\n", stderr="")
        new = {"first_scan_complete": True, "strand_a": [{"title": "a"}], "strand_b": []}
        old = {"first_scan_complete": True, "strand_a": [{"title": "a"}], "strand_b": [{"title": "b1"}, {"title": "b2"}]}
        shows = {
            "new:radar.json": subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(new), stderr=""),
            "old:radar.json": subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(old), stderr=""),
        }
        def fake_run(args, **kwargs):
            if args[:2] == ["git", "rev-list"]:
                return revs
            if args[:2] == ["git", "show"]:
                return shows[args[2]]
            raise AssertionError(args)
        with mock.patch.object(scan.subprocess, "run", side_effect=fake_run):
            recovered = scan._recover_radar_from_git()
        self.assertEqual(len(recovered["strand_b"]), 2)


if __name__ == "__main__":
    unittest.main()
