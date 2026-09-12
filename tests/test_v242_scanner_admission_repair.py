from pathlib import Path
import datetime as dt
import importlib.util
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_v242_contract", PATH)
S = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = S
spec.loader.exec_module(S)


class V242ScannerAdmissionRepairTests(unittest.TestCase):
    def test_graded_europe_scope(self):
        direct, _ = S.eu_evidence(
            "EU–China research cooperation under a de-risking framework",
            "The study examines EU science policy and research cooperation.", ""
        )
        supported, _ = S.eu_evidence(
            "Building deep-tech ecosystems in European regions", "", ""
        )
        unclear, _ = S.eu_evidence(
            "Knowledge transfer through German universities",
            "University-industry collaboration and innovation performance.", ""
        )
        none, _ = S.eu_evidence(
            "Research competition in the United States and China", "", ""
        )
        self.assertEqual(direct, "direct")
        self.assertEqual(supported, "supported")
        self.assertEqual(unclear, "unclear")
        self.assertEqual(none, "none")
        self.assertTrue(S.eu_scope_admissible(direct))
        self.assertTrue(S.eu_scope_admissible(supported))
        self.assertFalse(S.eu_scope_admissible(unclear))
        self.assertFalse(S.eu_scope_admissible(none))

    def test_benchmark_title_only_a_recall(self):
        # Exact/near-exact titles from scan_these_now.docx. These are intentionally
        # tested without abstracts: explicit title evidence must not be rejected merely
        # because Crossref/OpenAlex omitted text.
        titles = [
            "Digital infrastructure, innovation capacity, and AI technology adoption in EU manufacturing",
            "The geography of artificial intelligence in European regions: Innovation, exposure and use",
            "From dependency to resilience: JRC science for EU technological sovereignty",
            "Choose Europe: Research careers, brain drain and policy lessons from the CESAER 2024 Survey",
            "EU–China research cooperation under a ‘de-risking’ framework: The securitisation of knowledge in EU science policy (2021–2025)",
            "From pilot to policy: European university alliances and their contribution to the European Research Area",
            "Promising security, delivering dependency: The material constraints of EU semiconductor collective securitisation",
            "Norm transformation in EU research security: A pragmatist approach",
            "Building deep-tech entrepreneurial ecosystems: Factors that promote the presence of deep-tech startups in European regions",
            "Financing instruments for innovation in the EU: Panel evidence from the SAFE survey",
            "Funding sources and university patenting: An analysis of European higher education institutions",
            "Enabling the EU’s digital sovereignty: A Europe-level quantum internet as the key infrastructure for a European digital polity",
            "The European Union’s approach to strategic technology governance: The case of AI",
        ]
        failed = []
        for title in titles:
            ev = S.gate_scope(title, "", "", 3, source_kind="scholarly")
            if not ev["a_pass"]:
                failed.append((title, ev.get("eu_relevance"), ev.get("aboutness_reason"), ev.get("centrality_reason")))
        self.assertEqual(failed, [])

    def test_generic_europe_and_single_member_state_still_fail_a(self):
        negatives = [
            "A comparison of breakfast preferences in European hotels",
            "Knowledge transfer through German universities",
            "AI-supported classroom engagement in European secondary schools",
        ]
        for title in negatives:
            ev = S.gate_scope(title, "", "", 3, source_kind="scholarly")
            self.assertFalse(ev["a_pass"], title)

    def test_inference_only_foreign_material_stays_out(self):
        self.assertEqual(S.external_eu_bridge_sentence(
            "The United States announces a national AI strategy with no European content.", []
        ), (False, "", []))
        ev = S.gate_scope(
            "United States national AI strategy",
            "The strategy expands domestic US compute and research capability.", "", 1, source_kind="institutional"
        )
        self.assertFalse(ev["a_pass"])

    def test_formal_eu_press_release_surface_is_not_blanket_excluded(self):
        title = "Commission proposes new European Innovation Act to help innovative European ideas grow and compete globally"
        text = "The European Commission proposes a new European Innovation Act for research-driven innovative companies. Press release."
        reason = S.document_exclusion_reason(
            title, text, "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1810", "press release"
        )
        self.assertIsNone(reason)
        self.assertTrue(S.formal_proposal_is_public_signal(title + ". " + text, title, text, "European Commission", "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1810"))

    def _news(self, headline, desc, source, domain, link):
        text = headline + " " + desc
        return {
            "headline": headline, "_desc": desc, "source": source,
            "source_domain": domain, "link": link, "date": "2026-09-09T08:00Z",
            "_themes": S.themes_for(text),
            "_entities": S.distinct_matches(text, S.ENTITY_TERMS + S.GEO_ACTORS),
        }

    def test_c_event_route_accepts_real_european_ri_developments(self):
        rows = [
            self._news(
                "European Commission proposes new European Innovation Act to help innovative European ideas grow and compete globally",
                "The European Commission proposes a new European Innovation Act for innovative companies and research-driven scale-ups.",
                "European Commission", "ec.europa.eu", "https://ec.europa.eu/commission/presscorner/detail/en/ip_26_1810"
            ),
            self._news(
                "EuroHPC Joint Undertaking launches the AI Gigafactories call",
                "EuroHPC launched the AI Gigafactories call to expand European AI compute capacity and innovation infrastructure.",
                "EuroHPC Joint Undertaking", "eurohpc-ju.europa.eu", "https://eurohpc-ju.europa.eu/news/example"
            ),
            self._news(
                "ERC Starting Grant success rate below 9% amid record demand",
                "ERC Starting Grant success rate fell below 9% amid record demand from researchers across the EU.",
                "Research Professional News", "researchprofessionalnews.com", "https://www.researchprofessionalnews.com/example"
            ),
        ]
        out = S.anchor_news(rows, [], allow_unanchored=True)
        self.assertEqual(len(out), 3)
        self.assertTrue(all(x.get("c_event_actor") for x in out))
        self.assertTrue(all(x.get("c_event_date") == "2026-09-09" for x in out))
        self.assertTrue(all(x.get("c_admission_route") == "event" for x in out))
        self.assertEqual({x.get("realisation_status") for x in out}, {"proposed", "announced", "delivered"})

    def test_c_precursor_intention_stays_out(self):
        row = self._news(
            "Commission to present long-awaited Innovation Act proposal",
            "The European Commission intends to present the European Innovation Act proposal next week.",
            "Science|Business", "sciencebusiness.net", "https://sciencebusiness.net/news/example"
        )
        self.assertEqual(S.anchor_news([row], [], allow_unanchored=True), [])

    def test_realisation_status_and_status_aware_retention(self):
        self.assertEqual(S.realisation_status_for("The Commission proposes a new act."), "proposed")
        self.assertEqual(S.realisation_status_for("The Council adopted its negotiating position for FP10."), "in_negotiation")
        now = dt.datetime(2026, 9, 10, tzinfo=dt.timezone.utc)
        proposed = {"first_seen": "2026-06-02T00:00:00Z", "realisation_status": "proposed"}
        delivered = {"first_seen": "2026-06-02T00:00:00Z", "realisation_status": "delivered"}
        self.assertFalse(S.signal_retention_expired(proposed, now))
        self.assertTrue(S.signal_retention_expired(delivered, now))

    def test_c_share_targets_three_without_forcing_a_floor(self):
        cfg = json.loads((ROOT / "radar_config.json").read_text(encoding="utf-8"))
        self.assertEqual(int(cfg.get("target_new_c_per_scan", -1)), 3)
        self.assertEqual(int(cfg.get("c_min_new_per_successful_scan", -1)), 0)
        self.assertFalse(bool(cfg.get("c_floor_rescue_enabled", True)))
        self.assertEqual(cfg.get("target_item_mix_mode"), "relative_release")

    def test_missing_text_queue_is_persistent_state(self):
        state = S.initial_scan_state({})
        self.assertIn("deferred_metadata_queue", state)
        source = PATH.read_text(encoding="utf-8")
        self.assertIn("recover_persistent_metadata_queue", source)
        self.assertIn("persist_current_metadata_queue(state)", source)


if __name__ == "__main__":
    unittest.main()
