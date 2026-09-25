"""Trend headlines state the trend their evidence shows (v26).

The earlier rule headed each side with the first clause of its single strongest
record ("Belgium has opened a semiconductor-espionage case"), which turned a trend
backed by many sources into an anecdote without context.  The invariant kept from
that rule is entailment: a side title may not claim more than its evidence shows.
It is now enforced by characterising the side from its evidence (who acts, what kind
of evidence it is) and showing the developments underneath as examples.
"""
import inspect
import unittest

from scripts import card_writer as CW
from scripts.claim_reasoning_live import _trend_payload


def _ref(n, role):
    return {"claim_id": n["claim_id"], "identity": n["claim_id"], "role": role, "source_statement": n["text"],
            "source": n["_source"], "date": n["status_date"], "claim_kind": n["kind"], "claim_status": n["status"],
            "mechanism": n["mechanism"], "object": "research_security.screening", "title": n["text"]}


def _node(cid, text, source, date, kind="action", status="operating", mechanism="launches", countries=(), level="member_state",
          actor_class="national_funder", direction="expands"):
    return {"claim_id": cid, "text": text, "_source": source, "status_date": date, "kind": kind, "status": status,
            "mechanism": mechanism, "scope": {"level": level, "countries": list(countries)},
            "actor": {"name": source, "class": actor_class}, "direction": direction}


class TrendHeadlineEntailmentTests(unittest.TestCase):
    def test_single_record_anecdote_no_longer_heads_a_trend(self):
        src = inspect.getsource(_trend_payload)
        self.assertNotIn("headline_from_plain", src)
        self.assertNotIn("belgian authorities opened a concrete semiconductor-espionage case", src)
        self.assertIn("write_trend", src)

    def test_side_titles_state_the_point_without_names(self):
        nodes = {
            "a": _node("a", "Belgian authorities opened a semiconductor-espionage case.", "Reuters", "2026-09-07", countries=["Belgium"]),
            "b": _node("b", "Research-security self-assessment became part of Research Council of Finland applications.", "Research Council of Finland", "2026-08-21", mechanism="requires", countries=["Finland"]),
            "c": _node("c", "German universities debate de-risking.", "MERICS", "2026-06-30", kind="diagnosis", status="delivered", mechanism="assesses", level="eu", actor_class="ngo_thinktank"),
            "x": _node("x", "Export controls remain member state competences.", "JCMS", "2026-07-06", kind="diagnosis", status="delivered", mechanism="assesses", level="eu", actor_class="university_group", direction="becomes_contested"),
            "y": _node("y", "Research security makes openness more conditional.", "European Security", "2026-06-01", kind="diagnosis", status="delivered", mechanism="assesses", level="eu", actor_class="university_group", direction="becomes_conditional"),
        }
        left = [_ref(nodes[k], "Expands") for k in ("a", "b", "c")]
        right = [_ref(nodes[k], "Constrains") for k in ("x", "y")]
        out = CW.write_trend("cluster:research_security", left, right, nodes, left_pull=41, right_pull=59)
        self.assertEqual(out["left_title"], "Governments are acting on research security")
        self.assertIn("Studies", out["right_title"])            # analysis is described as analysis
        shown = out["pair_title"] + out["left_title"] + out["left_plain"] + out["right_plain"]
        for name in ("Belgium", "Finland", "Reuters", "Research Council"):
            self.assertNotIn(name, shown)                       # points, not who-did-what
        self.assertNotIn("…", out["left_plain"] + out["right_plain"])
        self.assertTrue(out["pair_title"].startswith("Research security:"))

    def test_analysis_on_both_sides_is_reported_as_disagreement(self):
        nodes = {k: _node(k, t, s, "2026-07-01", kind="diagnosis", status="delivered", mechanism="assesses", level="eu", actor_class="university_group", direction=d)
                 for k, t, s, d in (("p", "Studies link R&D intensity to better outcomes.", "Journal A", "expands"),
                                    ("q", "Collaboration is associated with faster adoption.", "Journal B", "expands"),
                                    ("r", "EU27 remains behind the US and Japan.", "JRC", "contracts"),
                                    ("t", "Gaps persist for scale-up.", "European Parliament", "contracts"))}
        left = [_ref(nodes[k], "Expands") for k in ("p", "q")]
        right = [_ref(nodes[k], "Constrains") for k in ("r", "t")]
        out = CW.write_trend("innovation.system_performance", left, right, nodes, left_pull=34, right_pull=66)
        self.assertEqual(out["pair_title"], "Innovation performance: the evidence points both ways")


if __name__ == "__main__":
    unittest.main()
