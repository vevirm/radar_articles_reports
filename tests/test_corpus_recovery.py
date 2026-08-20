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


    def test_valid_saved_radar_accepts_c_only_history(self):
        self.assertTrue(scan._valid_saved_radar({"strand_a": [], "strand_b": [], "strand_c": [{"headline": "x"}]}))

    def test_ab_merge_does_not_mark_rediscovery_new(self):
        old = [{"title": "Existing report", "link": "https://example.test/a", "strand": "A", "date": "2026-08-18", "first_seen": "2026-08-18T00:00Z"}]
        new = [{"title": "Existing report", "link": "https://example.test/a", "strand": "A", "date": "2026-08-18", "summary": "refreshed"}]
        merged = scan.merge_corpus(old, new, "A", "2026-08-20T00:00Z")
        self.assertEqual(len(merged), 1)
        self.assertFalse(merged[0]["new_this_scan"])
        self.assertEqual(merged[0]["first_seen"], "2026-08-18T00:00Z")

    def test_history_union_restores_signal_lost_by_previous_scan(self):
        current = {
            "first_scan_complete": True,
            "strand_a": [], "strand_b": [],
            "strand_c": [{"headline": "Today signal", "source": "Reuters", "date": "2026-08-20T08:00Z"}],
        }
        older = {
            "first_scan_complete": True,
            "strand_a": [], "strand_b": [],
            "strand_c": [
                {"headline": "Today signal", "source": "Reuters", "date": "2026-08-20T08:00Z"},
                {"headline": "Yesterday signal", "source": "Politico Europe", "date": "2026-08-19T08:00Z"},
            ],
        }
        revs = subprocess.CompletedProcess(args=[], returncode=0, stdout="old\n", stderr="")
        show = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(older), stderr="")
        def fake_run(args, **kwargs):
            if args[:2] == ["git", "rev-list"]:
                return revs
            if args[:2] == ["git", "show"]:
                return show
            raise AssertionError(args)
        with mock.patch.object(scan.subprocess, "run", side_effect=fake_run):
            restored = scan._augment_with_git_history(current)
        self.assertEqual({x["headline"] for x in restored["strand_c"]}, {"Today signal", "Yesterday signal"})

    def test_weak_signals_accumulate_and_dedupe(self):
        old = [{"headline": "Earlier weak signal", "source": "Reuters", "date": "2026-08-19T09:00Z", "link": "old", "first_seen": "2026-08-19T10:00Z"}]
        current = [
            {"headline": "Earlier weak signal", "source": "Reuters", "date": "2026-08-19T09:00Z", "link": "old"},
            {"headline": "New weak signal", "source": "Politico Europe", "date": "2026-08-20T08:00Z", "link": "new"},
        ]
        merged = scan.merge_signal_corpus(old, current, "2026-08-20T08:30Z")
        self.assertEqual(len(merged), 2)
        by_head = {x["headline"]: x for x in merged}
        self.assertFalse(by_head["Earlier weak signal"]["new_this_scan"])
        self.assertEqual(by_head["Earlier weak signal"]["first_seen"], "2026-08-19T10:00Z")
        self.assertTrue(by_head["New weak signal"]["new_this_scan"])

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
