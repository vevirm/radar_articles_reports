from __future__ import annotations

import unittest

from scripts import claim_reasoning_live as live
from scripts import claim_reasoning_shadow as shadow
from scripts.claims_schema import load_vocabulary


def _node(obj: str, *, actor_class: str = "eu_body", scope: str = "eu"):
    return {
        "object": obj,
        "secondary_objects": [],
        "actor": {"class": actor_class},
        "scope": {"level": scope, "countries": []},
        "kind": "action",
        "direction": "expands",
        "mechanism": "supports",
        "status": "operating",
    }


class ReasoningProductSemanticsTests(unittest.TestCase):
    def test_sequence_gap_products_do_not_leak_into_ongoing_phenomena(self):
        self.assertEqual(live._product_for({"grammar_id": "practice_before_doctrine"}), "risk")
        self.assertEqual(live._product_for({"grammar_id": "goal_without_measure"}), "risk")
        self.assertEqual(live._product_for({"grammar_id": "clock_before_rule"}), "risk")
        self.assertEqual(live._product_for({"grammar_id": "success_metric_gap"}), "risk")
        self.assertEqual(live._product_for({"grammar_id": "named_continuity"}), "continuity")
        self.assertEqual(live._product_for({"grammar_id": "era_conjunction"}), "continuity")
        self.assertEqual(live._product_for({"grammar_id": "split_recurrence"}), "continuity")

    def test_triggerless_internal_dependency_is_not_automatically_a_shock(self):
        vocab = load_vocabulary(live.ROOT / "claims_vocabulary.json")
        ok, reason = shadow._shock_driver_basis(
            "datacentre.permitting",
            [_node("datacentre.permitting")],
            vocab,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "no_discontinuity_driver")

    def test_external_or_critical_input_dependency_can_seed_a_shock(self):
        vocab = load_vocabulary(live.ROOT / "claims_vocabulary.json")
        ok_export, _ = shadow._shock_driver_basis(
            "eu_entities.export_access",
            [_node("eu_entities.export_access", actor_class="third_country", scope="external")],
            vocab,
        )
        ok_material, _ = shadow._shock_driver_basis(
            "materials.critical_raw",
            [_node("materials.critical_raw", actor_class="third_country", scope="external")],
            vocab,
        )
        self.assertTrue(ok_export)
        self.assertTrue(ok_material)

    def test_reader_copy_uses_plain_language_not_grammar_or_object_tokens(self):
        cases = [
            (
                "practice_before_doctrine", "risk",
                {"object": "research.system_governance"},
                {"primary_records": 3, "primary_sources": 3},
            ),
            (
                "latent_channel", "opportunity",
                {"endpoint_objects": ["research.infrastructure", "compute.capacity"]},
                {"primary_records": 4, "primary_sources": 4},
            ),
            (
                "dependency_pathway", "shock",
                {"endpoint_objects": ["compute.public_procurement", "materials.critical_raw"]},
                {"primary_records": 5, "primary_sources": 5},
            ),
        ]
        forbidden = ("latent channel", "practice before doctrine", "dependency pathway", " × ", "research.system_governance", "compute.capacity", "materials.critical_raw")
        for grammar, product, raw, candidate in cases:
            title, summary = live._reader_copy(grammar, product, raw, candidate)
            visible = f"{title} {summary}".lower()
            for token in forbidden:
                self.assertNotIn(token, visible)


if __name__ == "__main__":
    unittest.main()
