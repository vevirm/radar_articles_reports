import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import claim_reasoning_live as crl

PRODUCTS = ("shock", "trend", "continuity", "risk", "opportunity")


class CreativeReserveHelperTests(unittest.TestCase):
    def test_contradicted_or_empty_hypotheses_are_not_held(self):
        empty = {"status": "watch", "support": [], "context": []}
        self.assertFalse(crl._creative_eligible(empty)[0])
        contradicted = {
            "status": "watch",
            "support": [{"identity": "a"}],
            "context": [],
            "counter_records": 3,
        }
        self.assertEqual(crl._creative_eligible(contradicted), (False, "contradicted"))
        killed = {"status": "killed", "support": [{"identity": "a"}]}
        self.assertFalse(crl._creative_eligible(killed)[0])

    def test_partially_grounded_weak_signal_is_held(self):
        c = {
            "status": "watch",
            "wow": 5,
            "endpoint_objects": ["chips.fab", "shock_pressure.energy"],
            "support": [{"identity": "a", "strand": "C", "claim_origin": "deep_scan", "source": "X", "date": "2026-09-10"}],
            "context": [],
        }
        self.assertTrue(crl._creative_eligible(c)[0])
        traits = crl._creative_traits(c, "2026-09-18")
        for t in ("distant", "cross_domain", "emerging", "weak_signal", "partially_grounded"):
            self.assertTrue(traits[t], t)

    def test_family_and_cluster_scope_matching(self):
        node = {"object": "research_security.screening", "secondary_objects": []}
        self.assertTrue(crl._object_matches("family:research_security", node))
        self.assertFalse(crl._object_matches("family:talent", node))
        crl._register_family("cluster:test_cluster", ["research_security.screening"])
        self.assertTrue(crl._object_matches("cluster:test_cluster", node))

    def test_reviewed_primary_tag_grounds_but_provisional_does_not(self):
        self.assertTrue(crl._reviewed_tag_grounds("talent.retention", "talent.retention", "deep_scan"))
        self.assertFalse(crl._reviewed_tag_grounds("talent.retention", "talent.retention", "provisional"))
        self.assertFalse(crl._reviewed_tag_grounds("talent.retention", "ai.adoption", "deep_scan"))

    def test_neutral_wording_uses_reviewed_direction_only(self):
        reviewed = {"text": "Talent policy was discussed at the council.", "object": "talent.retention", "origin": "deep_scan", "direction": "expands"}
        scanner = dict(reviewed, origin="provisional")
        self.assertEqual(crl._reader_trend_side(reviewed, "talent.retention"), "expands")
        self.assertEqual(crl._reader_trend_side(scanner, "talent.retention"), "")


class CreativeReserveEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        prev = copy.deepcopy(raw.get("high_order_inference") or {})
        cls.state = crl.refresh_claim_high_order(copy.deepcopy(raw), prev, root=ROOT)
        if cls.state is None:
            raise unittest.SkipTest("claim authority gate not ready in this repository snapshot")

    def test_every_page_is_full_and_reserve_meets_target(self):
        sel = self.state["selection"]
        for p in PRODUCTS:
            self.assertEqual(len(self.state["publications"][p]), 15, p)
            self.assertGreaterEqual(sel[p]["reserve"], crl.RESERVE_TARGET, p)

    def test_creative_reserve_is_never_published_and_never_contradicted(self):
        published = {i for ids in self.state["publications"].values() for i in ids}
        for c in self.state["candidates"]:
            if not c.get("creative_reserve"):
                continue
            self.assertNotIn(c.get("id"), published)
            self.assertEqual(c.get("stock_tier"), "creative_reserve")
            self.assertTrue(crl._creative_eligible(c)[0])
            self.assertTrue(c.get("creative_traits"))

    def test_reserve_spans_wow_levels(self):
        for p in PRODUCTS:
            by_wow = self.state["selection"][p]["reserve_by_wow"]
            self.assertGreaterEqual(sum(1 for v in by_wow.values() if v > 0), 3, p)


if __name__ == "__main__":
    unittest.main()
