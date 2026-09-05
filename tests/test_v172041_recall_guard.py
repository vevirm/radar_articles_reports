"""V17.20.41 recall guard.

Every precision release adds tests asserting that a specific false positive stays out.
Nothing asserted that the corpus's own true positives stay *in*, so successive precision
patches were free to tighten the admission vocabulary past the evidence the scanner had
already accepted. Between v17.20.37 and v17.20.39 that is what happened: daily Strand-A
yield fell from ~76 to ~15 at unchanged scan frequency, and 22% of the live corpus would
no longer have been admitted by the code that was shipping.

These tests are the missing direction. They do not weaken any precision rule; they assert
that the scanner cannot contradict itself, and that the live corpus stays admissible.
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

# Measured at 14.5% on the v17.20.41 corpus. The margin absorbs ordinary drift from
# retirements and future precision work; a genuine recall collapse blows straight past it.
MAX_CORPUS_REJECTION_RATE = 0.25


class VocabularyDriftTests(unittest.TestCase):
    """The recording vocabulary and the admission vocabulary must not diverge."""

    def test_admission_mechanisms_cover_recording_mechanisms(self):
        missing = [t for t in scan.A_TECH_RI_MECHANISMS if t not in scan.A_CENTRAL_TECH_RI_MECHANISMS]
        self.assertEqual(
            missing, [],
            "_ri_hits() can record R&I evidence that _central_ri_hits() cannot reproduce, "
            "so eu_ri_centrality() would reject records the scanner itself evidenced. "
            f"Unreachable mechanism terms: {missing}",
        )

    def test_major_ri_system_terms_are_admissible_subjects(self):
        """A term good enough for the major-focus gate must not be invisible to centrality."""
        for term in ("deep tech", "technology transfer", "brain drain", "research security"):
            with self.subTest(term=term):
                self.assertIn(term, scan.A_MAJOR_RI_SYSTEM)
                sentence = f"European {term} policy and strategic autonomy in research and innovation."
                self.assertTrue(
                    scan._central_ri_hits(sentence),
                    f"'{term}' is a major R&I system term but establishes no centrality.",
                )

    def test_recorded_evidence_is_always_reproducible_by_the_gate(self):
        """Whatever _ri_hits() writes onto a record, the admission gate must also see."""
        sentences = [
            "The EIC Tech Report identifies emerging deep tech signals supporting Europe's "
            "competitiveness in strategic technologies.",
            "European dual-use research coordination under Horizon Europe.",
            "Artificial intelligence innovation capacity across European member states.",
            "Quantum research funding and scale-up commercialisation in the European Union.",
        ]
        for sentence in sentences:
            with self.subTest(sentence=sentence[:60]):
                if scan._ri_hits(sentence):
                    self.assertTrue(
                        scan._central_ri_hits(sentence),
                        "Scanner records R&I evidence here but the admission gate scores zero.",
                    )


class LiveCorpusRecallTests(unittest.TestCase):
    """The shipped corpus must remain admissible under the shipped gate."""

    @classmethod
    def setUpClass(cls):
        doc = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        # Only items the scanner judged on the abstract alone can be re-judged fairly here;
        # for full_text records the body that was actually gated is not retained.
        cls.rows = [r for r in doc.get("strand_a", []) if r.get("text_mode") == "abstract_only"]

    def test_corpus_still_passes_the_centrality_gate(self):
        if len(self.rows) < 50:
            self.skipTest("corpus too small to measure recall")
        rejected = []
        for item in self.rows:
            ok, reason, _hits = scan.eu_ri_centrality(
                item.get("title", "") or "", item.get("summary", "") or "", ""
            )
            if not ok:
                rejected.append((reason, str(item.get("title", ""))[:70]))
        rate = len(rejected) / len(self.rows)
        self.assertLessEqual(
            rate, MAX_CORPUS_REJECTION_RATE,
            f"Admission gate now rejects {rate:.1%} of the live Strand-A corpus "
            f"({len(rejected)}/{len(self.rows)}), above the {MAX_CORPUS_REJECTION_RATE:.0%} "
            f"recall floor. Precision tightening has outrun the evidence base. "
            f"First rejections: {rejected[:5]}",
        )

    def test_horizon_europe_governance_is_not_an_event_recap(self):
        """Association/Joint Committee decisions are primary notices, not event recaps."""
        for title in (
            "Fourth EU-Albania Horizon Europe Joint Research and Innovation Committee meeting",
            "2nd Horizon Europe association Joint Committee meeting between Canada and the European Union",
        ):
            with self.subTest(title=title[:50]):
                _ok, reason, _hits = scan.eu_ri_centrality(
                    title,
                    "The Joint Committee reviewed Horizon Europe association and research and "
                    "innovation cooperation, including research security and researcher mobility.",
                    "",
                )
                self.assertNotEqual(reason, "event_recap_not_substantive_evidence")


class PrecisionHeldTests(unittest.TestCase):
    """The recall repair must not resurrect any retired false positive."""

    def test_generic_capability_language_still_fails_the_strategic_gate(self):
        title = "Regional knowledge base and firm efficiency: Evidence from start-ups and fast-growing medium-sized firms"
        abstract = (
            "We study how the regional knowledge base affects firm efficiency, using access to "
            "local capabilities, dependence on regional resources and the resilience of "
            "technological capabilities across European regions."
        )
        ok, _a, _b = scan.implied_strategic_context(f"{title}. {abstract}")
        self.assertFalse(ok, "v17.20.39 false positive can triangulate a strategic mechanism again.")

    def test_retired_non_ri_subjects_still_fail_centrality(self):
        for title, abstract in (
            ("Lunar governance tabletop exercise explores engaging stakeholders in space resource rules",
             "ESPI convened a tabletop exercise on lunar governance, engaging participants on space resource rules."),
            ("Dramatherapy and wellbeing outcomes in community settings",
             "This study evaluates dramatherapy sessions and participant wellbeing in community settings."),
        ):
            with self.subTest(title=title[:50]):
                ok, _reason, _hits = scan.eu_ri_centrality(title, abstract, "")
                self.assertFalse(ok, "Retired false positive passes centrality again.")


if __name__ == "__main__":
    unittest.main()
