import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import claim_reasoning_live as crl
from scripts import scenarios_2035 as sc2035


class Scenarios2035Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        state = crl.refresh_claim_high_order(copy.deepcopy(raw), copy.deepcopy(raw.get("high_order_inference") or {}), root=ROOT)
        if state is None:
            raise unittest.SkipTest("claim authority gate not ready")
        cls.state = state
        cls.sc = state["scenarios_2035"]

    def test_four_worlds_with_four_variants_each(self):
        self.assertNotIn("error", self.sc)
        worlds = self.sc["scenarios"]
        self.assertEqual(len(worlds), 4)
        self.assertEqual({w["id"] for w in worlds}, {"big_commons", "fortress_frontier", "brilliant_but_broke", "quiet_retreat"})
        for w in worlds:
            self.assertEqual(len(w["variants"]), 4, w["id"])
            self.assertTrue(w["story"] and w["name"])
            # Scenarios, not forecasts: no plausibility or ranking.
            self.assertNotIn("closeness", w)
            self.assertNotIn("closeness_rank", w)

    def test_every_variant_is_triggered_by_a_distinct_published_finding(self):
        published = {i for ids in self.state["publications"].values() for i in ids}
        triggers = [v["finding_id"] for w in self.sc["scenarios"] for v in w["variants"]]
        self.assertEqual(len(triggers), len(set(triggers)))
        self.assertTrue(set(triggers) <= published)
        for w in self.sc["scenarios"]:
            for s in w["signals"]:
                self.assertIn(s["finding_id"], published)

    def test_variant_names_do_not_repeat(self):
        names = [v["name"] for w in self.sc["scenarios"] for v in w["variants"]]
        self.assertEqual(len(names), len(set(names)))

    def test_no_likelihood_language(self):
        import re
        texts = [b["text"] for w in self.sc["scenarios"] for b in w["bullets"]]
        texts += [b["text"] for w in self.sc["scenarios"] for v in w["variants"] for b in v["bullets"]]
        joined = " ".join(texts).lower()
        for phrase in ("closest", "plausib", "likely", "probab", "odds", "long shot", "stretch from here"):
            self.assertNotIn(phrase, joined, phrase)
        html = (ROOT / "2035" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("futureToday", html)
        self.assertNotIn("closeness", html)

    def test_empty_inputs_do_not_crash(self):
        out = sc2035.build_scenarios_2035({}, [], "2026-09-19")
        self.assertEqual(out["scenarios"], [])

    def test_page_is_in_navigation_and_has_no_inline_style(self):
        shell = (ROOT / "site-shell.js").read_text(encoding="utf-8")
        self.assertIn("['2035/','2035','']", shell)
        html = (ROOT / "2035" / "index.html").read_text(encoding="utf-8")
        self.assertIn("radar.css", html)
        self.assertIn("site-shell.js", html)
        self.assertNotIn("<style", html)
        self.assertNotIn(' style="', html)


    # ---- the page follows the findings -------------------------------------------
    def test_removed_finding_is_replaced(self):
        pubs = copy.deepcopy(self.state["publications"])
        gone = self.sc["scenarios"][0]["variants"][0]["finding_id"]
        for k in pubs:
            pubs[k] = [i for i in pubs[k] if i != gone]
        out = sc2035.build_scenarios_2035(pubs, self.state["candidates"])
        used = {v["finding_id"] for w in out["scenarios"] for v in w["variants"]}
        self.assertNotIn(gone, used)
        self.assertEqual(sum(len(w["variants"]) for w in out["scenarios"]), 16)

    def test_new_finding_enters_the_scenarios(self):
        cands = copy.deepcopy(self.state["candidates"]); pubs = copy.deepcopy(self.state["publications"])
        base = sc2035.build_scenarios_2035(pubs, cands)
        used = next(v["finding_id"] for w in base["scenarios"] for v in w["variants"] if v["kind"] == "opportunity")
        by_id = {c["id"]: c for c in cands}
        new = copy.deepcopy(by_id[used])
        new["id"] = "claim:new:opportunity"; new["reader_title"] = "A brand-new opportunity"
        cands.append(new)
        pubs["opportunity"] = [new["id"] if i == used else i for i in pubs["opportunity"]]
        out = sc2035.build_scenarios_2035(pubs, cands)
        self.assertIn("A brand-new opportunity", json.dumps(out))

    def test_scenarios_are_rebuilt_by_the_scan_step(self):
        # The same refresh that updates findings each scan also rebuilds 2035.
        self.assertIn("scenarios_2035", self.state)


    def _paragraphs(self, sc):
        out = []
        for w in sc["scenarios"]:
            out += [b["text"] for b in w["bullets"]]
            for v in w["variants"]:
                out += [b["text"] for b in v["bullets"]]
        return out

    def test_every_card_is_bullets(self):
        for w in self.sc["scenarios"]:
            labels = [b["label"] for b in w["bullets"]]
            for need in ("Picture", "A day in 2035", "Researchers", "Universities", "Companies", "Funders", "The price"):
                self.assertIn(need, labels, w["id"])
            for v in w["variants"]:
                vl = [b["label"] for b in v["bullets"]]
                self.assertEqual(vl[0], "Trigger")
                self.assertIn("Where Europe ends up", vl)
                self.assertGreaterEqual(len(vl), 3)

    def test_language_does_not_repeat(self):
        from collections import Counter
        paras = self._paragraphs(self.sc)
        self.assertEqual([p for p, n in Counter(paras).items() if n > 1], [])
        import re as _re
        # Dated history lines ("July 2026, <source>: ...") legitimately share openings.
        openings = Counter(" ".join(p.split()[:4]) for p in paras
                           if not _re.match(r"^[A-Z][a-z]+ \d{4},", p))
        self.assertEqual([o for o, n in openings.items() if n > 1], [])
        import re
        self.assertEqual([p for p in paras if re.search(r"\. [a-z]", p)], [])

    def test_updates_when_findings_change(self):
        pubs, cands = self.state["publications"], self.state["candidates"]
        base = sc2035.build_scenarios_2035(pubs, cands)
        # A shock finding leaves the page: its variant is replaced.
        gone = base["scenarios"][0]["variants"][0]["finding_id"]
        p1 = copy.deepcopy(pubs)
        p1["shock"] = [i for i in p1["shock"] if i != gone]
        after = sc2035.build_scenarios_2035(p1, cands)
        self.assertFalse(any(v["finding_id"] == gone for w in after["scenarios"] for v in w["variants"]))
        # Trend balances change: the stories that draw on them change with them.
        c2 = copy.deepcopy(cands)
        m = {c["id"]: c for c in c2}
        for i in pubs["trend"]:
            m[i]["trend_balance"]["left_title"] = "A new push " + i[-4:]
            m[i]["trend_balance"]["right_title"] = "A new pushback " + i[-4:]
        swung = sc2035.build_scenarios_2035(pubs, c2)
        self.assertNotEqual([w["bullets"] for w in swung["scenarios"]], [w["bullets"] for w in base["scenarios"]])
        # Same findings, same page: deterministic.
        self.assertEqual(sc2035.build_scenarios_2035(pubs, cands), base)


if __name__ == "__main__":
    unittest.main()
