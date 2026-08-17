import unittest
import sys, types
try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    sys.modules["feedparser"] = types.ModuleType("feedparser")
from scripts.scan_radar import gate_scope, document_exclusion_reason


class ClassifierTests(unittest.TestCase):
    def test_rejects_facility_call_false_positive(self):
        title = "PAMEC, Properties of Actinide Materials under Extreme Conditions"
        text = (
            "The PAMEC facility provides access to installations for basic research. "
            "Horizon Europe calls are open to participants from non-associated third countries "
            "unless conditions are specified in the work programme."
        )
        self.assertIsNotNone(document_exclusion_reason(title, "facility page"))
        ev = gate_scope(title, text, "", 1)
        self.assertFalse(ev["a_pass"])

    def test_accepts_true_strand_a_research_security(self):
        title = "Research security and the changing geopolitics of European research policy"
        abstract = (
            "This study examines how European Union research and innovation policy is adapting to geopolitical rivalry. "
            "It analyses research security, foreign interference and de-risking in international scientific cooperation, "
            "with implications for Horizon Europe and member-state policy."
        )
        ev = gate_scope(title, abstract, "", 2)
        self.assertTrue(ev["a_pass"])

    def test_rejects_general_geopolitics_without_ri(self):
        title = "Europe in a new era of strategic competition"
        abstract = "The report examines sanctions, military alliances and national security competition between major powers."
        ev = gate_scope(title, abstract, "", 1)
        self.assertFalse(ev["a_pass"])

    def test_accepts_methodology_first_strand_b(self):
        title = "Designing strategic foresight methods for EU research and innovation policy under geopolitical uncertainty"
        abstract = (
            "The paper evaluates horizon scanning and scenario methods used in European Union research and innovation policy. "
            "It compares methodological design choices, bias controls, participatory processes and evaluation criteria for "
            "anticipatory governance under geopolitical and economic-security uncertainty."
        )
        ev = gate_scope(title, abstract, "", 2)
        self.assertTrue(ev["b_pass"])

    def test_rejects_pure_trend_output_for_b(self):
        title = "Megatrends 2035: The future of European technology"
        abstract = (
            "This outlook lists trends in artificial intelligence, demographics and energy. "
            "It presents scenarios for Europe but does not discuss how foresight methods are designed or evaluated."
        )
        ev = gate_scope(title, abstract, "", 1)
        self.assertFalse(ev["b_pass"])

    def test_accepts_document_level_a_bridge(self):
        title = "European innovation policy in an age of economic security"
        abstract = (
            "The report analyses European Union research and innovation policy for critical technologies. "
            "A separate section examines strategic dependencies, de-risking and export controls in the US-China technology rivalry. "
            "It assesses consequences for EU funding and international research cooperation."
        )
        ev = gate_scope(title, abstract, "", 1)
        self.assertTrue(ev["a_pass"])

    def test_accepts_transferable_methodology_b(self):
        title = "Evaluating horizon-scanning methods for public technology policy"
        abstract = (
            "This peer-reviewed study compares horizon scanning methods, evaluation criteria and bias controls for government technology policy. "
            "It proposes a framework for integrating weak signals with strategic intelligence and risk assessment."
        )
        ev = gate_scope(title, abstract, "", 2)
        self.assertTrue(ev["b_pass"])
        self.assertEqual(ev["eu_relevance"], "derived")

    def test_rejects_unrelated_futures_methodology(self):
        title = "Integral foresight methodology for post-growth lifestyles"
        abstract = (
            "The article develops an integral foresight method combining literature review, scenarios and participatory workshops. "
            "It explores household lifestyles and personal wellbeing under post-growth futures."
        )
        ev = gate_scope(title, abstract, "", 2)
        self.assertFalse(ev["b_pass"])


if __name__ == "__main__":
    unittest.main()
