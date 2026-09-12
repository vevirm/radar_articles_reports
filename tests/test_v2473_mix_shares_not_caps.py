"""Regression tests: 8:1:3 is a soft publication share, never an absolute cap/floor."""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_v2473", SCAN)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)


def ab(i, strand):
    return {
        "title": f"Eligible {strand} item {i}",
        "strand": strand,
        "date": "2026-09-10",
        "link": f"https://example.org/{strand.lower()}/{i}",
        "source": "Test",
    }


def c(i, *, kind="policy / strategy", route="event", status="DONE"):
    labels = ["quantum regulation", "chip investment", "research security", "talent programme", "space infrastructure", "biotech funding"]
    label = labels[i % len(labels)]
    headline = f"European {label} change {i}"
    return {
        "headline": headline,
        "what": headline,
        "core_message": headline,
        "date": f"2026-09-{10+i:02d}",
        "c_event_date": f"2026-09-{10+i:02d}",
        "signal_kind": kind,
        "event_status": status,
        "c_admission_route": route,
        "source": "Test",
        "source_domain": "example.org",
        "link": f"https://example.org/c/{i}",
        "anchor_status": "anchored",
    }


class V2473SoftMixShares(unittest.TestCase):
    def test_more_than_eight_a_and_one_b_are_not_suppressed(self):
        rows = [ab(i, "A") for i in range(12)] + [ab(100+i, "B") for i in range(3)]
        selected, stats = S.select_hard_new_ab_mix(rows)
        self.assertEqual(len(selected), 15)
        self.assertEqual(stats["selected_a"], 12)
        self.assertEqual(stats["selected_b"], 3)
        self.assertEqual(stats["suppressed_a"], 0)
        self.assertEqual(stats["suppressed_b"], 0)

    def test_more_than_three_distinct_c_are_not_suppressed(self):
        current = [c(i) for i in range(5)]
        selected, stats = S.select_hard_new_c_mix(current, [])
        self.assertEqual(len(selected), 5)
        self.assertEqual(stats["selected_c"], 5)
        self.assertEqual(stats["suppressed_c"], 0)

    def test_no_c_floor_or_quota_rescue_is_configured(self):
        self.assertEqual(int(S.CONFIG.get("c_min_new_per_successful_scan", -1)), 0)
        self.assertFalse(bool(S.CONFIG.get("c_floor_rescue_enabled", True)))
        self.assertEqual(S.CONFIG.get("target_item_mix_mode"), "soft_shares")

    def test_relative_mix_weights_are_8_1_3(self):
        self.assertEqual(S.target_mix_weights(), {"A": 8, "B": 1, "C": 3})

    def test_overrepresented_c_loses_bonus_searches_not_publications(self):
        state = S.relative_mix_discovery_state({"A": 3, "B": 0, "C": 11})
        self.assertTrue(state["under_target"]["A"], state)
        self.assertTrue(state["under_target"]["B"], state)
        self.assertFalse(state["under_target"]["C"], state)

    def test_weighted_ab_query_order_is_relative_not_truncating(self):
        a = [f"A{i}" for i in range(16)]
        b = ["B0", "B1"]
        bank = S.weighted_strand_query_bank(a, b)
        self.assertEqual(set(bank), set(a + b))
        self.assertEqual(len(bank), 18)
        self.assertEqual(bank[8], "B0")
        self.assertEqual(bank[17], "B1")


if __name__ == "__main__":
    unittest.main()
