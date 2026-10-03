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

    def test_fourth_package_issuance_is_blocked(self):
        state = empty_state()
        key = "main:stubborn"
        pending = [key]
        for n in range(1, 4):
            assigned = fill_lane(state, "A", pending, target_size=1)
            self.assertEqual(assigned, [key])
            register_package(state, "A", f"pkg-{n}", assigned)
        self.assertIn(key, assignment_blocked_keys(state))
        self.assertEqual(fill_lane(state, "A", pending, target_size=1), [])

    def test_failure_from_third_issued_package_is_terminal(self):
        state = empty_state()
        key = "main:stubborn"
        for n in range(1, 4):
            register_package(state, "A", f"pkg-{n}", [key])
        status = mark_recovery_failure(
            state, key, "pkg-3", reason="still inaccessible", verification={}
        )
        self.assertEqual(status, "needs_manual_verification")
        self.assertEqual(state["records"][key]["recovery_attempts"], 3)

    def test_old_ledger_backfills_distinct_package_memberships(self):
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
        self.assertIn(key, assignment_blocked_keys(state))


if __name__ == "__main__":
    unittest.main()
