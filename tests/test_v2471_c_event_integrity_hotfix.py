"""Regression tests for the v24.7.1 Strand-C event-integrity hotfix.

The hotfix keeps the v24.7 Europe-first source recall, but makes source-backed event/date
integrity authoritative: sitemap timestamps and standing call pages cannot become C, while
concrete European R&I state-variable changes remain admissible without geopolitical wording.
"""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_v2471", SCAN)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)


class V2471CEventIntegrityHotfix(unittest.TestCase):
    def row(self, headline, desc, source, domain, *, link="https://example.test/item", date_basis="page"):
        return {
            "headline": headline,
            "_desc": desc,
            "source": source,
            "source_domain": domain,
            "link": link,
            "date": "2026-09-10",
            "date_basis": date_basis,
            "_themes": list(S.themes_for(f"{headline}. {desc}")),
        }

    def admit(self, *args, **kwargs):
        diagnostics = []
        out = S.anchor_news([self.row(*args, **kwargs)], [], diagnostics, allow_unanchored=True)
        return out, diagnostics

    def test_sitemap_lastmod_cannot_date_public_signal(self):
        out, diagnostics = self.admit(
            "European programme launches €2bn quantum infrastructure initiative",
            "The programme launched a €2 billion quantum infrastructure initiative for European research.",
            "European Research Executive Agency", "rea.ec.europa.eu",
            link="https://rea.ec.europa.eu/funding-and-grants/example_en",
            date_basis="sitemap_lastmod_approximate",
        )
        self.assertEqual(out, [], diagnostics)
        self.assertIn("approximate_sitemap_date_not_c_event_date", {x["reason"] for x in diagnostics})

    def test_rea_infratech_standing_call_page_is_not_c(self):
        h = "Next generation of scientific instrumentation, tools and methods and advanced digital solutions (INFRATECH)"
        d = ("Apply now. Who should apply. 2025 Call Horizon Europe. This call closed on 18 September 2025. "
             "€140 million overall indicative budget. See all calls on the Funding & Tenders Opportunities Portal. "
             "Deadline for applicants to submit proposals. 47 proposals submitted.")
        self.assertTrue(S.c_standing_funding_or_call_page(
            h, d, "European Research Executive Agency",
            "https://rea.ec.europa.eu/funding-and-grants/horizon-europe-research-infrastructures/infratech_en",
        ))

    def test_rea_reforming_system_call_page_is_not_c(self):
        h = "Reforming and enhancing the EU research and innovation system"
        d = ("2026 call for proposals. This call is closed. 8 topics. €52 million overall indicative budget. "
             "See all calls on the Funding and Tenders Opportunities Portal. Work Programme 2026.")
        out, diagnostics = self.admit(
            h, d, "European Research Executive Agency", "rea.ec.europa.eu",
            link="https://rea.ec.europa.eu/funding-and-grants/horizon-europe-reforming-and-enhancing-european-ri-system/reforming_en",
        )
        self.assertEqual(out, [], diagnostics)
        self.assertIn("standing_funding_call_page_not_c", {x["reason"] for x in diagnostics})

    def test_innovation_act_official_google_news_source_alias_is_c(self):
        out, diagnostics = self.admit(
            "Commission proposes new European Innovation Act to help innovative European ideas grow and compete globally - Shaping Europe’s digital future",
            "The European Commission proposed a new European Innovation Act with rules on R&D procurement, intellectual property valuation and testing innovations.",
            "EU Digital Strategy", "digital-strategy.ec.europa.eu",
            link="https://news.google.com/rss/articles/example?oc=5",
        )
        self.assertEqual(len(out), 1, diagnostics)
        self.assertEqual(out[0]["event_status"], "PROPOSED")

    def test_eu_china_research_cooperation_limited_is_c(self):
        out, diagnostics = self.admit(
            "EU-China research cooperation limited to ‘targeted areas’",
            "The EU limited research cooperation with China to targeted areas amid research-security concerns.",
            "Research Professional News", "researchprofessionalnews.com",
        )
        self.assertEqual(len(out), 1, diagnostics)

    def test_eu_quantum_regulation_delay_is_c(self):
        out, diagnostics = self.admit(
            "EU's first quantum tech regulation delayed by six months",
            "The EU delayed its first quantum technology regulation by six months, affecting rules for the strategic technology sector.",
            "Euractiv", "euractiv.com",
        )
        self.assertEqual(len(out), 1, diagnostics)
        self.assertEqual(out[0]["signal_type"], "contradicts")

    def test_broad_national_source_no_longer_localises_city_headline_into_public_c(self):
        out, diagnostics = self.admit(
            "Intel to invest €5bn in Leixlip campus on next-generation chips to power AI",
            "Intel will invest €5 billion in its Leixlip campus to develop and manufacture next-generation chips for AI.",
            "The Irish Times", "irishtimes.com",
        )
        self.assertEqual(out, [], diagnostics)
        self.assertTrue(any(x.get("reason") == "source_not_europe_trusted" for x in diagnostics), diagnostics)

    def test_country_source_does_not_localise_explicit_foreign_capacity_story(self):
        ok, hits = S.c_country_source_capacity_scope(
            "NVIDIA to invest $1.5bn in US AI packaging plant",
            "The investment will expand US semiconductor packaging capacity.",
            "The Irish Times", "irishtimes.com", "https://irishtimes.com/example",
        )
        self.assertFalse(ok, hits)

    def test_precursor_promotion_requires_realisation_evidence(self):
        self.assertFalse(S.c_precursor_promotion_evidence(
            "Commission updates proposal for a European AI programme",
            "The proposal would allocate €5 billion if adopted.",
        ))
        self.assertTrue(S.c_precursor_promotion_evidence(
            "Council approves European AI programme",
            "The Council approved the programme and funding was awarded.",
        ))

    def test_saved_external_signal_recovers_source_claim_before_radar_inference(self):
        item = {
            "what": "Radar inference: this development could change Europe's technology position / dependency.",
            "signal_note": ("The country stopped submitting TOP500 data after US export controls on advanced computing chips. "
                            "Radar inference: this development could change Europe's technology position / dependency."),
        }
        claim = S.c_saved_source_claim(item)
        self.assertIn("TOP500", claim)
        self.assertNotIn("Radar inference", claim)

    def test_saved_approximate_date_signal_fails_revalidation(self):
        item = {
            "headline": "Reforming and enhancing the EU research and innovation system",
            "source": "European Research Executive Agency",
            "date": "2026-09-02",
            "date_basis": "sitemap_lastmod_approximate",
            "link": "https://rea.ec.europa.eu/funding-and-grants/example_en",
            "event_status": "COMMITTED",
            "what": "2026 call for proposals. This call is closed. €52 million overall indicative budget.",
        }
        self.assertFalse(S._saved_signal_passes(item))


if __name__ == "__main__":
    unittest.main()
