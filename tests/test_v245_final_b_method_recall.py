from pathlib import Path
import importlib.util
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_v245_contract", SCAN_PATH)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)


class V245FinalBMethodRecallTests(unittest.TestCase):
    def assert_b(self, title, abstract=""):
        ev = S.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertTrue(ev["b_pass"], ev)
        return ev

    def assert_not_b(self, title, abstract=""):
        ev = S.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["b_pass"], ev)
        return ev

    def test_b_is_independent_of_europe_scope_when_method_is_object(self):
        ev = self.assert_b("Mission-oriented scenarios: A new method for urban foresight")
        self.assertFalse(ev["a_pass"], ev)

    def test_medical_innovation_scanning_framework_development_is_b(self):
        self.assert_b(
            "Horizon scanning for medical technologies: Methodological framework development study of the Medical Innovation Scanning Technique"
        )

    def test_foresight_feasibility_study_is_b(self):
        self.assert_b(
            "Participation in strategic foresight: Feasibility of using nonexpert methods for megatrend assessment"
        )

    def test_dynamic_adaptive_scenario_approach_is_b(self):
        self.assert_b(
            "A dynamic and adaptive scenario approach for formulating science & technology policy"
        )

    def test_novel_emerging_technology_identification_method_is_b(self):
        self.assert_b(
            "A novel method to identify emerging technologies using a semi-supervised topic clustering model: A case of 3D printing industry"
        )

    def test_technology_roadmapping_method_study_is_b(self):
        self.assert_b(
            "Research on the TRM Kaizen method for governmental organizations to apply technology roadmapping as a methodology to achieve the goals of industrial technology policy"
        )

    def test_pure_application_stays_out(self):
        self.assert_not_b(
            "Forecasting emerging technologies using data augmentation and deep learning",
            "We use data augmentation and deep learning to forecast a set of emerging technologies."
        )

    def test_research_evaluation_topic_without_method_object_stays_out(self):
        self.assert_not_b(
            "Interdisciplinary knowledge combinations and emerging technological topics: Implications for reducing uncertainties in research evaluation"
        )

    def test_version_bumped_for_reconsideration(self):
        cfg = json.loads((ROOT / "radar_config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg.get("admission_profile"), "v24.5-final-b-method-recall")
        self.assertEqual(S.CURATOR_DECISION_PROFILE_VERSION, "v24.5-final-b-method-recall")


if __name__ == "__main__":
    unittest.main()
