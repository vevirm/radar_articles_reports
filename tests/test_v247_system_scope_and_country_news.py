"""Regression tests for the v24.7 semantic/source-discovery repair.

The mission is to observe European R&I as a strategic system. Internal European state-variable
changes are admissible even without geopolitical vocabulary; retrieval/source prestige never
substitutes for an R&I-system relationship.
"""
from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_v247_scope", SCAN)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)


class V247SystemScopeAndCountryNews(unittest.TestCase):
    def gate(self, title, abstract, *, kind="scholarly", tier=1):
        return S.gate_scope(title, abstract, "", tier, kind)

    def c_admitted(self, headline, desc, source, domain, link="https://example.test/item"):
        row = {
            "headline": headline,
            "_desc": desc,
            "source": source,
            "source_domain": domain,
            "link": link,
            "date": "2026-09-10",
            "_themes": list(S.themes_for(f"{headline}. {desc}")),
        }
        diagnostics = []
        out = S.anchor_news([row], [], diagnostics, allow_unanchored=True)
        return bool(out), diagnostics

    def test_internal_european_deep_tech_financing_gap_is_A(self):
        row = self.gate(
            "Deep-tech scale-up financing gap in Europe",
            "We benchmark venture and growth capital availability for European deep-tech firms "
            "against the United States and analyse implications for scale-up capacity.",
        )
        self.assertTrue(row["a_pass"], row)

    def test_doctoral_candidate_wellbeing_does_not_become_A(self):
        row = self.gate(
            "Mental health of doctoral candidates in European universities",
            "We survey doctoral candidates across ten European countries and analyse depression, "
            "stress and wellbeing.",
        )
        self.assertFalse(row["a_pass"], row)

    def test_incidental_innovation_performance_does_not_become_A(self):
        row = self.gate(
            "Green bond issuance and firm value: evidence from European listed companies",
            "Using panel data on European listed companies, we find innovation performance "
            "moderates the relationship between green bond issuance and firm value.",
        )
        self.assertFalse(row["a_pass"], row)

    def test_sectoral_innovation_ecosystem_does_not_become_A(self):
        row = self.gate(
            "Innovation ecosystems and wine cooperatives in Southern Europe",
            "This study analyses innovation ecosystems surrounding wine cooperatives in Spain, "
            "Italy and Portugal.",
        )
        self.assertFalse(row["a_pass"], row)

    def test_european_technology_standard_setting_capacity_is_A(self):
        row = self.gate(
            "European leadership in ISO/IEC artificial intelligence standards committees",
            "We map European participation and leadership in ISO/IEC AI technical committees and "
            "compare representation with the United States and China.",
        )
        self.assertTrue(row["a_pass"], row)

    def test_roadmapping_review_is_B(self):
        row = self.gate(
            "Technology roadmapping: a review of approaches",
            "This paper reviews technology roadmapping approaches, synthesises methodological "
            "designs and compares their strengths and limitations.",
        )
        self.assertTrue(row["b_pass"], row)

    def test_scenario_planning_and_firm_performance_is_not_B(self):
        row = self.gate(
            "Scenario planning and firm performance",
            "This paper studies whether using scenario planning improves firm performance.",
        )
        self.assertFalse(row["b_pass"], row)

    def test_recruiting_story_is_not_mistaken_for_job_ad(self):
        self.assertFalse(S.routine_signal_noise(
            "China is recruiting researchers from European universities through state-sponsored talent programmes",
            "The programme offers relocation grants and laboratory funding to researchers currently "
            "working at European universities.",
        ))

    def test_actual_job_ad_remains_noise(self):
        self.assertTrue(S.routine_signal_noise(
            "Postdoctoral researcher position in quantum technologies",
            "Applications are invited for a full-time postdoctoral position. Application deadline 30 September.",
        ))

    def test_workshop_word_does_not_poison_formal_policy_event(self):
        ok, diagnostics = self.c_admitted(
            "Council adopts position on European Research Area Act",
            "After a workshop with stakeholders, the Council adopted its position on the European "
            "Research Area Act, changing governance and research-career provisions ahead of negotiations.",
            "Reuters", "reuters.com",
        )
        self.assertTrue(ok, diagnostics)

    def test_youtube_no_not_youtube(self):
        # Guard the configured-source helper and the new national-media source universe.
        names = {str(x.get("name")) for x in S.configured_c_news_sources()}
        self.assertIn("Yle News", names)
        self.assertNotIn("YouTube", names)

    def test_yle_google_finland_investment_is_C(self):
        ok, diagnostics = self.c_admitted(
            "Google announces €13bn additional investment in Finland",
            "Google announced an additional €13 billion investment in Finland to expand data centres "
            "and AI infrastructure, its largest investment in Europe.",
            "Yle News", "yle.fi", "https://yle.fi/a/74-20245301",
        )
        self.assertTrue(ok, diagnostics)

    def test_dialogue_without_change_is_not_C(self):
        ok, diagnostics = self.c_admitted(
            "Commissioner leads dialogue on how to attract and retain research talent in Europe",
            "The Commissioner met stakeholders for a dialogue on how Europe can attract and retain "
            "research talent. Participants discussed ideas and future options.",
            "ERA Portal Austria", "era.gv.at",
        )
        self.assertFalse(ok, diagnostics)

    def test_eu_ai_data_centre_commitment_is_C(self):
        ok, diagnostics = self.c_admitted(
            "EU launches €30B push to build 7 massive AI data centers",
            "The programme launches seven AI data centres as new European compute capacity.",
            "Politico Europe", "politico.eu",
        )
        self.assertTrue(ok, diagnostics)

    def test_member_state_ai_factory_is_C(self):
        ok, diagnostics = self.c_admitted(
            "Baltics' first AI factory to open in Estonia",
            "Estonia is opening the Baltic region's first AI factory to add computing capacity for research and companies.",
            "ERR News", "err.ee",
        )
        self.assertTrue(ok, diagnostics)

    def test_explicit_europe_sovereign_ai_financing_move_is_C(self):
        ok, diagnostics = self.c_admitted(
            "Mistral bags €3B to build Europe's sovereign AI champion",
            "The financing will expand European AI model and compute capability.",
            "The Register", "theregister.com",
        )
        self.assertTrue(ok, diagnostics)

    def test_europe_plan_without_realised_change_still_is_not_C(self):
        ok, diagnostics = self.c_admitted(
            "Europe looks to challenge US dominance in space sector with €10 billion plan",
            "Officials are considering a plan that could support future European space technology capacity.",
            "France 24", "france24.com",
        )
        self.assertFalse(ok, diagnostics)

    def test_C_pre_novelty_cap_is_not_publication_cap(self):
        self.assertGreaterEqual(int(S.CONFIG.get("c_pre_novelty_candidate_cap", 0)), 20)
        self.assertLessEqual(int(S.CONFIG.get("c_min_new_per_successful_scan", 3)), 3)


if __name__ == "__main__":
    unittest.main()
