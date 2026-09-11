from pathlib import Path
import importlib.util
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_v246", SCAN)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)


class V246CriteriaRepairTests(unittest.TestCase):
    def gate(self, title, abstract="", kind="scholarly", tier=2):
        return S.gate_scope(title, abstract, "", tier, source_kind=kind)

    # --- B: method identity first; method itself must be the object ---
    def test_b_rejects_generic_future_research_framework(self):
        ev = self.gate(
            "Mapping organizational capabilities in eco-innovation",
            "We propose an integrative framework and conclude with directions for future research."
        )
        self.assertFalse(ev["b_pass"], ev)

    def test_b_rejects_bare_scenario_engineering(self):
        ev = self.gate(
            "Evaluation of Beamforming Strategies for Enhanced Space-Based ADS-B Signal Detection",
            "Numerical simulations show that performance is scenario dependent. We evaluate the approach across several scenarios."
        )
        self.assertFalse(ev["b_pass"], ev)

    def test_b_rejects_stock_prediction_with_future_research(self):
        ev = self.gate(
            "Modeling Inter-Firm Dependencies with Temporal Graph Neural Networks for Stock Price Prediction",
            "We develop a framework for stock-price prediction and discuss limitations and future research directions."
        )
        self.assertFalse(ev["b_pass"], ev)

    def test_b_rejects_health_technology_assessment_homonym(self):
        ev = self.gate(
            "Methods for Evaluating Usability in Healthcare Technology Assessment: A Critical Literature Review",
            "This review compares methods used in health technology assessment and discusses their limitations."
        )
        self.assertFalse(ev["b_pass"], ev)

    def test_b_rejects_application_of_foresight_without_method_contribution(self):
        ev = self.gate(
            "Utilizing the Foresight Methodology and Delphi Method to Assess Innovation Effectiveness in Advancing Bulgaria's Green Deal Objectives",
            "Strategic foresight and Delphi are used as tools for informed decision making in the green transition."
        )
        self.assertFalse(ev["b_pass"], ev)

    def test_b_keeps_real_method_development(self):
        ev = self.gate(
            "Mission-oriented scenarios: A new method for urban foresight",
            "We develop and validate a reusable scenario method and discuss its design principles and transferability."
        )
        self.assertTrue(ev["b_pass"], ev)

    def test_b_keeps_nominal_delphi_quality_question_without_extra_action_verb(self):
        ev = self.gate(
            "Bias in Expert Judgment Within Large-Scale Science and Technology Delphis: What Do We Know (and Not Know) and Can Utilization of Panelists' Rationales Help Reduce Potential Bias?",
            "We offer a critique of prior work on biases in expert judgments in large-scale S&T Delphi surveys. The prior authors misunderstand both the purpose of Delphi applications and the concept of bias."
        )
        self.assertTrue(ev["b_pass"], ev)
        self.assertEqual(ev["b_route"], "future-method-study")

    def test_b_rejects_domain_scenario_framework_without_independent_method_claim(self):
        ev = self.gate(
            "Fueling Tomorrow: Scenario Planning for the Future of Gas Stations",
            "This study recenters gas stations as sociotechnical transition actors and develops a traceable, design-integrated scenario approach to derive place-based transition pathways. The scenarios support policy-industry coordination for gas-station transition decisions."
        )
        self.assertFalse(ev["b_pass"], ev)

    def test_b_keeps_case_developed_method_when_replicability_is_explicit(self):
        ev = self.gate(
            "Bridging foresight and transition theory: policy mixes for transforming Europe’s food systems",
            "The paper asks how participatory foresight tools and transition research frameworks can be combined into a replicable methodology for developing internally coherent policy mixes."
        )
        self.assertTrue(ev["b_pass"], ev)

    def test_b_keeps_conceptual_foresight_method_framework(self):
        ev = self.gate(
            "Governance logics and foresight functions: European strategic foresight in contrastive perspective",
            "The purpose of the article is to develop a governance-sensitive framework that links foresight methods to institutional functions in public decision-making."
        )
        self.assertTrue(ev["b_pass"], ev)

    def test_b_keeps_horizon_scanning_methodology_review_even_with_domain(self):
        ev = self.gate(
            "Scientific foundations of Horizon Scanning methodology for early signal identification in healthcare",
            "The article presents a systematic analysis of contemporary international approaches to the application of Horizon Scanning methodology in healthcare and the pharmaceutical sector."
        )
        self.assertTrue(ev["b_pass"], ev)

    def test_b_keeps_framework_testing_when_methodology_is_explicit_object(self):
        ev = self.gate(
            "A sectoral strategic roadmapping framework for combining regulatory and industry perspectives: the case of Advanced Air Mobility in Canada",
            "This paper presents a sectoral roadmap development framework-testing process to evaluate a methodology for expanding technological roadmaps into comprehensive sectoral frameworks."
        )
        self.assertTrue(ev["b_pass"], ev)

    def test_b_keeps_reusable_technology_intelligence_system_method(self):
        ev = self.gate(
            "A Multi-agent Approach to Technology Intelligence: From Patents to Market Signals with Large Language Models",
            "Technology Intelligence gives decision-makers awareness of technological trends, opportunities and threats. This paper presents TechIntel-MAS, an eight-role multi-agent system that transforms patent and market evidence into technology signals."
        )
        self.assertTrue(ev["b_pass"], ev)
        self.assertEqual(ev["b_route"], "ri-futures-analytic-method")

    def test_b_keeps_explicit_new_regional_foresight_methodology_despite_application_shaped_title(self):
        ev = self.gate(
            "Foresight for regional policy: technological and regional fit",
            "The purpose of this paper is to propose and discuss a new regional foresight methodology. Its value is as a tool to suggest policies and R&D investments."
        )
        self.assertTrue(ev["b_pass"], ev)

    def test_b_keeps_foresight_as_policy_infrastructure_conceptual_study(self):
        ev = self.gate(
            "Strategic Foresight as Policy Infrastructure for Financial Governance: A Multi-Layered Framework for Anticipatory Policymaking in Emerging Economies",
            "This article develops a multi-layered framework for understanding how strategic foresight can function as a form of policy infrastructure within financial governance systems. The paper also outlines exploratory scenarios for Iran in 2030."
        )
        self.assertTrue(ev["b_pass"], ev)
        self.assertTrue(ev["method_bridge"], ev)

    def test_b_rejects_corporate_foresight_outcome_model_where_role_belongs_to_another_variable(self):
        # Corpus regression: "foresight ... role" used to be read across the title even
        # though "mediating role" grammatically belongs to innovation culture. This paper
        # studies the organisational effect of using corporate foresight, not foresight
        # methodology itself.
        ev = self.gate(
            "Corporate Foresight and Innovation: The Mediating Role of Innovation Culture and the Moderating Effect of Environmental Uncertainty",
            "This manuscript asks how corporate foresight relates to new product portfolio innovativeness. To adapt to a swiftly evolving and unpredictable world, business leaders have strengthened strategic planning approaches by incorporating corporate foresight to support innovation."
        )
        self.assertFalse(ev["b_pass"], ev)

    def test_b_rejects_organisational_cases_of_foresight_practice_without_method_study(self):
        # Studying where/how foresight is used in organisations is not, by itself, a study
        # of the method. Bare "foresight practices" must not act as a meta-method cue.
        ev = self.gate(
            "Four Cases of Foresight and Futures Thinking in Public Universities Under the Discourse of University Disruption",
            "This study investigates foresight practices in public universities through the lens of futures research, an interdisciplinary field concerned with the systematic study of possible, probable, and preferable futures. Many universities have begun to incorporate foresight into their strategic thinking processes."
        )
        self.assertFalse(ev["b_pass"], ev)

    # --- A: internal EU R&I can qualify, but only through a meaningful state variable ---
    def test_a_keeps_internal_eu_research_capacity_evidence(self):
        ev = self.gate(
            "Research careers and brain drain across the European Research Area",
            "Using longitudinal data, we estimate researcher mobility, talent retention and research workforce changes across EU member states."
        )
        self.assertTrue(ev["a_pass"], ev)
        self.assertIn(ev["a_route"], {"eu-ri-system-relevance", "research-evidence", "explicit-geopolitics"})

    def test_a_keeps_internal_eu_innovation_financing_evidence(self):
        ev = self.gate(
            "Financing instruments for innovation in the EU: Panel evidence from the SAFE survey",
            "The study measures innovation financing and investment constraints across European firms."
        )
        self.assertTrue(ev["a_pass"], ev)

    def test_a_rejects_european_local_technology_application(self):
        ev = self.gate(
            "Cybersecurity adoption in a European regional rail operator",
            "This case study evaluates a cybersecurity framework used by one rail operator and surveys employee adoption."
        )
        self.assertFalse(ev["a_pass"], ev)

    def test_a_rejects_pure_european_security_without_ri_object(self):
        ev = self.gate(
            "European security cooperation and the challenge of strategic autonomy",
            "The article discusses defence cooperation, alliances and national security policy in Europe."
        )
        self.assertFalse(ev["a_pass"], ev)

    def test_a_keeps_eu_technological_resilience_as_strategic_state_variable(self):
        ev = self.gate(
            "The Economic and Technological Resilience in the European Union: Geopolitical Fragmentation, Economic Security and the Future of Competitiveness",
            "The study examines how geopolitical and geoeconomic fragmentation is reshaping the European Union's technological resilience, critical external dependencies and long-term competitiveness."
        )
        self.assertTrue(ev["a_pass"], ev)
        self.assertEqual(ev["a_route"], "explicit-geopolitics")

    def test_a_keeps_eu_strategic_technology_industrial_base(self):
        ev = self.gate(
            "Environmental Biotechnology for a Sustainable and Competitive EU",
            "Biotechnology is a Commission priority technology. It can strengthen Europe's industrial base, support innovation, strategic autonomy, resilience and resource security."
        )
        self.assertTrue(ev["a_pass"], ev)


    # --- C: Europe/EU source lane; external-only developments stay out ---
    def test_c_external_domestic_biotech_investment_stays_out(self):
        row = {
            "headline": "China invests $8 billion in new biotech research hub",
            "_desc": "The Chinese government announced investment in biotech companies and laboratories to expand national biotechnology capacity.",
            "source": "Reuters",
            "source_domain": "reuters.com",
            "link": "https://www.reuters.com/example-biotech-hub",
            "date": "2026-09-10",
            "_themes": list(S.themes_for("China invests $8 billion in new biotech research hub. The Chinese government announced investment in biotech companies and laboratories to expand national biotechnology capacity.")),
        }
        diagnostics = []
        out = S.anchor_news([row], [], diagnostics, allow_unanchored=True)
        self.assertEqual(out, [], diagnostics)

    def test_c_external_us_science_funding_shock_stays_out(self):
        row = {
            "headline": "US cuts NSF research funding",
            "_desc": "The US government cuts National Science Foundation funding for university research and scientific programmes.",
            "source": "Reuters",
            "source_domain": "reuters.com",
            "link": "https://www.reuters.com/example-nsf-cuts",
            "date": "2026-09-10",
            "_themes": list(S.themes_for("US cuts NSF research funding. The US government cuts National Science Foundation funding for university research and scientific programmes.")),
        }
        diagnostics = []
        out = S.anchor_news([row], [], diagnostics, allow_unanchored=True)
        self.assertEqual(out, [], diagnostics)

    def test_c_direct_european_ai_capacity_commitment_can_enter(self):
        headline = "Europe commits €5 billion to fund seven AI megafactories and catch up with the US and China"
        desc = "European governments commit funding for seven AI megafactories to expand compute capacity and close a strategic capability gap with the United States and China."
        row = {
            "headline": headline,
            "_desc": desc,
            "source": "Le Monde",
            "source_domain": "lemonde.fr",
            "link": "https://example.test/europe-ai-megafactories",
            "date": "2026-07-31",
            "_themes": list(S.themes_for(f"{headline}. {desc}")),
        }
        diagnostics = []
        out = S.anchor_news([row], [], diagnostics, allow_unanchored=True)
        self.assertTrue(out, diagnostics)

    def test_c_external_research_collaboration_restriction_stays_out(self):
        row = {
            "headline": "US politicians push agencies to restrict research collaboration with China",
            "_desc": "US lawmakers are pressing federal science agencies to restrict research collaboration with Chinese institutions in sensitive technologies.",
            "source": "Nature",
            "source_domain": "nature.com",
            "link": "https://www.nature.com/example-research-restrictions",
            "date": "2026-07-16",
            "_themes": list(S.themes_for("US politicians push agencies to restrict research collaboration with China. US lawmakers are pressing federal science agencies to restrict research collaboration with Chinese institutions in sensitive technologies.")),
        }
        diagnostics = []
        out = S.anchor_news([row], [], diagnostics, allow_unanchored=True)
        self.assertEqual(out, [], diagnostics)

    def test_c_external_china_chip_control_stays_out(self):
        row = {
            "headline": "China restricts exports of advanced chipmaking materials",
            "_desc": "The Chinese government imposed new export controls affecting semiconductor research and production capacity.",
            "source": "Reuters",
            "source_domain": "reuters.com",
            "link": "https://www.reuters.com/example-chip-controls",
            "date": "2026-09-10",
            "_themes": list(S.themes_for("China restricts exports of advanced chipmaking materials. The Chinese government imposed new export controls affecting semiconductor research and production capacity.")),
        }
        diagnostics = []
        out = S.anchor_news([row], [], diagnostics, allow_unanchored=True)
        self.assertEqual(out, [], diagnostics)

    def test_c_fast_deep_tech_discovery_queries_include_funding_round_language(self):
        queries = S.c_capital_infrastructure_fast_queries(72)
        joined = " ".join(queries).lower()
        self.assertIn("funding round", joined)
        self.assertIn("raises", joined)
        self.assertIn("artificial intelligence", joined)

    def test_c_named_european_ai_firm_is_not_rejected_because_actor_dictionary_misses_it(self):
        headline = "French AI company Mistral hits $24 billion valuation in funding round"
        desc = (
            "French AI company Mistral raised 3 billion euros in a funding round. The funding will support AI model "
            "development and frontier research as it competes with larger U.S. rivals and supports European technological sovereignty."
        )
        row = {
            "headline": headline,
            "_desc": desc,
            "source": "Reuters",
            "source_domain": "reuters.com",
            "link": "https://www.reuters.com/example-mistral-funding",
            "date": "2026-09-08",
            "_themes": list(S.themes_for(f"{headline}. {desc}")),
        }
        diagnostics = []
        out = S.anchor_news([row], [], diagnostics, allow_unanchored=True)
        self.assertEqual(len(out), 1, diagnostics)

    def test_c_european_chip_capacity_breaking_ground_is_a_hard_capacity_move(self):
        headline = "ASML breaks ground on new manufacturing facilities in major expansion"
        desc = (
            "ASML commenced construction on a major new production site in the Netherlands to expand capacity for "
            "advanced semiconductor chipmaking equipment, with new cleanroom facilities and up to 20,000 workers."
        )
        ok, rel, _ = S.c_source_backed_eu_ri_relevance(headline, desc, "Reuters", "reuters.com", "https://www.reuters.com/example-asml")
        self.assertTrue(ok)
        self.assertIn(rel, {"supported", "member_state"})

    def test_c_rejects_generic_foreign_data_centre_pr(self):
        ok, _, _ = S.c_source_backed_eu_ri_relevance(
            "Company opens a new data centre in Texas",
            "The company opened a 20MW facility for ordinary enterprise cloud services."
        )
        self.assertFalse(ok)

    def test_c_rejects_event_landing_page_even_when_semiconductor_and_europe_words_are_present(self):
        headline = "Plug & Play Taiwan | From Breakthrough to Scale: The Next Wave of Semiconductor Innovation | imec"
        desc = (
            "This event explores how frontier technologies emerging from global startups can connect with Taiwan's "
            "world-class manufacturing and supply chain to accelerate validation, commercialization, and scale. "
            "September 1, 2026 | Da'an District, Taiwan. Semiconductor innovation gathering bringing together leading "
            "startups, corporates, investors, and research leaders across Taiwan, APAC, the U.S., and Europe."
        )
        self.assertTrue(S.routine_signal_noise(headline, desc))

    def test_c_rejects_operational_supercomputer_procurement_notice(self):
        headline = "Acquisition, Delivery, Installation and Hardware and Software Maintenance of INNOVATE Industrial Grade Supercomputer"
        desc = "Invitation to tender for acquisition, delivery, installation and maintenance of an industrial-grade supercomputer for an Italian research centre."
        self.assertTrue(S.routine_signal_noise(headline, desc))
        item = {
            "headline": headline,
            "what": "Invitation to tender for acquisition, delivery, installation and maintenance of the INNOVATE industrial-grade supercomputer.",
            "source": "EuroHPC Joint Undertaking",
            "link": "https://www.eurohpc-ju.europa.eu/document/download/example_en?filename=Invitation_to_tender.pdf",
            "date": "2026-07-16",
            "c_event_date": "2026-07-16",
            "event_status": "DONE",
            "language": "English",
        }
        self.assertFalse(S._saved_signal_passes(item))

    def test_saved_c_event_landing_page_is_not_grandfathered(self):
        item = {
            "headline": "Plug & Play Taiwan | From Breakthrough to Scale: The Next Wave of Semiconductor Innovation | imec",
            "signal_note": (
                "This event explores how frontier technologies emerging from global startups can connect with Taiwan's "
                "manufacturing and supply chain. September 1, 2026 | Taiwan. Semiconductor innovation gathering bringing "
                "together startups, corporates, investors and research leaders across Taiwan, the U.S. and Europe."
            ),
            "source": "imec",
            "link": "https://www.imec-int.com/en/events/plug-play-taiwan-breakthrough-scale-next-wave-semiconductor-innovation",
            "date": "2026-08-12",
            "event_status": "DONE",
            "language": "English",
        }
        self.assertFalse(S._saved_signal_passes(item))

    def test_c_admission_trace_is_bounded_deduplicated_and_reason_counted(self):
        rows, counts = S.compact_c_admission_trace(
            [
                {"headline": "A", "source": "X", "status": "rejected", "reason": "no_watch_theme"},
                {"headline": "A", "source": "X", "status": "rejected", "reason": "no_watch_theme"},
            ],
            [
                {"headline": "B", "source": "Y", "status": "accepted", "reason": "accepted_unanchored"},
            ],
            limit=10,
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(counts["no_watch_theme"], 1)
        self.assertEqual(counts["accepted_unanchored"], 1)

    def test_c_recognises_missing_policy_event_verbs(self):
        self.assertTrue(S.signal_headline_has_current_change("Netherlands tightens screening of researchers in sensitive technologies"))
        self.assertEqual(S.signal_event_status("", "Netherlands tightens screening of researchers in sensitive technologies", ""), "DONE")
        self.assertTrue(S.signal_headline_has_current_change("Council ratifies research association agreement"))

    # --- publication mix is a soft share downstream of quality ---
    def test_soft_8_1_ab_share_does_not_cap_valid_rows(self):
        candidates = []
        for i in range(20):
            candidates.append({"title": f"A candidate {i}", "link": f"https://a/{i}", "strand": "A"})
        for i in range(20):
            candidates.append({"title": f"B candidate {i}", "link": f"https://b/{i}", "strand": "B"})
        selected, stats = S.select_hard_new_ab_mix(candidates)
        self.assertEqual(sum(x["strand"] == "A" for x in selected), 20)
        self.assertEqual(sum(x["strand"] == "B" for x in selected), 20)
        self.assertEqual(stats["selected_a"], 20)
        self.assertEqual(stats["selected_b"], 20)
        self.assertEqual(stats["suppressed_a"], 0)
        self.assertEqual(stats["suppressed_b"], 0)

    def test_both_candidate_is_normalised_without_b_cap(self):
        candidates = [{"title": "Both", "link": "https://x/both", "strand": "both"}]
        candidates += [{"title": f"A {i}", "link": f"https://x/a{i}", "strand": "A"} for i in range(12)]
        candidates += [{"title": f"B {i}", "link": f"https://x/b{i}", "strand": "B"} for i in range(12)]
        selected, stats = S.select_hard_new_ab_mix(candidates)
        self.assertEqual(sum(x["strand"] == "B" for x in selected), 12)
        self.assertEqual(sum(x["strand"] == "A" for x in selected), 12)
        self.assertEqual(sum(x["strand"] == "both" for x in selected), 1)
        self.assertEqual(stats["selected_a"], 13)
        self.assertEqual(stats["selected_b"], 13)
        self.assertTrue(all(x["strand"] in {"A", "B", "both"} for x in selected))
        self.assertEqual(stats["suppressed_a"], 0)
        self.assertEqual(stats["suppressed_b"], 0)

    def test_c_share_does_not_cap_novel_rows(self):
        headlines = [
            "China restricts quantum exports", "US cuts NSF science funding",
            "Germany opens AI research factory", "France funds biotech laboratory",
            "Japan signs international research pact", "India launches scientist return programme",
            "Council adopts FP10 budget position", "Netherlands tightens research screening",
        ]
        rows = [{"headline": h, "link": f"https://reuters.com/signal-{i}", "date": "2026-09-10", "source": "Reuters"} for i, h in enumerate(headlines)]
        selected, stats = S.select_hard_new_c_mix(rows, [])
        self.assertEqual(len(selected), 8)
        self.assertEqual(stats["selected_c"], 8)
        self.assertEqual(stats["suppressed_c"], 0)

    # --- one-time migration of the known v24.5 flood/current curator negatives ---
    def test_v246_b_library_cleanup_revalidates_all_saved_b_rows(self):
        bad = {
            "title": "Ordinary stock model with future research directions",
            "summary": "We propose a prediction framework and outline directions for future research across several scenarios.",
            "type": "peer-reviewed journal article",
            "source_tier": "Tier 2",
            "strand": "B",
        }
        old = dict(bad, link="https://example.org/old", first_seen="2026-09-09T22:52Z")
        legacy_null = dict(bad, link="https://example.org/legacy-null", first_seen=None)
        flooded = dict(bad, link="https://example.org/flood", first_seen="2026-09-09T23:26Z")
        cleaned, stats = S.surgical_precision_cleanup({"strand_a": [], "strand_b": [old, legacy_null, flooded]})
        self.assertEqual(cleaned["strand_b"], [])
        self.assertEqual(stats["strand_b_removed"], 3)

    def test_v246_b_library_cleanup_keeps_real_method_object_regardless_of_age(self):
        good = {
            "title": "Bias in expert judgment within large-scale science and technology Delphis",
            "summary": "We critique bias, panelist rationales and the methodological design of large-scale S&T Delphi surveys.",
            "type": "peer-reviewed journal article",
            "source_tier": "Tier 2",
            "strand": "B",
            "first_seen": None,
            "link": "https://example.org/delphi-method",
        }
        cleaned, stats = S.surgical_precision_cleanup({"strand_a": [], "strand_b": [good]})
        self.assertEqual([x["link"] for x in cleaned["strand_b"]], [good["link"]])
        self.assertEqual(stats["strand_b_removed"], 0)

    def test_ab_diagnostics_do_not_count_b_only_pass_as_no_eu_failure(self):
        ev = self.gate(
            "Mission-oriented scenarios: A new method for urban foresight",
            "We develop and validate a reusable scenario method and discuss its design principles and transferability.",
        )
        self.assertTrue(ev["b_pass"], ev)
        self.assertFalse(ev["a_pass"], ev)
        S.ADMISSION_DIAGNOSTICS.clear()
        S._record_ab_gate_diagnostic("fixture", ev)
        self.assertEqual(S.ADMISSION_DIAGNOSTICS["fixture_b_admitted_gate"], 1)
        self.assertEqual(S.ADMISSION_DIAGNOSTICS["fixture_reject_no_direct_eu"], 0)

    def test_ab_diagnostics_record_recognised_b_family_without_method_object(self):
        ev = self.gate(
            "An investigation of the alternative futures of public libraries in 2030",
            "Horizon scanning and foresight workshops were used to develop four scenarios for public libraries.",
        )
        self.assertFalse(ev["b_pass"], ev)
        self.assertTrue(ev["method_evidence"], ev)
        S.ADMISSION_DIAGNOSTICS.clear()
        S._record_ab_gate_diagnostic("fixture", ev)
        self.assertEqual(S.ADMISSION_DIAGNOSTICS["fixture_b_reject_method_object"], 1)

    def test_curator_gold_negative_c_is_rejected_semantically_not_by_title_tombstone(self):
        headline = "EY expands quantum computing with on-site system for enterprise AI"
        self.assertNotIn(headline, S._retired_signal_headlines())
        item = {
            "headline": headline,
            "what": "EY Canada installed an on-site quantum computer for enterprise workloads and AI experimentation.",
            "source": "eeNews Europe",
            "link": "https://www.eenewseurope.com/en/ey-expands-quantum-computing-with-on-site-system-for-enterprise-ai/",
            "date": "2026-07-30",
            "c_event_date": "2026-07-30",
            "event_status": "DONE",
            "language": "English",
        }
        self.assertFalse(S._saved_signal_passes(item))

    def test_profile_and_mix_contract(self):
        cfg = json.loads((ROOT / "radar_config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["admission_profile"], "v24.6-criteria-repair")
        self.assertEqual(cfg["quality_profile_version"], "v24.6-criteria-repair")
        self.assertEqual(cfg["signal_quality_profile_version"], "v24.6-independent-c-state-variable-change")
        self.assertEqual(cfg["signal_discovery_version"], "v24.6-independent-c-state-variable-change-c60d")
        self.assertEqual(S.C_ADMISSION_PROFILE_VERSION, "v24.6-state-variable-change-c")
        self.assertEqual(S.CURATOR_DECISION_PROFILE_VERSION, "v24.6-criteria-repair")
        self.assertEqual((cfg["target_new_a_per_scan"], cfg["target_new_b_per_scan"], cfg["target_new_c_per_scan"]), (8, 1, 3))
        self.assertEqual(cfg["c_min_new_per_successful_scan"], 0)
        self.assertFalse(cfg["c_floor_rescue_enabled"])
        self.assertEqual(cfg.get("target_item_mix_mode"), "soft_shares")


if __name__ == "__main__":
    unittest.main()
