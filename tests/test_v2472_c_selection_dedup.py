"""Regression tests for v24.7.2 Strand-C event deduplication and final ranking."""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_v2472", SCAN)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)


def c(headline, date, *, kind="policy / strategy", status="DONE", route="event", source="Test", anchor="anchored"):
    domains = {
        "Euractiv": "euractiv.com",
        "Research Professional News": "researchprofessionalnews.com",
        "The Irish Times": "irishtimes.com",
        "Sifted": "sifted.eu",
        "Tech Policy Press": "techpolicy.press",
        "Science|Business": "sciencebusiness.net",
        "Le Monde": "lemonde.fr",
    }
    domain = domains.get(source, "example.test")
    return {
        "headline": headline,
        "what": headline,
        "core_message": headline,
        "date": date,
        "c_event_date": date[:10],
        "signal_kind": kind,
        "event_status": status,
        "c_admission_route": route,
        "source": source,
        "source_domain": domain,
        "link": f"https://{domain}/{abs(hash((headline, source)))}/",
        "anchor_status": anchor,
    }


class V2472CSelectionDedup(unittest.TestCase):
    def test_japan_horizon_cross_publisher_rewrite_is_same_event(self):
        a = c("Japan formally joins Horizon Europe as associated country", "2026-07-30")
        b = c("Japan and EU sign off Horizon Europe association", "2026-07-30")
        self.assertTrue(S.signals_near_duplicate(a, b))

    def test_ai_gigafactory_cross_publisher_launch_is_same_event_within_week(self):
        a = c("EU opens applications for €10bn AI gigafactory scheme", "2026-07-30", kind="investment / capacity")
        b = c("Europe commits €5 billion to fund seven AI megafactories and catch up with the US and China", "2026-07-31", kind="investment / capacity")
        self.assertTrue(S.signals_near_duplicate(a, b))

    def test_ai_gigafactory_later_material_stage_is_not_auto_collapsed(self):
        a = c("EU opens applications for €10bn AI gigafactory scheme", "2026-07-30", kind="investment / capacity")
        b = c("EU selects first AI gigafactory sites for construction", "2026-09-30", kind="investment / capacity")
        self.assertFalse(S.signals_near_duplicate(a, b))

    def test_final_selection_excludes_existing_event_rewrites_and_prefers_concrete_events(self):
        previous = [
            c("Japan and EU sign off Horizon Europe association", "2026-07-30", kind="cooperation / alignment"),
            c("Europe commits €5 billion to fund seven AI megafactories and catch up with the US and China", "2026-07-31", kind="investment / capacity"),
        ]
        current = [
            c("Japan formally joins Horizon Europe as associated country", "2026-07-30", kind="cooperation / alignment", source="Research Professional News"),
            c("EU opens applications for €10bn AI gigafactory scheme", "2026-07-30", kind="investment / capacity", source="Sifted"),
            c("The EU's AI Boom Could Undermine its Own Chip Strategy", "2026-09-10", kind="analysis / interpretation", status="INTERPRETIVE", route="analysis", source="Tech Policy Press"),
            c("EU's first quantum tech regulation delayed by six months", "2026-09-10", kind="policy / strategy", source="Euractiv"),
            c("EU-China research cooperation limited to targeted areas", "2026-09-10", kind="restriction / security", source="Research Professional News"),
            c("Intel to invest €5bn in Leixlip campus on next-generation chips to power AI", "2026-09-09", kind="investment / capacity", source="The Irish Times"),
        ]
        selected, stats = S.select_hard_new_c_mix(current, previous)
        headlines = [x["headline"] for x in selected]
        self.assertNotIn("Japan formally joins Horizon Europe as associated country", headlines)
        self.assertNotIn("EU opens applications for €10bn AI gigafactory scheme", headlines)
        self.assertEqual(headlines, [
            "EU's first quantum tech regulation delayed by six months",
            "EU-China research cooperation limited to targeted areas",
            "Intel to invest €5bn in Leixlip campus on next-generation chips to power AI",
            "The EU's AI Boom Could Undermine its Own Chip Strategy",
        ])
        self.assertEqual(stats["selected_c"], 4)
        self.assertEqual(stats["suppressed_c"], 0)

    def test_repaired_good_signals_ignore_legacy_retirement_tombstones(self):
        row = c("EU-China research cooperation limited to ‘targeted areas’", "2026-09-10")
        data = {"retired_signal_headlines": ["EU-China research cooperation limited to ‘targeted areas’"]}
        self.assertFalse(S.signal_is_retired(row, data))


if __name__ == "__main__":
    unittest.main()
