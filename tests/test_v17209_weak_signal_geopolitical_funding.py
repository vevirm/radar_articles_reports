import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_scan_v17209", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class WeakSignalGeopoliticalFundingGateTests(unittest.TestCase):
    def test_generic_erc_grant_announcement_is_not_a_weak_signal(self):
        title = "Starting Grants 2026: Examples of projects"
        desc = (
            "The European Research Council has awarded 421 Starting Grants to early-career "
            "researchers across Europe as part of Horizon Europe."
        )
        self.assertFalse(scan.eu_funding_signal_has_geopolitical_setting(title, desc))
        self.assertFalse(
            scan.institutional_weak_signal_eligible(
                title,
                desc,
                "European Research Council",
                "https://erc.europa.eu/news-events/news/starting-grants-2026-examples-projects",
            )
        )

    def test_eu_funding_with_specific_geopolitical_purpose_can_pass_setting_gate(self):
        title = "EU funds quantum supply-chain projects under economic security strategy"
        desc = (
            "The funding aims to reduce strategic dependencies on non-European suppliers "
            "and strengthen technology sovereignty in critical quantum components."
        )
        self.assertTrue(scan.eu_funding_signal_has_geopolitical_setting(title, desc))

    def test_third_country_research_funding_setting_can_pass(self):
        title = "Horizon Europe opens targeted call with Ukraine"
        desc = (
            "The EU funding call supports research cooperation with Ukraine in a security-sensitive "
            "setting and is part of the Union's science-diplomacy response to Russia's war."
        )
        self.assertTrue(scan.eu_funding_signal_has_geopolitical_setting(title, desc))

    def test_saved_generic_eu_funding_row_is_removed_on_revalidation(self):
        item = {
            "headline": "Starting Grants 2026: Examples of projects",
            "source": "European Research Council",
            "date": "2026-09-03",
            "date_basis": "page",
            "link": "https://erc.europa.eu/news-events/news/starting-grants-2026-examples-projects",
            "anchor": "Research and innovation for the European Green Deal (Strand A)",
            "anchor_basis": "publication",
            "anchor_status": "anchored",
            "signal_note": (
                "The European Research Council has announced 421 Starting Grants across Europe "
                "under Horizon Europe. This could change participation, funding or international "
                "cooperation in EU research programmes."
            ),
            "why_it_matters": "This could change participation, funding or international cooperation in EU research programmes.",
            "strategic_classification": {"primary": "", "lenses": [], "trend_context": []},
            "strategic_classification_source": "source_text",
        }
        self.assertFalse(scan._saved_signal_passes(item))

    def test_foreign_funding_signal_is_not_misread_as_generic_eu_funding(self):
        item = {
            "headline": "Canada invests in quantum supply-chain research",
            "source": "Financial Times",
            "date": "2026-08-28",
            "date_basis": "page",
            "link": "https://example.com/canada-quantum",
            "what": "Canada invests in quantum supply-chain research.",
            "signal_note": (
                "Canada invests in quantum supply-chain research. This may affect Europe's "
                "relative access and capability in quantum technologies."
            ),
            "strategic_classification": {"primary": "opportunity", "lenses": [{"type": "opportunity"}]},
            "strategic_classification_source": "source_text",
        }
        self.assertTrue(scan.saved_eu_funding_signal_has_geopolitical_setting(item))


if __name__ == "__main__":
    unittest.main()
