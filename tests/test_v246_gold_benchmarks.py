"""Curator-provided gold benchmarks for the v24.6 A/B/C criteria repair.

These are decision-boundary tests, not title allow/deny lists.  The production gate never
sees this fixture.  Each case encodes the semantic reason the curator supplied on 2026-09-10.
"""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_v246_gold", SCAN)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)


class V246GoldBenchmarks(unittest.TestCase):
    def gate(self, title: str, abstract: str = ""):
        return S.gate_scope(title, abstract, "", 2, source_kind="scholarly")

    def c_admitted(self, headline: str, desc: str, source: str, domain: str, link: str, date: str) -> tuple[bool, list[dict]]:
        row = {
            "headline": headline,
            "_desc": desc,
            "source": source,
            "source_domain": domain,
            "link": link,
            "date": date,
            "_themes": list(S.themes_for(f"{headline}. {desc}")),
        }
        diagnostics: list[dict] = []
        out = S.anchor_news([row], [], diagnostics, allow_unanchored=True)
        return bool(out), diagnostics

    # --- A: evidence about the European R&I system, not any European outcome of innovation ---
    def test_a_lewandowska_public_support_in_eu_smes_is_in(self):
        ev = self.gate(
            "From funding to competitiveness: the innovation effects of public support in European Union SMEs",
            "This study examines how public financial support for innovative activity translates into SMEs' innovation outcomes and competitiveness. Using Community Innovation Survey microdata from 84,115 SMEs in 12 European Union countries, we estimate a path model linking public funding to R&D investment, innovation cooperation and innovation performance.",
        )
        self.assertTrue(ev["a_pass"], ev)

    def test_a_minniti_ai_labor_market_outcome_is_out(self):
        ev = self.gate(
            "AI innovation and labor market polarization: Evidence from European regions",
            "We study whether AI innovation changes labor-market polarization by weakening the relative position of high-skilled workers. We test the model's predictions using European regional labor-market data and find that AI reduces the relative wage-cost ratio through wage and employment margins.",
        )
        self.assertFalse(ev["a_pass"], ev)

    def test_a_raza_eu_competitiveness_geopolitics_is_in(self):
        ev = self.gate(
            "Competitiveness in the age of geopolitics: What agenda does the EU really need?",
            "We scrutinize the debate on European competitiveness diagnosed by the Draghi Report. We compare competitiveness indicators for the European Union and United States, identify an innovation gap in high-tech services and energy dependencies, and conclude that targeted public investment and mission-oriented industrial policies are needed.",
        )
        self.assertTrue(ev["a_pass"], ev)
        self.assertEqual(ev["a_route"], "explicit-geopolitics")

    def test_a_smit_multilingual_research_practice_is_out(self):
        ev = self.gate(
            "Multilingualism in action in a European University Alliance: an exploratory survey of the roles of English and other languages for research purposes",
            "The findings show that English is complemented by other languages used for research activities. European University Alliances position multilingualism as a value, but their policies centre on language learning rather than language use. The study concerns multilingual research practices and language policy.",
        )
        self.assertFalse(ev["a_pass"], ev)

    # --- B: futures/foresight method or practice construct must itself be the research object ---
    def test_b_assefa_water_scenario_application_is_out(self):
        ev = self.gate(
            "Water storage gap in the Tana-Beles sub-basin, Upper Blue Nile, Ethiopia",
            "Properly planning diverse water storage options requires an assessment framework. We developed a framework for assessing water storage gaps under current and future scenarios. It is applied in the Tana-Beles sub-basin of Ethiopia.",
        )
        self.assertFalse(ev["b_pass"], ev)

    def test_b_gaspar_futures_literacy_measurement_is_in(self):
        ev = self.gate(
            "Mapping futures literacy as a competence space: structure, measuring and empirical patterns",
            "Futures literacy has gained attention as a key concept in futures studies, but its empirical operationalisation and measurement remain underdeveloped. This paper conceptualises futures literacy as a competence space and examines how its structure can be explored empirically. The aim is to contribute to conceptualisation, measurement, and empirical testing of futures literacy.",
        )
        self.assertTrue(ev["b_pass"], ev)
        self.assertEqual(ev["b_route"], "future-method-study")

    def test_b_jiang_delphi_bias_method_critique_is_in(self):
        ev = self.gate(
            "Bias in expert judgment within large-scale science and technology Delphis: What do we know (and not know) and can utilization of panelists' rationales help reduce potential bias?",
            "We offer a critique of prior work on biases in expert judgments in large-scale S&T Delphi surveys. We argue that the prior authors misunderstand the purpose of Delphi applications and the concept of bias, and assess the relevance of proposed remedial interventions for expert bias in large-scale Science & Technology Delphi applications.",
        )
        self.assertTrue(ev["b_pass"], ev)
        self.assertEqual(ev["b_route"], "future-method-study")

    def test_b_zackery_public_library_foresight_application_is_out(self):
        ev = self.gate(
            "An investigation of the alternative futures of public libraries in 2030: a case study from the Global South",
            "Participatory action research and future-oriented action research were deployed. Horizon and environmental scanning, SWOT analysis, foresight workshops, surveys and interviews were used to conduct the research. The authors provide four scenarios of the future of public libraries in Iran in 2030 and recommendations based on those scenarios.",
        )
        self.assertFalse(ev["b_pass"], ev)

    # --- C: a material new change in an A-relevant variable, not generic tech/business movement ---
    def test_c_erc_external_applications_rise_is_in(self):
        admitted, diagnostics = self.c_admitted(
            "Sharp rise in ERC advanced grant applications from outside Europe",
            "The number of scientists outside Europe who won a European Research Council grant has more than doubled following the launch of Choose Europe for Science. The ERC reported a sharp rise in applications from researchers outside the EU, and researchers relocating to Europe can request additional funding to establish a laboratory and research team in Europe.",
            "Research Professional News",
            "researchprofessionalnews.com",
            "https://www.researchprofessionalnews.com/example-erc-external-applications",
            "2026-06-23",
        )
        self.assertTrue(admitted, diagnostics)

    def test_c_horizon_budget_proposal_is_in(self):
        admitted, diagnostics = self.c_admitted(
            "Council presidency proposes €167B Horizon Europe budget",
            "The Cypriot presidency of the EU Council published figures for talks on the EU budget for 2028-34. The negotiating box proposes €167.9 billion for Horizon Europe, below the Commission proposal, with cuts to research and technology funding.",
            "Science|Business",
            "sciencebusiness.net",
            "https://sciencebusiness.net/news/horizon-europe/council-presidency-proposes-eu167b-horizon-europe-budget",
            "2026-06-11",
        )
        self.assertTrue(admitted, diagnostics)

    def test_c_ey_enterprise_quantum_deployment_is_out(self):
        admitted, diagnostics = self.c_admitted(
            "EY expands quantum computing with on-site system for enterprise AI",
            "EY is expanding its quantum computing capabilities with an on-site quantum computer at EY Canada, part of the professional services firm's investment in AI and next-generation technologies. The infrastructure supports enterprise workloads and practical deployment.",
            "eeNews Europe",
            "eenewseurope.com",
            "https://www.eenewseurope.com/en/ey-expands-quantum-computing-with-on-site-system-for-enterprise-ai/",
            "2026-07-30",
        )
        self.assertFalse(admitted, diagnostics)

    def test_c_hong_kong_biotech_fund_is_out(self):
        admitted, diagnostics = self.c_admitted(
            "Sugar for the pill: US$8b fund boosts Hong Kong's biotech hub ambitions",
            "Hong Kong is stepping up investment in biotech companies, positioning itself in Beijing's challenge to US pharmaceutical dominance. Hong Kong Investment Corporation manages about US$8 billion and has built a biotech and health technology investment portfolio to transform the city into a global biotech hub.",
            "South China Morning Post",
            "scmp.com",
            "https://www.scmp.com/business/china-business/article/3363320/us-china-pharma-rivalry-heats-can-hong-kongs-us8b-fund-be-global-bridge",
            "2026-08-07",
        )
        self.assertFalse(admitted, diagnostics)

    def test_c_ey_publisher_brand_europe_is_not_scope(self):
        # Source-faithful regression: the live article contains the phrase
        # "For eeNews Europe readers" even though the event is explicitly at EY Canada.
        # Publisher branding must not manufacture European semantic scope.
        headline = "EY expands quantum computing with on-site system for enterprise AI"
        desc = (
            "EY is expanding its quantum computing capabilities with an on-site quantum computer at EY Canada, "
            "as part of a large investment in AI and next-generation technologies. The system supports enterprise "
            "workloads and practical deployment. For eeNews Europe readers, the announcement is framed as evidence "
            "that large enterprises are moving beyond quantum research and pilot projects."
        )
        row = {
            "headline": headline,
            "_desc": desc,
            "source": "eeNews Europe",
            "source_domain": "eenewseurope.com",
            "link": "https://www.eenewseurope.com/en/ey-expands-quantum-computing-with-on-site-system-for-enterprise-ai/",
            "date": "2026-07-30",
            "_themes": list(S.themes_for(f"{headline}. {desc}")),
        }
        diagnostics = []
        out = S.anchor_news([row], [], diagnostics, allow_unanchored=True)
        self.assertEqual(out, [], diagnostics)
        self.assertEqual(diagnostics[-1]["reason"], "source_not_europe_trusted")



if __name__ == "__main__":
    unittest.main()
