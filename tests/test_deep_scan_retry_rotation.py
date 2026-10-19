from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.deep_scan_work_state import (
    assignment_blocked_keys,
    empty_state,
    fill_lane,
    load_state,
    mark_recovery_failure,
    register_package,
)


class DeepScanRetryRotation(unittest.TestCase):
    def test_reissued_lane_rotates_to_fresh_work(self):
        state = empty_state()
        pending = ["main:old1", "main:old2", "main:fresh1", "main:fresh2"]
        first = fill_lane(state, "A", pending, target_size=2)
        self.assertEqual(first, ["main:old1", "main:old2"])
        register_package(state, "A", "pkg-1", first)

        second = fill_lane(state, "A", pending, target_size=2)
        self.assertEqual(second, ["main:fresh1", "main:fresh2"])

    def test_unanswered_package_issuance_does_not_block_fourth_attempt(self):
        state = empty_state()
        key = "main:stubborn"
        pending = [key]
        for n in range(1, 4):
            assigned = fill_lane(state, "A", pending, target_size=1)
            self.assertEqual(assigned, [key])
            register_package(state, "A", f"pkg-{n}", assigned)
        self.assertNotIn(key, assignment_blocked_keys(state))
        self.assertEqual(fill_lane(state, "A", pending, target_size=1), [key])

    def test_first_validated_failure_after_three_unanswered_packages_is_first_pass(self):
        state = empty_state()
        key = "main:stubborn"
        for n in range(1, 4):
            register_package(state, "A", f"pkg-{n}", [key])
        status = mark_recovery_failure(
            state, key, "pkg-3", reason="still inaccessible", verification={}
        )
        self.assertEqual(status, "recovery_retry")
        self.assertEqual(state["records"][key]["recovery_attempts"], 1)

    def test_saturated_backlog_refills_both_workers_without_overlap(self):
        state = empty_state()
        pending = [f"main:backlog-{n}" for n in range(22)]
        # All candidates have been packaged several times, but none has a
        # validated failed retrieval ladder or authoritative Deep Scan decision.
        for key in pending:
            state["records"][key] = {"status": "assigned", "scan_package_attempts": 6}
        state["lanes"]["SINGLE"] = {"assigned": pending[:2]}
        a = fill_lane(state, "A", pending, target_size=8)
        b = fill_lane(state, "B", pending, target_size=8)
        self.assertEqual(len(a), 8)
        self.assertEqual(len(b), 8)
        self.assertFalse(set(a) & set(b))
        self.assertFalse(set(a + b) & set(pending[:2]))

    def test_three_real_failed_recovery_passes_still_require_hands_on(self):
        state = empty_state()
        key = "main:needs-source"
        for n in range(3):
            status = mark_recovery_failure(
                state, key, f"pkg-{n}", reason="audited recovery exhausted", verification={}
            )
        self.assertEqual(status, "needs_manual_verification")
        self.assertIn(key, assignment_blocked_keys(state))
        self.assertEqual(fill_lane(state, "A", [key], target_size=1), [])

    def test_old_ledger_backfills_distinct_package_memberships_without_blocking(self):
        key = "historical:old"
        raw = empty_state()
        raw["records"][key] = {"status": "recovery_retry", "recovery_attempts": 1}
        for n in range(1, 4):
            raw["packages"][f"pkg-{n}"] = {"lane": "A", "record_keys": [key]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            state = load_state(path)
        self.assertEqual(state["records"][key]["scan_package_attempts"], 3)
        self.assertNotIn(key, assignment_blocked_keys(state))


if __name__ == "__main__":
    unittest.main()
