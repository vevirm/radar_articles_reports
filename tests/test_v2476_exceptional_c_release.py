"""Regression tests for the v24.7.6 strict exceptional-C urgency bypass."""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_v2476_exceptional_c", SCAN)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)


def c_row(
    headline: str,
    *,
    source: str = "Research Professional News",
    domain: str = "researchprofessionalnews.com",
    status: str = "DONE",
    rel: str = "direct",
    kind: str = "policy / strategy",
    route: str = "event",
    n: int = 1,
):
    return {
        "headline": headline,
        "what": headline,
        "core_message": headline,
        "source": source,
        "source_domain": domain,
        "date": f"2026-09-{10+n:02d}",
        "c_event_date": f"2026-09-{10+n:02d}",
        "event_status": status,
        "realisation_status": "delivered" if status == "OBSERVED" else "announced",
        "signal_kind": kind,
        "signal_type": "instantiates",
        "c_admission_route": route,
        "c_admission_basis": "trusted_europe_publication",
        "eu_relevance": rel,
        "eu_evidence": ["EU"],
        "watch_theme": "critical and emerging technologies",
        "anchor_status": "anchored",
        "analytical_weight": 0.3,
        "link": f"https://example.org/c/{n}",
    }


class V2476ExceptionalCRelease(unittest.TestCase):
    def test_major_horizon_access_change_is_exceptional(self):
        row = c_row("Japan formally joins Horizon Europe as associated country")
        decision = S.exceptional_c_release_decision(row)
        self.assertTrue(decision["eligible"], decision)
        self.assertEqual(decision["reason"], "major_research_programme_access_changed")

    def test_billion_scale_realised_strategic_capital_move_is_exceptional(self):
        row = c_row(
            "French start-up Mistral AI raises €3 billion in Samsung-led round",
            source="Euronews",
            domain="euronews.com",
            rel="member_state",
        )
        decision = S.exceptional_c_release_decision(row)
        self.assertTrue(decision["eligible"], decision)
        self.assertEqual(decision["reason"], "major_strategic_capital_or_control_change")

    def test_proposal_or_open_call_does_not_bypass(self):
        row = c_row(
            "EU opens call for seven gigafactories to train AI technologies",
            source="Euronews",
            domain="euronews.com",
        )
        decision = S.exceptional_c_release_decision(row)
        self.assertFalse(decision["eligible"], decision)

    def test_adopted_proposal_is_not_mistaken_for_binding_rule(self):
        row = c_row(
            "Commission adopts proposal for new EU AI research security regulation",
            source="Politico Europe",
            domain="politico.eu",
        )
        decision = S.exceptional_c_release_decision(row)
        self.assertFalse(decision["eligible"], decision)

    def test_launch_of_future_build_programme_is_not_operational_capability(self):
        row = c_row(
            "EU launches seven AI factories to build new compute capacity",
            source="Politico Europe",
            domain="politico.eu",
        )
        decision = S.exceptional_c_release_decision(row)
        self.assertFalse(decision["eligible"], decision)

    def test_forecasted_investment_need_does_not_bypass(self):
        row = c_row(
            "€14 Trillion in Investment Needed to Advance Europe’s Strategic Autonomy by 2035",
            source="Bloomberg",
            domain="bloomberg.com",
            status="COMMITTED",
            rel="supported",
            kind="investment / capacity",
        )
        decision = S.exceptional_c_release_decision(row)
        self.assertFalse(decision["eligible"], decision)

    def test_warning_or_commentary_does_not_bypass(self):
        row = c_row(
            "Belgium's medicine price cuts risk its own innovation, economist warns",
            source="Euractiv",
            domain="euractiv.com",
            rel="member_state",
        )
        decision = S.exceptional_c_release_decision(row)
        self.assertFalse(decision["eligible"], decision)

    def test_ordinary_valid_c_still_waits_when_there_are_no_slots(self):
        ordinary = c_row("Europe discusses new approaches to quantum research cooperation")
        selected, deferred, stats = S.select_relative_c_release(
            [ordinary], {"A": 3, "B": 1, "C": 1}, 0
        )
        self.assertEqual(stats["release_slots"], 0)
        self.assertEqual(selected, [])
        self.assertEqual(len(deferred), 1)
        self.assertEqual(stats["exceptional_ratio_bypass_c"], 0)

    def test_exceptional_event_publishes_even_with_zero_normal_slots(self):
        urgent = c_row("Japan formally joins Horizon Europe as associated country")
        selected, deferred, stats = S.select_relative_c_release(
            [urgent], {"A": 3, "B": 1, "C": 1}, 0
        )
        self.assertEqual(stats["release_slots"], 0)
        self.assertEqual(len(selected), 1)
        self.assertEqual(deferred, [])
        self.assertTrue(selected[0]["exceptional_c_release"])
        self.assertTrue(selected[0]["exceptional_c_ratio_bypass"])
        self.assertEqual(stats["exceptional_ratio_bypass_c"], 1)
        # Urgency changes timing only; the weak-signal analytical weight is untouched.
        self.assertEqual(selected[0]["analytical_weight"], 0.3)

    def test_exceptional_event_uses_an_available_normal_slot_before_bypassing(self):
        ordinary = c_row("Europe reports a new AI research cooperation initiative", n=2)
        urgent = c_row("Japan formally joins Horizon Europe as associated country", n=3)
        selected, deferred, stats = S.select_relative_c_release(
            [ordinary, urgent], {"A": 1, "B": 1, "C": 0}, 0
        )
        self.assertEqual(stats["release_slots"], 1)
        self.assertEqual(len(selected), 1)
        self.assertTrue(selected[0]["exceptional_c_release"])
        self.assertFalse(selected[0]["exceptional_c_ratio_bypass"])
        self.assertEqual(stats["exceptional_ratio_bypass_c"], 0)
        self.assertEqual(len(deferred), 1)

    def test_multiple_exceptional_events_can_all_surface_but_create_ratio_debt(self):
        horizon = c_row("Japan formally joins Horizon Europe as associated country", n=4)
        capital = c_row(
            "French start-up Mistral AI raises €3 billion in Samsung-led round",
            source="Euronews",
            domain="euronews.com",
            rel="member_state",
            n=5,
        )
        selected, deferred, stats = S.select_relative_c_release(
            [horizon, capital], {"A": 3, "B": 1, "C": 1}, 0
        )
        self.assertEqual(len(selected), 2)
        self.assertEqual(stats["exceptional_ratio_bypass_c"], 2)
        self.assertEqual(deferred, [])
        # Once both are counted in the ledger, even A=8 supports only C=3 total,
        # so no ordinary C slot reopens yet.
        c_slots, c_target, projected_a = S.relative_mix_release_slots(
            {"A": 3, "B": 1, "C": 3}, 5, "C"
        )
        self.assertEqual(projected_a, 8)
        self.assertEqual(c_target, 3)
        self.assertEqual(c_slots, 0)

    def test_untrusted_source_cannot_use_exception(self):
        row = c_row(
            "EU formally adopts a binding quantum export control",
            source="Random Blog",
            domain="random.example",
        )
        decision = S.exceptional_c_release_decision(row)
        self.assertFalse(decision["eligible"], decision)
        self.assertEqual(decision["reason"], "source_not_strong_enough")


if __name__ == "__main__":
    unittest.main()
