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


    def test_shock_page_is_diverse(self):
        from collections import Counter
        m = {c["id"]: c for c in self.state["candidates"]}
        page = [m[i] for i in self.state["publications"]["shock"]]
        for kind, cap in (("driver", crl.SHOCK_MAX_PER_DRIVER), ("asset", crl.SHOCK_MAX_PER_ASSET)):
            counts = Counter(v for c in page for k, v, _ in crl._diversity_keys(c) if k == kind)
            self.assertLessEqual(max(counts.values()), cap + 1, kind)  # one-step relaxation only

    def test_every_disruption_type_has_a_path_to_mature(self):
        stock = {c.get("pressure_id") or v.split(".")[-1]
                 for c in self.state["candidates"] if c.get("product") == "shock" and c.get("status") not in {"killed", "dormant"}
                 for k, v, _ in crl._diversity_keys(c) if k == "driver"}
        held = {v.split(".")[-1]
                for c in self.state["candidates"] if c.get("product") == "shock" and c.get("stock_tier") in {"page", "reserve", "creative_reserve"}
                for k, v, _ in crl._diversity_keys(c) if k == "driver"}
        self.assertEqual(stock - held, set())

    def test_stable_when_nothing_changes(self):
        # The first run starts from a shelf chosen by an older code version, so one
        # settling step is legitimate hysteresis.  After that, with no new evidence,
        # the page must not change at all.
        raw = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        state = self.state
        runs = []
        for _ in range(2):
            r = copy.deepcopy(raw)
            r["high_order_inference"] = copy.deepcopy(state)
            crl._LIVE_DETECTION_CACHE.clear()
            state = crl.refresh_claim_high_order(r, copy.deepcopy(state), root=ROOT)
            runs.append(state)
        for p in PRODUCTS:
            self.assertEqual(runs[1]["publications"][p], runs[0]["publications"][p], p)

    def test_stronger_evidence_swaps_in_small_gain_does_not(self):
        cands = self.state["candidates"]
        m = {c["id"]: c for c in cands}
        for p in ("risk", "opportunity"):
            page = [m[i] for i in self.state["publications"][p]]
            used = {(k, v) for c in page for k, v, _ in crl._diversity_keys(c)}
            for w in (1, 2, 3, 4, 5):
                natives = [c for c in page if c.get("wow") == w and not c.get("page_slot_wow")]
                if len(natives) < 3:
                    continue
                weak = min(natives, key=crl._selection_rank)
                if weak["maturity_score"] > 85:
                    continue
                pool = [c for c in cands if c.get("product") == p and c.get("wow") == w and c.get("stock_tier") == "reserve"
                        and c.get("presentation_ready") and not ({(k, v) for k, v, _ in crl._diversity_keys(c)} & used)]
                if not pool:
                    continue
                ch = max(pool, key=crl._selection_rank)
                results = []
                for gain in (1, crl.SHELF_SWAP_MARGIN + 3):
                    cs = copy.deepcopy(cands); mc = {c["id"]: c for c in cs}
                    mc[ch["id"]]["score"] = int(mc[ch["id"]].get("score", 0)) + int((weak["maturity_score"] + gain - ch["maturity_score"]) / 0.58) + 2
                    pubs, _ = crl._select_stage7(cs, copy.deepcopy(self.state))
                    results.append(ch["id"] in pubs[p])
                self.assertEqual(results, [False, True], p)
                return
        self.skipTest("no clean swap case in this snapshot")


if __name__ == "__main__":
    unittest.main()
