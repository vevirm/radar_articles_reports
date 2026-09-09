from pathlib import Path
import datetime as dt
import importlib.util
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
PREP_PATH = ROOT / "scripts" / "prepare_priority_docx.py"

spec = importlib.util.spec_from_file_location("radar_v243_contract", SCAN_PATH)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)

prep_spec = importlib.util.spec_from_file_location("priority_prep_v243", PREP_PATH)
P = importlib.util.module_from_spec(prep_spec)
sys.modules[prep_spec.name] = P
prep_spec.loader.exec_module(P)


class V243PriorityBenchmarkRepairTests(unittest.TestCase):
    def test_priority_parser_skips_headings_and_scan_notes(self):
        self.assertFalse(P.looks_like_apa_reference_paragraph("Evidence"))
        self.assertFalse(P.looks_like_apa_reference_paragraph("Methods"))
        self.assertFalse(P.looks_like_apa_reference_paragraph("Signals"))
        self.assertFalse(P.looks_like_apa_reference_paragraph("Research & Innovation × Geopolitics Radar"))
        self.assertFalse(P.looks_like_apa_reference_paragraph(
            "Windows applied: evidence, publications since 1 March 2026; methods, since September 2011."
        ))
        self.assertTrue(P.looks_like_apa_reference_paragraph(
            "Fuchs-Schündeln, N., & Holub, F. (2026). Homophily in grant evaluations. Nature Human Behaviour. https://doi.org/10.1038/s41562-026-02554-w"
        ))

    def test_research_grant_evaluation_is_ri_system_evidence(self):
        ev = S.gate_scope(
            "Homophily in grant evaluations",
            "The study analyses grant evaluations by European research funders and research grant allocation.",
            "", 1, source_kind="scholarly"
        )
        self.assertTrue(ev["a_pass"], ev)
        self.assertIn(ev["eu_relevance"], {"direct", "supported"})

    def test_generic_nonresearch_grant_evaluation_stays_out(self):
        ev = S.gate_scope(
            "EU grant evaluation for cultural festival funding",
            "The evaluation compares arts grants awarded to festivals and museums across Europe.",
            "", 2, source_kind="scholarly"
        )
        self.assertFalse(ev["a_pass"], ev)

    def test_scientific_knowledge_in_eu_policymaking_is_ri_system_evidence(self):
        ev = S.gate_scope(
            "The European Union’s use of scientific knowledge in SDG policymaking: A topic model approach",
            "This study examines how the European Union uses scientific knowledge in policymaking.",
            "", 2, source_kind="scholarly"
        )
        self.assertTrue(ev["a_pass"], ev)

    def test_priority_b_uses_b_method_hard_window_before_rejecting_age(self):
        raw = {
            "title": ["Functional technology foresight. A novel methodology to identify emerging technologies"],
            "abstract": "We develop and test a novel methodology for technology foresight to identify emerging technologies for science and technology policy.",
            "language": "en",
            "type": "journal-article",
            "container-title": ["European Journal of Futures Research"],
            "publisher": "Springer Nature",
        }
        with patch.object(S, "crossref_date", return_value=dt.date(2016, 1, 1)), patch.object(
            S, "quality_from_crossref", return_value=(True, 1, 1.0, "European Journal of Futures Research", "Tier 1", "peer-reviewed article")
        ):
            status, detail = S._curator_crossref_gate_status(raw)
        self.assertNotEqual(status, "outside_retention_window", detail)
        self.assertEqual(status, "passed_gate", detail)
        self.assertTrue(detail["gate"]["b_pass"], detail)

    def test_b_window_is_ten_plus_or_minus_five_year_policy(self):
        cfg = json.loads((ROOT / "radar_config.json").read_text(encoding="utf-8"))
        self.assertEqual(int(cfg.get("b_method_recent_lookback_years")), 5)
        self.assertEqual(int(cfg.get("b_method_lookback_years")), 15)

    def test_jmir_is_trusted_peer_reviewed_publisher(self):
        cfg = json.loads((ROOT / "radar_config.json").read_text(encoding="utf-8"))
        self.assertIn("JMIR Publications", cfg.get("trusted_broad_journal_publishers", []))


if __name__ == "__main__":
    unittest.main()
