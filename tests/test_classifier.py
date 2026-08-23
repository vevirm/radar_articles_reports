import unittest
import sys, types
try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    sys.modules["feedparser"] = types.ModuleType("feedparser")
from scripts.scan_radar import gate_scope, document_exclusion_reason, eu_evidence


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

    def test_accepts_future_method_for_public_technology_policy(self):
        title = "Evaluating horizon-scanning methods for public technology policy"
        abstract = (
            "This peer-reviewed study compares horizon scanning methods, evaluation criteria and bias controls for government technology policy. "
            "It proposes a framework for integrating weak signals with strategic intelligence and risk assessment."
        )
        ev = gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertTrue(ev["b_pass"])
        self.assertEqual(ev["b_route"], "future-of-A-method")

    def test_rejects_unrelated_futures_methodology(self):
        title = "Integral foresight methodology for post-growth lifestyles"
        abstract = (
            "The article develops an integral foresight method combining literature review, scenarios and participatory workshops. "
            "It explores household lifestyles and personal wellbeing under post-growth futures."
        )
        ev = gate_scope(title, abstract, "", 2)
        self.assertFalse(ev["b_pass"])


class V12BalancedRelevanceTests(unittest.TestCase):
    def test_accepts_european_ri_capabilities_without_policy_wording(self):
        title = "Europe innovation capacity in a fragmented technology order"
        abstract = (
            "Europe's innovation capacity is being reshaped by US-China technology competition. "
            "The paper analyses R&D intensity, deep-tech scale-up, semiconductor capabilities and "
            "supply-chain security across European economies."
        )
        ev = gate_scope(title, abstract, "", 2)
        self.assertTrue(ev["a_pass"])
        self.assertEqual(ev["eu_relevance"], "direct")

    def test_accepts_member_state_ri_geopolitics_as_direct_eu_scope(self):
        title = "Germany research and innovation under strategic competition"
        abstract = (
            "Germany's research and innovation system faces pressure from strategic competition with China "
            "and new technology controls. The study examines university research, R&D cooperation and "
            "technological capabilities."
        )
        ev = gate_scope(title, abstract, "", 2)
        self.assertTrue(ev["a_pass"])
        self.assertEqual(ev["eu_relevance"], "direct")

    def test_still_rejects_generic_european_geopolitics_without_ri(self):
        title = "Europe in a new era of strategic competition"
        abstract = "The report examines sanctions, military alliances and national security competition between major powers."
        ev = gate_scope(title, abstract, "", 1)
        self.assertFalse(ev["a_pass"])

    def test_still_rejects_generic_european_innovation_without_geopolitics(self):
        title = "European startup competitiveness"
        abstract = "The report examines venture capital, startup growth and productivity across European firms."
        ev = gate_scope(title, abstract, "", 1)
        self.assertFalse(ev["a_pass"])


    def test_member_state_scope_uses_whole_words(self):
        rel, evidence = eu_evidence("Germanium materials for quantum devices", "A technical materials study.", "")
        self.assertIsNone(rel)
        self.assertEqual(evidence, [])

    def test_one_passing_eu_body_mention_is_not_enough(self):
        rel, _ = eu_evidence(
            "Global technology competition",
            "A comparison of US and Chinese technology systems.",
            "The paper focuses on the United States and China. EU policy is mentioned once in a footnote-style comparison.",
        )
        self.assertIsNone(rel)

    def test_accepts_tier1_foresight_methodology_deeper_in_report(self):
        title = "Futures for European research funding"
        abstract = "This European report examines strategic foresight for research organisations and innovation funding under geopolitical and economic-security uncertainty."
        body = (
            ("Executive summary. " * 40)
            + "The report applies strategic foresight to European research funding and technology policy under strategic competition. "
            + "The methodology combines horizon scanning with participatory scenario construction. "
            + "The process uses weak signals, stakeholder workshops and evaluation criteria to test robustness."
        )
        ev = gate_scope(title, abstract, body, 1, source_kind="institutional")
        self.assertTrue(ev["b_pass"])


class V17SubstanceQualityTests(unittest.TestCase):
    def test_rejects_zero_waste_teacher_scenarios_method_paper(self):
        title = "PATHWAYS TO ZERO WASTE: PROSPECTIVE SCIENCE TEACHERS’ SOLUTIONS THROUGH EVERYDAY LIFE SCENARIOS"
        abstract = (
            "The study uses prospective scenarios with science teachers to explore household waste reduction and environmental education. "
            "Participants develop everyday-life solutions and reflect on sustainability learning."
        )
        ev = gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertFalse(ev["b_pass"])

    def test_rejects_eu_politics_report_without_ri_substance(self):
        title = "2026 Rule of law report - Communication and country chapters"
        abstract = "The European Commission reviews democracy, justice systems, media pluralism and anti-corruption policy across EU Member States."
        body = "The report discusses institutional resilience and public trust in the European Union."
        ev = gate_scope(title, abstract, body, 1, source_kind="institutional")
        self.assertFalse(ev["a_pass"])

    def test_accepts_scholarly_a_when_abstract_has_full_triangle(self):
        title = "Research security in Europe under strategic competition"
        abstract = (
            "This peer-reviewed article examines European research and innovation systems under US-China strategic competition. "
            "It analyses knowledge security, foreign interference and international scientific collaboration, with implications for Horizon Europe."
        )
        ev = gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertTrue(ev["a_pass"])

    def test_b_rejects_eu_ri_geo_method_comparison_without_method_development(self):
        title = "Horizon scanning for EU research security under geopolitical uncertainty"
        abstract = (
            "The article evaluates horizon-scanning methodology for European Union research and innovation policy. "
            "It compares weak-signal detection and scenario methods for research security, export controls and strategic competition."
        )
        ev = gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["b_pass"])


if __name__ == "__main__":
    unittest.main()
