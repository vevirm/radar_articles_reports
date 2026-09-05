"""Recall guard retained for browser-upload compatibility.

The GitHub web uploader replaces files but does not reliably remove files omitted from an
uploaded tree.  This test exists in the live repository and therefore remains part of the
actual scanner contract.  Keep it in release packages so local/package tests match GitHub.
"""
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_scan_v172041", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)
MAX_CORPUS_REJECTION_RATE = 0.25


class VocabularyDriftTests(unittest.TestCase):
    def test_admission_mechanisms_cover_recording_mechanisms(self):
        missing = [t for t in scan.A_TECH_RI_MECHANISMS if t not in scan.A_CENTRAL_TECH_RI_MECHANISMS]
        self.assertEqual(missing, [])

    def test_major_ri_system_terms_are_admissible_subjects(self):
        for term in ("deep tech", "technology transfer", "brain drain", "research security"):
            with self.subTest(term=term):
                self.assertIn(term, scan.A_MAJOR_RI_SYSTEM)
                sentence = f"European {term} policy and strategic autonomy in research and innovation."
                self.assertTrue(scan._central_ri_hits(sentence))

    def test_recorded_evidence_is_always_reproducible_by_the_gate(self):
        sentences = [
            "The EIC Tech Report identifies emerging deep tech signals supporting Europe's competitiveness in strategic technologies.",
            "European dual-use research coordination under Horizon Europe.",
            "Artificial intelligence innovation capacity across European member states.",
            "Quantum research funding and scale-up commercialisation in the European Union.",
        ]
        for sentence in sentences:
            with self.subTest(sentence=sentence[:60]):
                if scan._ri_hits(sentence):
                    self.assertTrue(scan._central_ri_hits(sentence))


class LiveCorpusRecallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        doc = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        cls.rows = [r for r in doc.get("strand_a", []) if r.get("text_mode") == "abstract_only"]

    def test_corpus_still_passes_the_centrality_gate(self):
        if len(self.rows) < 50:
            self.skipTest("corpus too small to measure recall")
        rejected = []
        for item in self.rows:
            ok, reason, _hits = scan.eu_ri_centrality(item.get("title", "") or "", item.get("summary", "") or "", "")
            if not ok:
                rejected.append((reason, str(item.get("title", ""))[:70]))
        rate = len(rejected) / len(self.rows)
        self.assertLessEqual(rate, MAX_CORPUS_REJECTION_RATE, f"Admission gate rejects {rate:.1%} of live abstract-only Strand A: {rejected[:5]}")

    def test_horizon_europe_governance_is_not_an_event_recap(self):
        abstract = (
            "The Joint Committee reviewed Horizon Europe association and research and innovation cooperation, "
            "including research security and researcher mobility."
        )
        for title in (
            "Fourth EU-Albania Horizon Europe Joint Research and Innovation Committee meeting",
            "2nd Horizon Europe association Joint Committee meeting between Canada and the European Union",
        ):
            with self.subTest(title=title[:50]):
                _ok, reason, _hits = scan.eu_ri_centrality(title, abstract, "")
                self.assertNotEqual(reason, "event_recap_not_substantive_evidence")
                # The same governance notice must also survive the final shared A/B worthiness guard.
                self.assertTrue(scan.final_ab_candidate_worthiness({
                    "title": title,
                    "summary": abstract,
                    "type": "institutional report",
                    "link": "https://research-and-innovation.ec.europa.eu/example",
                }))


class PrecisionHeldTests(unittest.TestCase):
    def test_generic_capability_language_still_fails_the_strategic_gate(self):
        title = "Regional knowledge base and firm efficiency: Evidence from start-ups and fast-growing medium-sized firms"
        abstract = (
            "We study how the regional knowledge base affects firm efficiency, using access to local capabilities, "
            "dependence on regional resources and the resilience of technological capabilities across European regions."
        )
        ok, _a, _b = scan.implied_strategic_context(f"{title}. {abstract}")
        self.assertFalse(ok)

    def test_retired_non_ri_subjects_still_fail_centrality(self):
        for title, abstract in (
            ("Lunar governance tabletop exercise explores engaging stakeholders in space resource rules", "ESPI convened a tabletop exercise on lunar governance, engaging participants on space resource rules."),
            ("Dramatherapy and wellbeing outcomes in community settings", "This study evaluates dramatherapy sessions and participant wellbeing in community settings."),
        ):
            with self.subTest(title=title[:50]):
                ok, _reason, _hits = scan.eu_ri_centrality(title, abstract, "")
                self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
