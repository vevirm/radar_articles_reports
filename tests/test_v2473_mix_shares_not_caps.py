"""Regression tests: 8:1:3 is a relative publication ratio, not fixed 8/1/3 caps."""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_v2475_ratio", SCAN)
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


class V2475RelativeMixRelease(unittest.TestCase):
    def test_candidate_gate_does_not_throw_away_valid_a_or_b(self):
        rows = [ab(i, "A") for i in range(12)] + [ab(100+i, "B") for i in range(3)]
        selected, stats = S.select_hard_new_ab_mix(rows)
        self.assertEqual(len(selected), 15)
        self.assertEqual(stats["selected_a"], 12)
        self.assertEqual(stats["selected_b"], 3)

    def test_candidate_gate_does_not_throw_away_valid_c_before_relative_release(self):
        current = [c(i) for i in range(5)]
        selected, stats = S.select_hard_new_c_mix(current, [])
        self.assertEqual(len(selected), 5)
        self.assertEqual(stats["selected_c"], 5)
        self.assertEqual(stats["suppressed_c"], 0)

    def test_no_c_floor_or_rescue_is_configured(self):
        self.assertEqual(int(S.CONFIG.get("c_min_new_per_successful_scan", -1)), 0)
        self.assertFalse(bool(S.CONFIG.get("c_floor_rescue_enabled", True)))
        self.assertEqual(S.CONFIG.get("target_item_mix_mode"), "relative_release")

    def test_relative_mix_weights_are_8_1_3(self):
        self.assertEqual(S.target_mix_weights(), {"A": 8, "B": 1, "C": 3})

    def test_one_a_cannot_release_a_c_flood(self):
        published = {"A": 0, "B": 0, "C": 0}
        b_slots, b_target, projected_a = S.relative_mix_release_slots(published, 1, "B")
        c_slots, c_target, projected_a_c = S.relative_mix_release_slots(published, 1, "C")
        self.assertEqual(projected_a, 1)
        self.assertEqual(projected_a_c, 1)
        # One small-sample pulse avoids starvation; 25/26 C can never be released here.
        self.assertEqual((b_slots, b_target), (1, 1))
        self.assertEqual((c_slots, c_target), (1, 1))

    def test_eight_a_resolves_to_one_b_three_c(self):
        # Assume the initial anti-starvation pulse has already published B=1/C=1.
        published = {"A": 1, "B": 1, "C": 1}
        b_slots, b_target, projected_a = S.relative_mix_release_slots(published, 7, "B")
        c_slots, c_target, _ = S.relative_mix_release_slots(published, 7, "C")
        self.assertEqual(projected_a, 8)
        self.assertEqual(b_target, 1)
        self.assertEqual(c_target, 3)
        self.assertEqual(b_slots, 0)
        self.assertEqual(c_slots, 2)

    def test_ratio_scales_not_fixed_ceiling(self):
        published = {"A": 8, "B": 1, "C": 3}
        b_slots, b_target, projected_a = S.relative_mix_release_slots(published, 72, "B")
        c_slots, c_target, _ = S.relative_mix_release_slots(published, 72, "C")
        self.assertEqual(projected_a, 80)
        self.assertEqual((b_target, c_target), (10, 30))
        self.assertEqual((b_slots, c_slots), (9, 27))

    def test_overrepresented_c_loses_bonus_searches(self):
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
