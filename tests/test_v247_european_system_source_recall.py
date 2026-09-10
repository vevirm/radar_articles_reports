from pathlib import Path
import importlib.util
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_v247", SCAN)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)


class V247EuropeanSystemAndSourceRecallTests(unittest.TestCase):
    def gate(self, title, abstract="", kind="scholarly", tier=2):
        return S.gate_scope(title, abstract, "", tier, source_kind=kind)

    def signal(self, headline, desc, source="Yle News", domain="yle.fi", link="https://example.test/item"):
        return {
            "headline": headline,
            "_desc": desc,
            "source": source,
            "source_domain": domain,
            "link": link,
            "date": "2026-09-10",
            "_themes": list(S.themes_for(f"{headline}. {desc}")),
        }

    # A: a state-variable word is evidence vocabulary, never admission by itself.
    def test_a_rejects_doctoral_mental_health_without_system_capacity_relation(self):
        ev = self.gate(
            "Mental health of doctoral candidates in European universities",
            "A survey measures anxiety, wellbeing and depression among doctoral candidates across European universities.",
        )
        self.assertFalse(ev["a_pass"], ev)

    def test_a_rejects_incidental_innovation_performance(self):
        ev = self.gate(
            "Green bond issuance and firm value: evidence from European listed companies",
            "We estimate the effect of green bond issuance on firm value; innovation performance is included as a moderator.",
        )
        self.assertFalse(ev["a_pass"], ev)

    def test_a_rejects_local_sector_innovation_ecosystem(self):
        ev = self.gate(
            "Innovation ecosystems and wine cooperatives in Southern Europe",
            "The article studies local wine cooperatives, business networks and product innovation in selected regions.",
        )
        self.assertFalse(ev["a_pass"], ev)

    def test_a_keeps_european_standard_setting_capacity(self):
        ev = self.gate(
            "European leadership in ISO/IEC artificial intelligence committees",
            "The study measures European participation, chairing roles and standards influence in ISO/IEC technical committees for artificial intelligence.",
        )
        self.assertTrue(ev["a_pass"], ev)

    def test_a_keeps_ri_financing_gap_but_not_generic_investment(self):
        good = self.gate(
            "Europe's deep-tech scale-up financing gap",
            "The report measures growth-capital availability for European R&D-based firms and the relocation consequences of late-stage financing constraints.",
            kind="institutional",
        )
        bad = self.gate(
            "Foreign direct investment and employment in Europe",
            "The paper estimates aggregate foreign investment and employment effects across service industries.",
        )
        self.assertTrue(good["a_pass"], good)
        self.assertFalse(bad["a_pass"], bad)

    # B: the foresight method must itself be the research object.
    def test_b_keeps_technology_roadmapping_review(self):
        ev = self.gate(
            "Technology roadmapping: a review of approaches",
            "This article reviews technology-roadmapping approaches and synthesises methodological design choices and validation criteria.",
        )
        self.assertTrue(ev["b_pass"], ev)

    def test_b_rejects_scenario_planning_and_firm_performance(self):
        ev = self.gate(
            "Scenario planning and firm performance",
            "We test whether firms that use scenario planning have higher financial and innovation performance.",
        )
        self.assertFalse(ev["b_pass"], ev)

    def test_b_domain_does_not_veto_real_method_review(self):
        ev = self.gate(
            "Horizon scanning for forest pests: a methodological review",
            "We review, compare and validate horizon-scanning methods for early-signal identification, using forest pests as the empirical case.",
        )
        self.assertTrue(ev["b_pass"], ev)

    # C: collection noise must be structural rather than keyword poisoning.
    def test_c_foreign_recruitment_of_european_researchers_is_not_job_ad_noise(self):
        h = "China launches programme recruiting researchers from European universities"
        d = "A state-sponsored programme is recruiting senior semiconductor researchers from European universities with new laboratory funding."
        self.assertFalse(S.routine_signal_noise(h, d))
        self.assertTrue(S.factual_news(h, d))

    def test_c_real_job_ad_still_rejected(self):
        h = "Postdoctoral researcher position in quantum technologies"
        d = "Applications are invited for a full-time position. Apply by 30 September; salary and job requirements are listed."
        self.assertTrue(S.routine_signal_noise(h, d))

    def test_c_workshop_word_does_not_poison_substantive_policy_event(self):
        h = "Council adopts position on European Research Area Act"
        d = "The Council adopted its position on the European Research Area Act after consultations that included a stakeholder workshop."
        self.assertFalse(S.routine_signal_noise(h, d))

    def test_c_event_listing_workshop_still_rejected(self):
        h = "Workshop on Europe's quantum future"
        d = "Register for the workshop. Speakers, venue and agenda are available online."
        self.assertTrue(S.routine_signal_noise(h, d))

    def test_c_y_le_finland_compute_investment_can_enter(self):
        h = "Google announces €13bn additional investment in Finland"
        d = "Google announced €13 billion additional investment in Finland over the next two years, focused on data centres and AI infrastructure. The investment confirms plans for new data centres will go ahead."
        diagnostics = []
        out = S.anchor_news([self.signal(h, d)], [], diagnostics, allow_unanchored=True)
        self.assertEqual(len(out), 1, diagnostics)
        self.assertIn("compute infrastructure", out[0]["why_it_matters"])

    def test_c_innovation_act_formal_proposal_can_enter(self):
        h = "EU Innovation Act aims to boost growth of R&D-based companies"
        d = "The European Commission unveiled the Innovation Act, including new rules on R&D procurement, intellectual property valuation and testing innovations under lighter rules."
        diagnostics = []
        out = S.anchor_news([
            self.signal(h, d, "Research Professional News", "researchprofessionalnews.com")
        ], [], diagnostics, allow_unanchored=True)
        self.assertEqual(len(out), 1, diagnostics)
        self.assertIn("procuring", out[0]["why_it_matters"])

    def test_c_horizon_vote_delay_can_enter(self):
        h = "Parliament spending-rules dispute delays vote on Horizon Europe"
        d = "The European Parliament postponed votes on the next Horizon Europe programme. The Horizon Europe vote was pushed to November amid a dispute over EU-wide spending rules."
        diagnostics = []
        out = S.anchor_news([
            self.signal(h, d, "Science|Business", "sciencebusiness.net")
        ], [], diagnostics, allow_unanchored=True)
        self.assertEqual(len(out), 1, diagnostics)
        self.assertIn("timing", out[0]["why_it_matters"])

    def test_c_dialogue_only_is_not_a_change(self):
        h = "Commissioner leads dialogue on how to attract and retain research talent in Europe"
        d = "The Commissioner led a stakeholder dialogue on attracting and retaining research talent. Participants discussed ideas and future options."
        diagnostics = []
        out = S.anchor_news([
            self.signal(h, d, "ERA Portal Austria", "era.gv.at")
        ], [], diagnostics, allow_unanchored=True)
        self.assertEqual(out, [], diagnostics)

    def test_c_claim_extractor_prefers_decision_over_aspiration(self):
        h = "Macron and von der Leyen call for stronger European space sector"
        d = "Europe is seeking to strengthen its space industry. The EU decided last month to accelerate IRIS² by expanding it to more than 350 satellites."
        what = S._signal_what_claim(d, h)
        self.assertIn("decided", what.lower())
        self.assertIn("350 satellites", what.lower())
        self.assertNotIn("seeking to strengthen", what.lower())

    def test_country_news_queries_do_not_require_europe_wording(self):
        qs = S.country_news_queries("yle.fi", "Finland", 72)
        self.assertTrue(qs)
        joined = " ".join(qs).lower()
        self.assertIn("finland", joined)
        self.assertIn("data centre", joined)
        # Country-local discovery is deliberately allowed to find internally worded events.
        self.assertNotIn('"europe"', joined)

    def test_y_le_is_configured_as_public_service_and_direct_source(self):
        rows = [x for x in S.CONFIG.get("country_news_sources", []) if x.get("domain") == "yle.fi"]
        self.assertTrue(rows)
        self.assertEqual(rows[0].get("role"), "public_service")
        direct = [x for x in S.CONFIG.get("direct_news_sources", []) if x.get("domain") == "yle.fi"]
        self.assertTrue(direct)
        self.assertIn("/a/", direct[0].get("path_hints", []))


    def test_high_quality_international_primary_sources_are_trusted_without_extra_news_lane(self):
        rows = {x.get("domain"): x for x in S.configured_c_news_sources()}
        self.assertIn("nato.int", rows)
        self.assertIn("oecd.org", rows)
        self.assertIn("esa.int", rows)
        self.assertEqual(rows["nato.int"].get("role"), "official_primary")

    def test_anchor_news_is_not_truncated_to_six_before_novelty(self):
        cases = [
            ("Finland announces €13 billion investment in AI data centres", "Finland announced €13 billion investment in AI data centres and compute infrastructure, expanding technology capacity."),
            ("Germany opens new quantum research facility", "Germany opened a new quantum research facility with federal funding to expand national quantum technology capacity."),
            ("France funds semiconductor pilot line", "France allocated €2 billion to a semiconductor research pilot line to expand chip technology capacity."),
            ("Sweden launches researcher return programme", "Sweden launched a funded programme to attract and retain researchers in strategic technologies."),
            ("Netherlands expands biotechnology research infrastructure", "The Netherlands invested €1 billion to expand biotechnology laboratories and research infrastructure."),
            ("Spain approves new supercomputer expansion", "Spain approved funding to expand national supercomputer and high-performance computing capacity."),
            ("Ireland increases public R&D funding", "Ireland increased public R&D funding for university research and strategic technology programmes."),
        ]
        rows = [self.signal(h, d, link=f"https://example.test/{i}") for i, (h, d) in enumerate(cases, 1)]
        diagnostics = []
        out = S.anchor_news(rows, [], diagnostics, allow_unanchored=True)
        self.assertGreaterEqual(len(out), 7, diagnostics)


if __name__ == "__main__":
    unittest.main()
