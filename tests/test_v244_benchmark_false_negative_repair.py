from pathlib import Path
import importlib.util
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_v244_contract", SCAN_PATH)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)


class V244BenchmarkFalseNegativeRepairTests(unittest.TestCase):
    def test_eu_university_kis_mapping_is_ri_system_evidence(self):
        ev = S.gate_scope(
            "One more KIS? A new approach to mapping university–KIS interactions in EU regions",
            "", "", 2, source_kind="scholarly"
        )
        self.assertTrue(ev["a_pass"], ev)
        self.assertEqual(ev["eu_relevance"], "direct")

    def test_research_activity_of_eu_candidate_country_universities_is_ri(self):
        ev = S.gate_scope(
            "Similar outputs, different positions: Convergence and divergence in research activity of public and private universities in EU candidate countries",
            "", "", 2, source_kind="scholarly"
        )
        self.assertTrue(ev["a_pass"], ev)
        self.assertEqual(ev["eu_relevance"], "direct")

    def test_procurement_as_research_subject_is_not_document_type_exclusion(self):
        self.assertIsNone(S.document_exclusion_reason(
            "Buyer–supplier learning under uncertainty: Relational mechanisms in big science innovation procurement",
            "This peer-reviewed study analyses procurement as an innovation and learning mechanism in big science."
        ))
        self.assertEqual(
            S.document_exclusion_reason(
                "Procurement notice for microscopy equipment",
                "Supply, delivery and installation contract."
            ),
            "hard exclusion: procurement/acquisition notice",
        )

    def test_workshop_mentioned_in_abstract_does_not_turn_article_into_event(self):
        self.assertIsNone(S.document_exclusion_reason(
            "Bridging foresight and transition theory: Policy mixes for transforming Europe’s food systems",
            "The peer-reviewed study uses a stakeholder workshop as one part of its foresight methodology."
        ))
        self.assertEqual(
            S.document_exclusion_reason(
                "Workshop on Horizon Europe foresight methods",
                "Registration is open for this workshop."
            ),
            "hard exclusion: workshop",
        )

    def test_decision_profiles_are_bumped_for_reconsideration(self):
        cfg = json.loads((ROOT / "radar_config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg.get("admission_profile"), "v24.4-benchmark-false-negative-repair")
        self.assertEqual(S.CURATOR_DECISION_PROFILE_VERSION, "v24.4-benchmark-false-negative-repair")


if __name__ == "__main__":
    unittest.main()
