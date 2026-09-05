import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_scan_v172039", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class PrecisionAndLowYieldMethodTests(unittest.TestCase):
    def test_generic_access_and_capabilities_do_not_create_geopolitics(self):
        title = "Regional knowledge base and firm efficiency: Evidence from start-ups and fast-growing medium-sized firms"
        abstract = (
            "Using micro-level data across European regions, we examine production efficiency. "
            "The study evaluates how access to regional knowledge and technological capabilities "
            "influences firm performance and innovation strategies."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertNotEqual(ev.get("a_route"), "triangulated-strategic-context")
        self.assertEqual(ev.get("geo_evidence"), [])

    def test_real_external_dependency_can_still_triangulate(self):
        title = "European research infrastructure dependence on foreign suppliers"
        abstract = (
            "European research infrastructures rely on foreign suppliers for specialised components. "
            "This external supplier dependence creates a capability gap and threatens access to critical "
            "scientific equipment needed for European research."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertTrue(ev["a_pass"])
        self.assertIn(ev.get("a_route"), {"triangulated-strategic-context", "explicit-geopolitics"})

    def test_live_false_positive_is_retired(self):
        row = {
            "title": "Regional knowledge base and firm efficiency: Evidence from start-ups and fast-growing medium-sized firms",
            "summary": "European regions, technological capabilities and firm efficiency.",
            "type": "peer-reviewed article",
            "source_tier": "Tier 2 comparable",
        }
        self.assertFalse(scan.final_ab_candidate_worthiness(row))

    def test_low_yield_adjacency_runs_before_extra_depth_waves(self):
        src = SCAN_PATH.read_text(encoding="utf-8")
        adjacency = src.index("V17.20.39: try adjacency BEFORE the extra broad/depth waves")
        waves = src.index("fresh_min_remaining = max", adjacency)
        self.assertLess(adjacency, waves)

    def test_low_yield_a_bank_does_not_append_b_method_bank(self):
        src = SCAN_PATH.read_text(encoding="utf-8")
        start = src.index("fresh_bank = diversified_query_bank(")
        snippet = src[start:start+500]
        self.assertNotIn("+ b_method_bank", snippet)


if __name__ == "__main__":
    unittest.main()
