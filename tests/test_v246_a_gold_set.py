"""Expanded Strand-A gold set for the v24.6 criteria repair.

A is evidence about the European R&I system.  Direct geopolitical language is one route,
but internal EU R&I state variables can also qualify when they materially describe Europe's
capacity/position.  Local applications and downstream social/consumer outcomes do not become A
merely because they happen in Europe or use a strategic technology.
"""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_v246_a_gold", SCAN)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)


class V246ExpandedAGold(unittest.TestCase):
    def gate(self, title, abstract):
        return S.gate_scope(title, abstract, "", 2, source_kind="scholarly")

    def assertA(self, title, abstract):
        ev = self.gate(title, abstract)
        self.assertTrue(ev["a_pass"], ev)

    def assertNotA(self, title, abstract):
        ev = self.gate(title, abstract)
        self.assertFalse(ev["a_pass"], ev)

    # --- structural A: internal evidence that describes a strategic R&I state variable ---
    def test_research_compute_capacity_is_a(self):
        self.assertA(
            "European research infrastructure and compute capacity across EU member states",
            "We measure investment, capacity concentration and access constraints across European research computing facilities and assess gaps in high-performance computing available to researchers.",
        )

    def test_researcher_mobility_and_retention_is_a(self):
        self.assertA(
            "Researcher mobility and talent retention in the European Research Area",
            "Using longitudinal data, we estimate researcher outflows, return rates and scientific workforce retention across EU countries.",
        )

    def test_semiconductor_patent_position_is_a(self):
        self.assertA(
            "Europe’s semiconductor patent position in advanced lithography",
            "We map patent ownership and citation impact across European firms and research organisations to assess technological position in advanced semiconductor equipment.",
        )

    def test_university_industry_transfer_performance_is_a(self):
        self.assertA(
            "University-industry knowledge transfer performance across the European Union",
            "We compare technology transfer, spin-off formation and university-industry collaboration across EU innovation systems using panel data.",
        )

    def test_horizon_research_infrastructure_evaluation_is_a(self):
        self.assertA(
            "Evaluation of Horizon Europe research infrastructure investments",
            "We evaluate how Horizon Europe funding changes research infrastructure capacity, cross-border access and scientific capability across the EU.",
        )

    # --- direct A: the source itself establishes the strategic/geopolitical relation ---
    def test_research_security_collaboration_is_a(self):
        self.assertA(
            "Research security and EU-China scientific collaboration in sensitive technologies",
            "We analyse how European research-security screening affects collaboration with Chinese institutions in quantum and semiconductor research.",
        )

    # --- negatives: Europe + technology/application is not enough ---
    def test_local_hospital_ai_application_is_not_a(self):
        self.assertNotA(
            "Artificial intelligence adoption in a European hospital",
            "This case study evaluates an AI decision-support tool in one hospital and measures clinician satisfaction and workflow efficiency.",
        )

    def test_rail_cybersecurity_compliance_is_not_a(self):
        self.assertNotA(
            "Cybersecurity adoption under NIS 2 in European rail operators",
            "We survey employees at regional rail operators and assess adoption of a cybersecurity framework for operational compliance.",
        )

    def test_dental_elearning_is_not_a(self):
        self.assertNotA(
            "Digital learning tools in European dental education",
            "This study evaluates e-learning satisfaction and personalisation among dentistry students at universities in Europe.",
        )

    def test_microgrid_optimisation_is_not_a(self):
        self.assertNotA(
            "Renewable energy optimisation for a European microgrid",
            "We propose a control algorithm and test it on a microgrid dataset from Italy, reducing energy costs under several scenarios.",
        )

    def test_ev_consumer_preferences_are_not_a(self):
        self.assertNotA(
            "Consumer adoption of electric vehicles in European regions",
            "We model household purchase intentions and consumer preferences for electric vehicles using survey data from five European countries.",
        )

    def test_multilingual_research_practice_is_not_a(self):
        self.assertNotA(
            "Multilingual research practices in a European University Alliance",
            "We survey researchers about the languages they use for communication and publication within a European university network.",
        )


if __name__ == "__main__":
    unittest.main()
