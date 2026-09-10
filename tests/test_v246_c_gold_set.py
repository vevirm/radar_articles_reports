"""Expanded Strand-C gold set for the v24.6 criteria repair.

These cases protect the intended distinction between a material change in an A-relevant
state variable and generic technology/business/news activity. They are semantic fixtures;
production code contains no title allow/deny list for them.
"""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_v246_c_gold", SCAN)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)


class V246ExpandedCGold(unittest.TestCase):
    def admitted(self, headline, desc, source, domain, link, date="2026-08-20"):
        row = {
            "headline": headline,
            "_desc": desc,
            "source": source,
            "source_domain": domain,
            "link": link,
            "date": date,
            "_themes": list(S.themes_for(f"{headline}. {desc}")),
        }
        diagnostics = []
        out = S.anchor_news([row], [], diagnostics, allow_unanchored=True)
        return bool(out), diagnostics

    def assertAdmitted(self, *args):
        ok, diagnostics = self.admitted(*args)
        self.assertTrue(ok, diagnostics)

    def assertRejected(self, *args):
        ok, diagnostics = self.admitted(*args)
        self.assertFalse(ok, diagnostics)

    # --- strong positives: concrete changes to an A-relevant state variable ---
    def test_horizon_association_change(self):
        self.assertAdmitted(
            "Japan and EU sign off Horizon Europe association",
            "Japan and the European Union signed the agreement associating Japan to Horizon Europe, changing participation rights for Japanese researchers in EU-funded research programmes.",
            "Science|Business", "sciencebusiness.net",
            "https://sciencebusiness.net/news/horizon-europe/japan-and-eu-sign-horizon-europe-association", "2026-07-30",
        )

    def test_european_ai_compute_capacity_commitment(self):
        self.assertAdmitted(
            "Europe commits €5 billion to fund seven AI megafactories and catch up with the US and China",
            "The European Union committed €5 billion to seven AI megafactories, expanding European high-performance compute capacity for frontier AI research and development.",
            "Le Monde", "lemonde.fr", "https://www.lemonde.fr/example", "2026-07-31",
        )

    def test_external_research_collaboration_restriction(self):
        self.assertAdmitted(
            "US politicians push agencies to restrict research collaboration with China",
            "US lawmakers are pressing federal science agencies to restrict research collaboration with Chinese institutions in sensitive technology fields, potentially segmenting international scientific networks.",
            "Nature", "nature.com", "https://www.nature.com/example", "2026-07-16",
        )

    def test_member_state_research_security_tightening(self):
        self.assertAdmitted(
            "Netherlands tightens screening of researchers in sensitive technologies",
            "The Dutch government tightened screening rules for researchers seeking access to sensitive semiconductor and quantum research at universities.",
            "Reuters", "reuters.com", "https://www.reuters.com/example-research-screening", "2026-09-01",
        )

    def test_eu_research_budget_position(self):
        self.assertAdmitted(
            "Council adopts negotiating position on €180B Horizon Europe budget",
            "The Council adopted its negotiating position for the next EU research framework programme, setting a €180 billion Horizon Europe budget and changing funding priorities.",
            "Reuters", "reuters.com", "https://www.reuters.com/example-horizon-budget", "2026-09-02",
        )

    # --- strong negatives: technology/business activity is not automatically a C signal ---
    def test_foreign_quantum_product_news(self):
        self.assertRejected(
            "IBM links cryogenic modules to scale fault-tolerant quantum computing",
            "IBM introduced new cryogenic control modules intended to improve the scaling of fault-tolerant quantum computers for enterprise and research users.",
            "eeNews Europe", "eenewseurope.com", "https://www.eenewseurope.com/example-ibm", "2026-08-21",
        )

    def test_foreign_enterprise_quantum_deal(self):
        self.assertRejected(
            "AT&T expands D-Wave quantum computing deal for AI-driven network optimisation",
            "AT&T expanded its commercial agreement with D-Wave to use quantum computing for network optimisation and enterprise AI applications in the United States.",
            "eeNews Europe", "eenewseurope.com", "https://www.eenewseurope.com/example-att", "2026-07-29",
        )

    def test_generic_foreign_data_centre(self):
        self.assertRejected(
            "Company opens a new AI data centre in Texas",
            "A cloud company opened a 20MW data centre in Texas for ordinary enterprise AI services.",
            "Reuters", "reuters.com", "https://www.reuters.com/example-data-centre", "2026-08-20",
        )

    def test_archive_page_is_not_signal(self):
        self.assertRejected(
            "Semiconductors Archives | Center for Security and Emerging Technology",
            "The place to find CSET publications, reports and people on semiconductors.",
            "CSET", "cset.georgetown.edu", "https://cset.georgetown.edu/topic/semiconductors/", "2026-07-13",
        )

    def test_event_landing_page_is_not_signal(self):
        self.assertRejected(
            "Plug & Play Taiwan | From Breakthrough to Scale: The Next Wave of Semiconductor Innovation | imec",
            "This event explores frontier technologies and Taiwan manufacturing. Join us for speakers, networking, registration and the event agenda.",
            "imec", "imec-int.com", "https://www.imec-int.com/events/example", "2026-08-12",
        )

    def test_operational_compute_tender_is_not_signal(self):
        self.assertRejected(
            "Acquisition, Delivery, Installation and Hardware and Software Maintenance of INNOVATE Industrial Grade Supercomputer",
            "Invitation to tender for acquisition, delivery, installation and maintenance of an industrial-grade supercomputer.",
            "EuroHPC Joint Undertaking", "eurohpc-ju.europa.eu", "https://www.eurohpc-ju.europa.eu/document/example.pdf", "2026-07-16",
        )


if __name__ == "__main__":
    unittest.main()
