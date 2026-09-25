"""v26: the engine writes clear cards and makes mechanism-backed connections."""
import datetime as dt
import json
import re
import unittest
from pathlib import Path

from scripts import card_writer as CW
from scripts import reader_labels as RL
from scripts import reasoning_moves as MV

ROOT = Path(__file__).resolve().parents[1]
VOCAB = json.loads((ROOT / "claims_vocabulary.json").read_text(encoding="utf-8"))


def node(cid, text, *, obj="compute.capacity", kind="action", status="operating", mechanism="funds", level="eu",
         actor="European Commission", actor_class="eu_body", countries=(), source="Source", date="2026-08-01",
         direction="expands", title="", origin="deep_scan"):
    return {"claim_id": cid, "_record_id": "rec:" + cid, "record_key": "link:https://example.org/" + cid, "text": text,
            "_title": title or text, "object": obj, "secondary_objects": [], "kind": kind, "status": status,
            "mechanism": mechanism, "direction": direction, "scope": {"level": level, "countries": list(countries)},
            "actor": {"name": actor, "class": actor_class}, "_source": source, "status_date": date, "merit": 90,
            "origin": origin, "era": "current", "_primary": True, "_collection": "strand_a"}


class ReaderLabelTests(unittest.TestCase):
    def test_every_controlled_object_has_a_reader_name(self):
        for obj in VOCAB["objects"]:
            self.assertIn(obj, RL.OBJECT_LABELS, obj)
            self.assertNotIn(".", RL.label(obj), obj)
            self.assertNotIn("_", RL.label(obj), obj)

    def test_labels_read_naturally(self):
        self.assertEqual(RL.label("materials.advanced"), "advanced materials")
        self.assertEqual(RL.label("innovation.regional_capacity"), "regional innovation capacity")
        self.assertEqual(RL.label("materials.critical_raw"), "critical raw materials")


class CardWriterTests(unittest.TestCase):
    def test_no_ellipsis_and_clause_cut(self):
        long = ("The EU's reliance on externally sourced inputs, technologies and infrastructures makes its growth model "
                "structurally fragile; of four constructed trajectories only Strategic Europe aligns competitiveness, control "
                "over critical flows and innovation direction, which the authors argue requires stronger alignment.")
        cut = CW.clause_cut(long, 30)
        self.assertTrue(cut.endswith("structurally fragile."))
        self.assertNotIn("…", cut)

    def test_single_source_contested_risk_is_modal(self):
        n = node("s1", "The publication documents growing opposition to the proposed research infrastructure.",
                 obj="research.infrastructure", kind="diagnosis", status="delivered", mechanism="assesses", direction="becomes_contested")
        ref = {"claim_id": "s1", "identity": "rec:s1", "role": "support", "source_statement": n["text"], "source": "Source A", "date": "2026-07-01",
               "claim_kind": "diagnosis", "claim_status": "delivered", "mechanism": "assesses", "object": "research.infrastructure"}
        card = CW.write_card("corroborated_claim", "risk", {"object": "research.infrastructure", "direction": "becomes_contested"},
                             {"support": [ref], "object": "research.infrastructure"}, {"s1": n}, VOCAB)
        self.assertIn("could become more contested", card["headline"])
        self.assertIn("Radar's inference", card["basis"])
        self.assertIn("opposition to the proposed research infrastructure", card["lead"])  # the finding itself
        self.assertNotIn("Source A", card["lead"])  # no who-said-what in the card text; sources are listed separately

    def test_shock_names_how_the_pressure_would_bite(self):
        self.assertTrue(CW.exposure_mechanism("export_control", "chips"))
        self.assertFalse(CW.exposure_mechanism("export_control", "talent"))


class ReasoningMoveTests(unittest.TestCase):
    def test_magnitude_contrast_computes_a_priority_gap(self):
        nodes = [
            node("safe", "SAFE establishes up to €150 billion in EU loans supporting joint defence procurement and industrial capacity.",
                 obj="finance.strategic_investment", status="in_force", source="European Commission", date="2025-05-27"),
            node("agile", "The EU created a EUR 115 million pilot instrument to fund and rapidly field disruptive defence innovations from SMEs.",
                 obj="defence.innovation_funding", status="adopted", source="European Commission", date="2026-03-26"),
        ]
        out = MV.magnitude_contrasts(nodes, VOCAB)
        gap = [c for c in out if c["contrast_frame"] == "priority_gap"]
        self.assertTrue(gap)
        self.assertGreater(gap[0]["ratio"], 1000)
        self.assertEqual(gap[0]["larger_label"], "defence procurement")
        self.assertEqual(gap[0]["smaller_label"], "defence innovation")

    def test_external_restriction_becomes_an_opening(self):
        nodes = [
            node("us", "Proposed US grant-policy changes would add restrictions to international research collaboration.",
                 obj="research.collaboration", kind="action", status="proposed", mechanism="restricts", level="external",
                 actor="US Office of Management and Budget", actor_class="third_country", countries=["US"], source="Science|Business",
                 date="2026-07-16", direction="contracts"),
            node("erc", "US-based eligible ERC Starting Grant applications increased in 2026.", obj="talent.recruitment_abroad",
                 mechanism="recruits", source="Science|Business News", date="2026-09-22"),
        ]
        out = MV.external_openings(nodes, VOCAB)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["external_actor"], "US")
        self.assertEqual(out[0]["wow_preliminary"], 3)  # the gain names the same outside actor


if __name__ == "__main__":
    unittest.main()
