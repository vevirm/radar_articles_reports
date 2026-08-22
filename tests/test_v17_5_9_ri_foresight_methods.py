import unittest
import sys, types
try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    sys.modules["feedparser"] = types.ModuleType("feedparser")

from scripts.scan_radar import gate_scope, initial_scan_state
import json
from pathlib import Path


class RIForesightMethodTransferTests(unittest.TestCase):
    def test_accepts_delphi_methodology_for_ri_foresight_without_geo_or_eu_words(self):
        ev = gate_scope(
            "A new Delphi methodology for R&I foresight",
            "This article develops and evaluates a Delphi method for research and innovation foresight, including expert selection, iterative elicitation, bias controls and robustness assessment.",
            "", 2, source_kind="scholarly"
        )
        self.assertTrue(ev["b_pass"])
        self.assertEqual(ev["eu_relevance"], "derived")
        self.assertTrue(ev["b_transferable"])
        self.assertFalse(ev["a_pass"])

    def test_accepts_horizon_scanning_method_for_innovation_policy(self):
        ev = gate_scope(
            "Evaluating horizon-scanning methods for innovation policy",
            "The study compares horizon scanning protocols, weak-signal coding, bias controls and evaluation criteria for innovation policy and research funding.",
            "", 2, source_kind="scholarly"
        )
        self.assertTrue(ev["b_pass"])
        self.assertTrue(ev["b_transferable"])

    def test_still_rejects_generic_lifestyle_delphi(self):
        ev = gate_scope(
            "A Delphi methodology for future lifestyles",
            "The study develops a Delphi process for consumer lifestyle scenarios, household preferences and leisure trends.",
            "", 2, source_kind="scholarly"
        )
        self.assertFalse(ev["b_pass"])

    def test_method_discovery_bank_is_explicit_and_rotating(self):
        cfg = json.loads((Path(__file__).parents[1] / "radar_config.json").read_text())
        bank = cfg.get("queries_b_method", [])
        self.assertGreaterEqual(len(bank), 12)
        self.assertTrue(any("Delphi" in q or "delphi" in q for q in bank))
        self.assertTrue(any("horizon scanning" in q.lower() for q in bank))
        self.assertGreaterEqual(int(cfg.get("queries_b_method_per_scan", 0)), 4)
        state = initial_scan_state({"source_expansion_version": "v17.5.2-gap-report-recall"})
        self.assertIn("strand_b_method_cursor", state)

    def test_still_rejects_trend_output_without_methodology(self):
        ev = gate_scope(
            "Megatrends for research and innovation 2040",
            "The report lists future trends affecting research and innovation but does not evaluate a foresight method or methodological design.",
            "", 2, source_kind="scholarly"
        )
        self.assertFalse(ev["b_pass"])


if __name__ == "__main__":
    unittest.main()
