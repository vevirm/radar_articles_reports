import importlib.util
import json
import os
import sys
import time
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"

spec = importlib.util.spec_from_file_location("radar_scan_test_module", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class SchedulerBreadthTests(unittest.TestCase):
    def test_interleaved_batch_keeps_all_lanes_in_executed_prefix(self):
        base = [f"base-{i}" for i in range(12)]
        explore = [f"explore-{i}" for i in range(12)]
        gaps = [f"gap-{i}" for i in range(32)]
        methods = [f"method-{i}" for i in range(12)]
        context = [f"context-{i}" for i in range(4)]
        batch = scan.interleaved_unique_batch(52, base, explore, gaps, methods, context)
        self.assertEqual(len(batch), 52)
        # Simulate a source deadline after only the first 20 queued queries start.
        prefix = batch[:20]
        for stem in ("base-", "explore-", "gap-", "method-", "context-"):
            self.assertTrue(any(x.startswith(stem) for x in prefix), stem)
        self.assertEqual(sum(x.startswith("base-") for x in batch), 12)
        self.assertEqual(sum(x.startswith("explore-") for x in batch), 12)



class SourceFailureReallocationTests(unittest.TestCase):
    def test_openalex_429_marks_source_unavailable_for_later_lanes(self):
        warnings = [
            "OpenAlex HTTP 429 (keyless OpenAlex allowance/rate limit); source stopped for this run; continuing with Crossref and direct publisher/institution scanning"
        ]
        self.assertTrue(scan.source_stage_failed(warnings, "openalex"))

    def test_stage_budget_warning_alone_does_not_mark_source_failed(self):
        self.assertFalse(scan.source_stage_failed(["OpenAlex scan budget reached; 11 queued query/queries skipped"], "openalex"))

    def test_reallocation_config_preserves_strict_gate_but_adds_replacement_search(self):
        self.assertTrue(scan.CONFIG.get("source_failure_reallocation_enabled"))
        self.assertGreaterEqual(scan.CONFIG.get("source_failure_reallocation_institution_sources", 0), 16)
        self.assertGreaterEqual(scan.CONFIG.get("source_failure_reallocation_crossref_journals", 0), 6)
        self.assertGreaterEqual(scan.CONFIG.get("queries_b_method_per_scan", 0), 12)



class LowYieldRotationTests(unittest.TestCase):
    def test_fresh_rotation_skips_queries_already_executed_and_wraps(self):
        bank = ["q0", "q1", "q2", "q3", "q4", "q5"]
        batch, next_cursor, wrapped = scan.rotating_batch_excluding(
            bank, 4, 3, {"q4", "q0"}
        )
        self.assertEqual(batch, ["q5", "q1", "q2"])
        self.assertEqual(next_cursor, 3)
        self.assertTrue(wrapped)

    def test_low_yield_count_uses_only_genuinely_new_unique_ab(self):
        old_ids = scan.KNOWN_AB_IDENTITIES
        old_links = scan.KNOWN_AB_LINKS
        scan.KNOWN_AB_IDENTITIES = {"title:known paper"}
        scan.KNOWN_AB_LINKS = {"https://example.org/known-link"}
        try:
            rows = [
                {"title": "Known Paper", "link": "https://example.org/x", "strand": "A"},
                {"title": "Known Link Different Title", "link": "https://example.org/known-link", "strand": "A"},
                {"title": "New Paper", "link": "https://example.org/new", "strand": "A"},
                {"title": "New Paper", "link": "https://example.org/new-duplicate", "strand": "A"},
                {"title": "Method Paper", "link": "https://example.org/method", "strand": "B"},
                {"title": "Signal", "link": "https://example.org/signal", "strand": "C"},
            ]
            out = scan.genuinely_new_ab_candidates(rows)
        finally:
            scan.KNOWN_AB_IDENTITIES = old_ids
            scan.KNOWN_AB_LINKS = old_links
        self.assertEqual({x["title"] for x in out}, {"New Paper", "Method Paper"})

    def test_rescue_cursor_does_not_advance_on_partial_execution(self):
        state = {}
        scan.commit_planned_cursor_if_executed(state, "cursor", 2, ["a", "b"], 4, {"a"})
        self.assertEqual(state["cursor"], 2)
        scan.commit_planned_cursor_if_executed(state, "cursor", 2, ["a", "b"], 4, {"a", "b"})
        self.assertEqual(state["cursor"], 4)

    def test_config_uses_twenty_item_target_as_search_depth_trigger(self):
        self.assertTrue(scan.CONFIG.get("low_yield_fresh_rotation_enabled"))
        self.assertEqual(scan.CONFIG.get("target_new_ab_per_scan"), 20)
        self.assertEqual(scan.CONFIG.get("low_yield_fresh_rotation_trigger_max_new_ab"), 19)
        self.assertTrue(scan.CONFIG.get("low_yield_extended_fallback_enabled"))
        self.assertTrue(scan.CONFIG.get("low_yield_full_rescue_run_enabled"))
        self.assertEqual(scan.CONFIG.get("low_yield_full_rescue_run_trigger_max_new_ab"), 19)
        self.assertEqual(scan.CONFIG.get("extended_top_quality_lookback_months"), 6)


class MainRecallRepairTests(unittest.TestCase):
    def test_metadata_rescue_priority_prefers_eu_ri_strategic_title(self):
        strong = scan.scholarly_metadata_rescue_priority(
            "European research security and critical technology dependencies",
            query="EU research security foreign interference",
            source="Research Policy",
            published=__import__('datetime').date.today(),
            tier=1,
        )
        weak = scan.scholarly_metadata_rescue_priority(
            "A general model of organisational behaviour",
            query="EU research security foreign interference",
            source="Generic Journal",
            published=__import__('datetime').date.today(),
            tier=2,
        )
        self.assertGreater(strong, weak)
        self.assertGreaterEqual(strong, scan.CONFIG.get("metadata_rescue_priority_min_score", 10))

    def test_institution_url_scoring_does_not_treat_domain_name_as_content_signal(self):
        score = scan.institution_url_score(
            "https://research-and-innovation.ec.europa.eu/about", None, __import__('datetime').date(2026, 4, 30)
        )
        self.assertEqual(score, 0)

    def test_source_adapter_queues_publication_link_not_generic_navigation(self):
        class FakeResponse:
            def __init__(self, url):
                self.url = url
                self.headers = {"content-type": "text/html"}
                self.text = (
                    '<html><body>'
                    '<a href="/publications/2026/eu-research-security-report">EU research security report</a>'
                    '<a href="/about">About</a>'
                    '</body></html>'
                )
        old_seen = scan.INSTITUTION_SEEN_FINGERPRINTS
        scan.INSTITUTION_SEEN_FINGERPRINTS = {}
        try:
            with mock.patch.object(scan, "get", side_effect=lambda url, **kwargs: FakeResponse(url)):
                jobs = scan._source_adapter_domain_jobs(
                    {"domain": "research-and-innovation.ec.europa.eu", "name": "EC R&I", "tier": 1},
                    __import__('datetime').date(2026, 4, 30),
                    time.monotonic() + 30,
                    False,
                )
        finally:
            scan.INSTITUTION_SEEN_FINGERPRINTS = old_seen
        urls = [x[0] for x in jobs]
        self.assertTrue(any("eu-research-security-report" in x for x in urls))
        self.assertFalse(any(x.endswith("/about") for x in urls))

    def test_commission_news_hub_is_container_not_evidence(self):
        hub = "https://research-and-innovation.ec.europa.eu/news/all-research-and-innovation-news_en"
        self.assertTrue(scan.institutional_container_page("All research and innovation news", hub))
        self.assertEqual(
            scan.document_exclusion_reason("All research and innovation news", "", hub, ""),
            "hard exclusion: listing/index page",
        )

    def test_child_story_under_commission_news_hub_is_not_container(self):
        child = (
            "https://research-and-innovation.ec.europa.eu/news/all-research-and-innovation-news/"
            "new-charter-boosts-access-companies-cutting-edge-research-and-technology-infrastructures-europe-2026-07-28_en"
        )
        self.assertFalse(scan.institutional_container_page(
            "New charter boosts access to cutting-edge research and technology infrastructures in Europe", child
        ))

    def test_parse_never_admits_or_signals_a_news_listing_page(self):
        class FakeResponse:
            status_code = 200
            url = "https://research-and-innovation.ec.europa.eu/news/all-research-and-innovation-news_en"
            headers = {"content-type": "text/html"}
            text = (
                '<html lang="en"><head>'
                '<meta property="og:title" content="All research and innovation news">'
                '<meta name="description" content="Latest research and innovation news">'
                '</head><body><main>'
                '<article><time datetime="2026-07-16">16 July 2026</time>'
                '<a href="/news/all-research-and-innovation-news/a-real-story-2026-07-16_en">A real story</a>'
                'First European research network on antisemitism and Jewish life officially launched. '
                '</article></main></body></html>'
            )
        old_candidates = scan.INSTITUTION_SIGNAL_CANDIDATES
        scan.INSTITUTION_SIGNAL_CANDIDATES = []
        try:
            with mock.patch.object(scan, "get", return_value=FakeResponse()), \
                 mock.patch.object(scan, "gate_scope") as gate:
                item = scan.parse_institution_page(
                    FakeResponse.url, "European Commission — Research & Innovation", 1,
                    time.monotonic() + 30, "", __import__('datetime').date(2026, 7, 1),
                )
                gate.assert_not_called()
        finally:
            candidates = list(scan.INSTITUTION_SIGNAL_CANDIDATES)
            scan.INSTITUTION_SIGNAL_CANDIDATES = old_candidates
        self.assertIsNone(item)
        self.assertEqual(candidates, [])

    def test_saved_news_hub_is_removed_even_when_recovered_from_history(self):
        bad = {
            "title": "All research and innovation news",
            "source": "European Commission — Research & Innovation",
            "date": "2026-07-16",
            "link": "https://research-and-innovation.ec.europa.eu/news/all-research-and-innovation-news_en",
            "strand": "A",
            "summary": "First child story accidentally copied from the listing page.",
        }
        clean, removed = scan._sanitize_saved_radar({"strand_a": [bad], "strand_b": [], "strand_c": []})
        self.assertEqual(clean["strand_a"], [])
        self.assertEqual(removed["strand_a"], 1)

    def test_core_eu_source_adapters_are_configured(self):
        adapters = scan.CONFIG.get("institution_source_adapters", {})
        for domain in (
            "research-and-innovation.ec.europa.eu",
            "joint-research-centre.ec.europa.eu",
            "op.europa.eu",
            "europarl.europa.eu",
            "consilium.europa.eu",
            "digital-strategy.ec.europa.eu",
            "eurohpc-ju.europa.eu",
        ):
            self.assertIn(domain, adapters)
            self.assertTrue(adapters[domain].get("hub_paths"))
        dg_hubs = adapters["research-and-innovation.ec.europa.eu"]["hub_paths"]
        self.assertIn("/knowledge-publications-tools-and-data/publications_en", dg_hubs)
        self.assertIn("/strategy/support-policy-making/support-national-research-and-innovation-policy-making/research-and-innovation-paper-series_en", dg_hubs)
        self.assertIn("/strategy/support-policy-making/support-national-research-and-innovation-policy-making/srip-report_en", dg_hubs)
        self.assertIn("/publications-and-data_en", adapters["joint-research-centre.ec.europa.eu"]["hub_paths"])

    def test_material_mature_signal_is_not_discarded_after_detection(self):
        title = "EU officially joins new AI compute capacity programme"
        desc = (
            "The European Union invests in artificial intelligence research infrastructure "
            "to strengthen strategic technology capacity and competitiveness."
        )
        self.assertTrue(scan.material_update_signal_text(f"{title}. {desc}"))
        self.assertTrue(scan.weak_signal_candidate_text(title, desc))


    def test_phrase_workbook_export_is_loaded_as_guarded_ontology(self):
        self.assertGreaterEqual(len(scan.PHRASE_RULES.get("strand_a", [])), 100)
        self.assertGreaterEqual(len(scan.PHRASE_RULES.get("strand_c_retrieval", [])), 18)
        self.assertIn("never admit", scan.PHRASE_RULES.get("principles", {}).get("c_admission_rule", "").lower())

    def test_c_phrase_is_retrieval_not_admission(self):
        # A named candidate technology without a strategic R&I development is not C.
        title = "Neuromorphic processor benchmark released"
        desc = "A vendor posts routine benchmark results for a new processor."
        # It may enter the broad retrieval pool, but cannot survive as C without the
        # strategic/EU and Strand-A relationship gates.
        self.assertTrue(scan.weak_signal_candidate_text(title, desc))
        self.assertFalse(scan.factual_news(title, desc))
        self.assertEqual(scan.anchor_news([{"headline": title, "_desc": desc, "_themes": scan.themes_for(title+" "+desc), "_entities": []}], []), [])
        queries = scan.global_news_queries(72)
        self.assertTrue(any("neuromorphic" in q.lower() or "risc-v" in q.lower() for q in queries))

    def test_old_topic_with_distinct_new_point_remains_a_signal_candidate(self):
        title = "Europe expands RISC-V research capacity as export controls tighten"
        desc = (
            "A European research consortium will invest €420 million in new RISC-V technology capacity "
            "after tighter export controls increased strategic dependency risks."
        )
        self.assertTrue(scan.weak_signal_candidate_text(title, desc))
        dims = scan.relationship_novelty_dimensions(f"{title}. {desc}")
        self.assertIn("new magnitude", dims)
        self.assertIn("new mechanism", dims)

    def test_established_eu_office_is_a_not_c_candidate(self):
        title = "European AI Office"
        desc = "The European AI Office supports the development and adoption of trustworthy AI solutions and coordinates implementation of EU AI policy."
        link = "https://digital-strategy.ec.europa.eu/en/policies/ai-office"
        self.assertTrue(scan.standing_institutional_page(title, desc))
        self.assertFalse(scan.institutional_weak_signal_eligible(
            title, desc, "European Commission — Digital Strategy", link
        ))

    def test_mature_eu_official_update_is_a_not_c_candidate(self):
        title = "European Commission updates EIC Fund Investment Guidelines for the EIC Accelerator and STEP Scaleup"
        desc = "The Commission updated the formal investment guidelines for its established funding instruments."
        link = "https://eic.ec.europa.eu/document/example"
        self.assertFalse(scan.institutional_weak_signal_eligible(
            title, desc, "European Innovation Council", link
        ))

    def test_provisional_eu_official_development_can_still_be_c(self):
        title = "Commission proposes pilot screening scheme for sensitive research cooperation"
        desc = "The European Commission proposes a pilot and consultation before deciding whether to adopt the research-security measure."
        link = "https://research-and-innovation.ec.europa.eu/example"
        self.assertTrue(scan.institutional_weak_signal_eligible(
            title, desc, "European Commission — Research & Innovation", link
        ))

    def test_saved_eu_official_background_page_cannot_survive_c_cleanup(self):
        item = {
            "headline": "European AI Office",
            "source": "European Commission — Digital Strategy",
            "link": "https://digital-strategy.ec.europa.eu/en/policies/ai-office",
            "date": "2026-08-31",
            "signal_note": "The European AI Office supports development and adoption of trustworthy AI solutions.",
            "anchor": "A paper about European AI capability (Strand A)",
        }
        self.assertFalse(scan._saved_signal_passes(item))

    def test_eu_office_page_gets_a_chance_at_a_but_never_enters_c(self):
        class FakeResponse:
            status_code = 200
            url = "https://digital-strategy.ec.europa.eu/en/policies/ai-office"
            headers = {"content-type": "text/html"}
            text = (
                '<html lang="en"><head>'
                '<meta property="og:title" content="European AI Office">'
                '<meta name="description" content="The European AI Office supports the development and adoption of trustworthy AI solutions and coordinates implementation of EU AI policy.">'
                '<meta property="article:published_time" content="2026-08-20">'
                '</head><body><main>'
                + ('The European AI Office supports European artificial intelligence policy, innovation, technology capacity, standards, governance and competitiveness. ' * 40)
                + '</main></body></html>'
            )
        old_candidates = scan.INSTITUTION_SIGNAL_CANDIDATES
        scan.INSTITUTION_SIGNAL_CANDIDATES = []
        try:
            with mock.patch.object(scan, "get", return_value=FakeResponse()), \
                 mock.patch.object(scan, "gate_scope", return_value={
                     "a_pass": True, "b_pass": False, "eu_relevance": "direct",
                     "ri_evidence": ["artificial intelligence", "innovation"],
                     "geo_evidence": ["competitiveness"],
                     "aboutness_reason": "official EU AI institutional framework", "a_focus_pass": True,
                 }), \
                 mock.patch.object(scan, "build_item", side_effect=lambda **kw: {
                     "title": kw["title"], "strand": kw["strand"], "type": kw["item_type"], "link": kw["link"]
                 }):
                item = scan.parse_institution_page(
                    FakeResponse.url, "European Commission — Digital Strategy", 1,
                    time.monotonic() + 30, "", __import__('datetime').date(2026, 8, 1)
                )
        finally:
            candidates = list(scan.INSTITUTION_SIGNAL_CANDIDATES)
            scan.INSTITUTION_SIGNAL_CANDIDATES = old_candidates
        self.assertEqual(candidates, [])
        self.assertIsNotNone(item)
        self.assertEqual(item["strand"], "A")
        self.assertEqual(item["type"], "official policy / institutional framework")

    def test_completed_commission_study_is_a_evidence_product_not_c(self):
        title = "Study on Cloud and AI Development in the EU"
        desc = (
            "Publication 11 August 2026. The study was carried out for the European Commission and gathers empirical evidence "
            "on EU cloud and AI infrastructure. The study identifies limited computing capacity in the EU and dependence on "
            "cloud and AI computing services provided by non-European suppliers. Read the study and executive summary."
        )
        link = "https://digital-strategy.ec.europa.eu/en/library/study-cloud-and-ai-development-eu"
        self.assertTrue(scan.formal_evidence_product(title, desc, "European Commission — Digital Strategy", link))
        self.assertFalse(scan.institutional_weak_signal_eligible(title, desc, "European Commission — Digital Strategy", link))
        saved = {
            "headline": title, "source": "European Commission — Digital Strategy", "link": link,
            "date": "2026-08-11", "signal_note": desc, "anchor": "Some Strand A paper (Strand A)",
        }
        self.assertFalse(scan._saved_signal_passes(saved))

    def test_cloud_ai_commission_study_passes_a_from_short_publication_page_text(self):
        title = "Study on Cloud and AI Development in the EU"
        desc = "The European Commission requested a study to gather empirical evidence on the EU's cloud and AI infrastructure requirements."
        body = (
            "The study identifies limited and geographically concentrated computing capacity within the EU and the EU's dependence "
            "on cloud and AI computing services provided by non-European suppliers. It analyses cross-border barriers, lock-in in the "
            "AI computing stack, third-country laws with extraterritorial effects, data-centre constraints and policy options. "
            "The analysis evaluates options using monetised cost-benefit analysis and multi-criteria decision analysis."
        )
        ev = scan.gate_scope(title, desc, body, 1, source_kind="institutional")
        self.assertTrue(ev["a_pass"])
        self.assertEqual(ev["eu_relevance"], "direct")

    def test_news_discovery_route_cannot_demote_formal_report_into_c(self):
        title = "Study on Cloud and AI Development in the EU"
        item = {
            "headline": title,
            "source": "European Commission — Digital Strategy",
            "date": "2026-08-11T12:00Z",
            "link": "https://digital-strategy.ec.europa.eu/en/library/study-cloud-and-ai-development-eu",
            "_desc": "Publication 11 August 2026. Read the study. It presents empirical evidence on EU cloud and AI infrastructure.",
            "_themes": ["critical and emerging technologies"],
            "_entities": [],
        }
        promoted = {"title": title, "strand": "A", "link": item["link"]}
        with mock.patch.object(scan, "_linked_publication_candidate", return_value=promoted):
            remaining, ab, stats = scan.route_formal_evidence_news_to_ab([item], [], time.monotonic() + 30)
        self.assertEqual(remaining, [])
        self.assertEqual(len(ab), 1)
        self.assertEqual(ab[0]["strand"], "A")
        self.assertEqual(stats["formal_evidence_not_c"], 1)
        self.assertEqual(scan.anchor_news([item], []), [])

    def test_jrc_biodiversity_service_does_not_pass_a_from_provenance_and_cooperation(self):
        title = "JRC Global Biodiversity Data Services (GBDS): Data Distribution Architecture, REST API and Query Builder"
        desc = "Access to Joint Research Centre's publications."
        body = (
            "By improving accessibility, interoperability and transparency, the GBDS strengthen collective capacity "
            "for biodiversity monitoring and reporting and support regional and global partners, including Technical "
            "and Scientific Cooperation support Centres, in implementing biodiversity targets. "
            "Access to Joint Research Centre's publications."
        )
        ev = scan.gate_scope(title, desc, body, 1, source_kind="institutional")
        self.assertEqual(ev["eu_relevance"], "direct")
        self.assertFalse(ev["a_pass"])

    def test_quantum_standard_setting_with_global_european_position_still_passes_a(self):
        title = "Standards for Quantum Technologies"
        body = (
            "This call supports research and development of European and international standards for quantum technologies. "
            "It will strengthen Europe's leadership in the global quantum standardisation landscape and ensure that "
            "European industrial and research priorities are represented in emerging standards."
        )
        ev = scan.gate_scope(title, body, "", 1, source_kind="institutional")
        self.assertTrue(ev["a_pass"])

    def test_jrc_navigation_text_is_removed_from_display_claims(self):
        raw = (
            "Relocation of European startups raises concerns about weakening the EU innovation ecosystem. "
            "Firms expand to foreign markets while retaining high-value R&D in Europe. "
            "Access to Joint Research Centre's publications."
        )
        cleaned = scan._strip_relevance_boilerplate(raw)
        self.assertNotIn("Access to Joint Research Centre", cleaned)
        claim = scan.concise_core_message(cleaned, "Is Europe losing its startups?")
        self.assertNotIn("Joint Research Centre", claim)

    def test_precision_cleanup_removes_saved_biodiversity_false_positive_but_keeps_startup_relocation(self):
        bad = {
            "title": "JRC Global Biodiversity Data Services (GBDS): Data Distribution Architecture, REST API and Query Builder",
            "source": "JRC Publications Repository", "date": "2026-08-31",
            "link": "https://publications.jrc.ec.europa.eu/repository/handle/JRC147250",
            "type": "official policy / institutional framework", "strand": "A",
            "eu_relevance": "direct", "a_route": "triangulated-strategic-context",
            "bridge_sentence": "", "geo_evidence": [], "ri_evidence": ["scientific cooperation"],
            "summary": "By improving accessibility and interoperability, GBDS supports regional and global partners in biodiversity monitoring. Access to Joint Research Centre's publications.",
            "source_tier": "Tier 1",
        }
        good = {
            "title": "Is Europe losing its startups?", "source": "JRC Publications Repository",
            "date": "2026-08-31", "link": "https://publications.jrc.ec.europa.eu/repository/handle/JRC146239",
            "type": "research/policy paper", "strand": "A", "eu_relevance": "direct",
            "a_route": "triangulated-strategic-context", "bridge_sentence": "", "geo_evidence": [],
            "ri_evidence": ["innovation ecosystem", "r&d"], "source_tier": "Tier 1",
            "summary": "Relocation of European startups raises concerns about weakening the EU innovation ecosystem. Firms expand to foreign markets while retaining high-value R&D in Europe. Access to Joint Research Centre's publications.",
            "core_message": "Access to Joint Research Centre's publications.",
        }
        cleaned, stats = scan.surgical_precision_cleanup({"strand_a": [bad, good], "strand_b": []})
        titles = {x["title"] for x in cleaned["strand_a"]}
        self.assertNotIn(bad["title"], titles)
        self.assertIn(good["title"], titles)
        kept = next(x for x in cleaned["strand_a"] if x["title"] == good["title"])
        self.assertNotIn("Joint Research Centre", kept.get("core_message", ""))

    def test_signal_quality_version_triggers_new_c_cleanup(self):
        self.assertIn("v17.19.18", scan.SIGNAL_QUALITY_PROFILE_VERSION)
        self.assertTrue(scan.needs_precision_signal_cleanup({
            "signal_quality_profile_version": "v17.17.0-relational-c-ontology-guarded"
        }))

    def test_signal_dedupe_requires_same_point_not_merely_same_topic(self):
        a = {
            "headline": "Europe expands AI compute capacity with new supercomputer investment",
            "what": "Europe adds €400 million of AI compute capacity.",
            "link": "https://example.org/a",
        }
        b = {
            "headline": "Europe AI compute faces electricity-grid bottleneck despite capacity expansion",
            "what": "Grid constraints, not chips, are becoming the limiting mechanism for AI compute.",
            "link": "https://example.org/b",
        }
        self.assertFalse(scan.signals_near_duplicate(a, b))
        syndicated = {
            "headline": "Europe expands AI compute capacity with €400m supercomputer investment",
            "what": "Europe adds €400 million of AI compute capacity.",
            "link": "https://example.org/c",
        }
        self.assertTrue(scan.signals_near_duplicate(a, syndicated))

    def test_unlisted_journal_requires_trusted_publisher(self):
        base = {
            "container-title": ["Unlisted but legitimate policy journal"],
            "type": "journal-article",
        }
        ok, *_ = scan.quality_from_crossref({**base, "publisher": "Springer Nature"})
        self.assertTrue(ok)
        ok, *_ = scan.quality_from_crossref({**base, "publisher": "Unknown Vanity Press"})
        self.assertFalse(ok)

    def test_sitemap_lastmod_is_not_treated_as_publication_date(self):
        class FakeResponse:
            status_code = 200
            url = "https://research-and-innovation.ec.europa.eu/publications/eu-research-security-report"
            headers = {"content-type": "text/html"}
            text = (
                '<html lang="en"><head><meta property="og:title" content="European research security and innovation capacity">'
                '<meta name="description" content="EU research and innovation policy addresses economic security, technology dependencies and strategic competition.">'
                '</head><body><main>' +
                ('European Union research and innovation policy, research security, technology dependencies, strategic competition and innovation capacity. ' * 80) +
                '</main></body></html>'
            )
        fp = scan.institution_fingerprint(FakeResponse.url, __import__('datetime').date.today())
        old_dates = scan.INSTITUTION_DISCOVERED_DATES
        old_seen = scan.INSTITUTION_SEEN_FINGERPRINTS
        scan.INSTITUTION_DISCOVERED_DATES = {fp: __import__('datetime').date.today()}
        scan.INSTITUTION_SEEN_FINGERPRINTS = {}
        try:
            with mock.patch.object(scan, "get", return_value=FakeResponse()), \
                 mock.patch.object(scan, "gate_scope", return_value={
                     "a_pass": True, "b_pass": False, "eu_relevance": "direct",
                     "ri_evidence": ["research"], "geo_evidence": ["economic security"],
                     "aboutness_reason": "about", "a_focus_pass": True,
                 }), \
                 mock.patch.object(scan, "build_item", return_value={"title": "x"}):
                item = scan.parse_institution_page(
                    FakeResponse.url, "European Commission — Research & Innovation", 1,
                    time.monotonic() + 30, fp, __import__('datetime').date.today() - __import__('datetime').timedelta(days=30)
                )
        finally:
            scan.INSTITUTION_DISCOVERED_DATES = old_dates
            scan.INSTITUTION_SEEN_FINGERPRINTS = old_seen
        self.assertIsNone(item)

    def test_source_integrity_rejects_missing_or_cross_document_links(self):
        missing = {
            "title": "Study to identify key strategic digital technologies for EU research and innovation funding beyond 2027",
            "source": "European Commission — Digital Strategy",
            "link": "",
        }
        self.assertFalse(scan.record_source_integrity_ok(missing))

        chimera = {
            "title": "Study to identify key strategic digital technologies for EU research and innovation funding beyond 2027",
            "source": "European Commission — Digital Strategy",
            "link": "https://assets.anthropic.com/m/12f214efcc2f457a/original/Claude-Sonnet-4-5-System-Card.pdf",
        }
        self.assertFalse(scan.record_source_integrity_ok(chimera))

        iasr_chimera = {
            "title": "International AI Safety Report 2026",
            "source": "International AI Safety Report",
            "link": "https://assets.anthropic.com/m/12f214efcc2f457a/original/Claude-Sonnet-4-5-System-Card.pdf",
        }
        self.assertFalse(scan.record_source_integrity_ok(iasr_chimera))

        correct = {
            "title": "Study to identify key strategic digital technologies for EU research and innovation funding beyond 2027",
            "source": "European Commission — Digital Strategy",
            "link": "https://digital-strategy.ec.europa.eu/en/activities/study-identify-digital-technologies-next-eu-research-and-innovation-fund",
        }
        self.assertTrue(scan.record_source_integrity_ok(correct))

    def test_legacy_sitemap_lastmod_rows_are_purged(self):
        row = {
            "title": "Study to identify key strategic digital technologies for EU research and innovation funding beyond 2027",
            "source": "European Commission — Digital Strategy",
            "link": "https://digital-strategy.ec.europa.eu/en/activities/study-identify-digital-technologies-next-eu-research-and-innovation-fund",
            "date": "2026-07-31",
            "date_basis": "sitemap_lastmod",
            "strand": "A",
        }
        clean, removed = scan._sanitize_saved_radar({"strand_a": [row], "strand_b": [], "strand_c": []})
        self.assertEqual(clean["strand_a"], [])
        self.assertEqual(removed["strand_a"], 1)

    def test_ongoing_study_webpage_is_not_a_published_study(self):
        reason = scan.document_exclusion_reason(
            "Study to identify key strategic digital technologies for EU research and innovation funding beyond 2027",
            "Collecting evidence on Research & Innovation needs. The study aims to identify priorities and will provide recommendations after stakeholder consultations.",
            "https://digital-strategy.ec.europa.eu/en/activities/study-identify-digital-technologies-next-eu-research-and-innovation-fund",
            "",
        )
        self.assertEqual(reason, "hard exclusion: ongoing study/project page")

    def test_saved_history_sanitizer_does_not_resurrect_bad_link_rows(self):
        bad = {
            "title": "International AI Safety Report 2026",
            "source": "International AI Safety Report",
            "link": "https://assets.anthropic.com/m/12f214efcc2f457a/original/Claude-Sonnet-4-5-System-Card.pdf",
            "strand": "C",
        }
        good = {
            "title": "Europe hails AI gigafactory plan, but industry fears deeper US tech reliance",
            "source": "South China Morning Post",
            "link": "https://www.scmp.com/economy/example",
            "date": "2026-08-07",
            "strand": "C",
        }
        clean, removed = scan._sanitize_saved_radar({"strand_a": [], "strand_b": [], "strand_c": [bad, good]})
        self.assertEqual(removed["strand_c"], 1)
        self.assertEqual(len(clean["strand_c"]), 1)
        self.assertEqual(clean["strand_c"][0]["source"], "South China Morning Post")

    def test_rejection_funnel_is_explicit_and_sequential(self):
        old = scan.ADMISSION_DIAGNOSTICS.copy()
        try:
            scan.ADMISSION_DIAGNOSTICS.clear()
            scan.ADMISSION_DIAGNOSTICS.update({
                "openalex_raw_records": 100,
                "openalex_evaluated": 60,
                "openalex_defer_insufficient_text": 10,
                "openalex_reject_no_direct_eu": 20,
                "openalex_reject_no_ri": 10,
                "openalex_reject_no_strategic_context": 5,
                "openalex_admitted_gate": 5,
                "openalex_metadata_rescue_attempted": 4,
                "openalex_metadata_rescue_recovered": 2,
                "openalex_metadata_rescue_admitted": 1,
            })
            funnel = scan.build_admission_rejection_funnel(unique_gate_candidates=4, genuinely_new_candidates=3)
        finally:
            scan.ADMISSION_DIAGNOSTICS.clear()
            scan.ADMISSION_DIAGNOSTICS.update(old)
        self.assertEqual(funnel["raw_records_seen"], 100)
        self.assertEqual(funnel["enough_text_to_judge"], 50)
        self.assertEqual(funnel["direct_eu_scope_remaining"], 30)
        self.assertEqual(funnel["central_eu_ri_scope_remaining"], 30)
        self.assertEqual(funnel["substantive_ri_remaining"], 20)
        self.assertEqual(funnel["strategic_context_remaining"], 20)
        self.assertFalse(funnel["strategic_context_gate_active"])
        self.assertEqual(funnel["genuinely_new_unique_ab"], 3)
        self.assertEqual(funnel["metadata_text_rescue"]["admitted_after_recovery"], 1)

    def test_optional_openalex_key_is_attached_only_at_request_time(self):
        captured = {}
        def fake_get(url, **kwargs):
            captured["url"] = url
            captured.update(kwargs)
            return object()
        old_key = scan.OPENALEX_API_KEY
        try:
            scan.OPENALEX_API_KEY = "test-secret-never-persist"
            with mock.patch.object(scan.SESSION, "get", side_effect=fake_get):
                scan.openalex_get("works", params={"search": "x"}, timeout=3)
        finally:
            scan.OPENALEX_API_KEY = old_key
        self.assertEqual(captured["params"]["api_key"], "test-secret-never-persist")
        self.assertNotIn("api_key", captured["url"])

    def test_snowball_reports_seed_resolution_429_instead_of_silent_zero(self):
        seed = {
            "title": "The Global Landscape of National AI Strategies",
            "date": "2026-07-28",
            "source_tier": "Tier 3",
            "type": "working paper",
            "eu_relevance": "direct",
            "link": "https://example.invalid/radu",
            "_snowball_pinned": True,
        }
        warnings = []
        with mock.patch.object(scan, "_snowball_seed_pool", return_value=[seed]), \
             mock.patch.object(scan, "_snowball_resolve_seed", side_effect=scan.OpenAlexRateLimit("429")):
            rows, stats = scan.collect_citation_snowball({}, [], warnings, time.monotonic() + 30, {})
        self.assertEqual(rows, [])
        self.assertEqual(stats["status"], "blocked_openalex_429")
        self.assertTrue(stats["rate_limited"])
        self.assertEqual(stats["seeds_planned"], 1)
        self.assertEqual(stats["seeds_resolved"], 0)
        self.assertTrue(any("429" in x for x in warnings))


class V1719RecallModelTests(unittest.TestCase):
    def test_europe_and_ri_can_be_in_different_abstract_sentences_without_strategy_words(self):
        title = "Changing patterns in university research"
        abstract = (
            "The analysis covers universities in Germany, France and the Netherlands. "
            "We measure changes in research funding, publication output and laboratory productivity over ten years. "
            "The results identify persistent shifts in the organisation of scientific work."
        )
        ev = scan.gate_scope(title, abstract, "", 1, source_kind="scholarly")
        self.assertTrue(ev["a_pass"])
        self.assertEqual(ev["eu_relevance"], "direct")
        self.assertEqual(ev["a_route"], "ri-relevance-assessment")

    def test_incidental_europe_background_does_not_make_chile_paper_direct_a(self):
        title = "Translating global innovation scripts: science and innovation policy and organisational change in Chilean universities"
        abstract = (
            "Responses are path-dependent across Chilean universities. "
            "Research on science and innovation policy in higher education has been dominated by evidence from Europe and North America."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertFalse(ev["centrality_pass"])
        self.assertIn("incidental", ev["centrality_reason"])

    def test_single_portuguese_dataset_location_does_not_create_eu_ri_centrality(self):
        title = "AI-Powered Student Dropout Prediction and Personalized Intervention Using TC-Net in Education"
        abstract = (
            "This research introduces an AI-based method for early detection of at-risk students "
            "using a dataset from two schools in Portugal."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertFalse(ev["centrality_pass"])

    def test_historical_europe_reference_does_not_make_africa_china_paper_eu_central(self):
        title = "Revisiting Dependency in the Twenty-First Century: A Critical Analysis of Africa-China Relations"
        abstract = (
            "The paper studies trade, infrastructure finance and technology transfer in Africa-China relations. "
            "It compares recent reliance on China with historical African dependence on European colonial powers."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertFalse(ev["centrality_pass"])

    def test_european_hydrogen_research_infrastructure_passes_without_strategy_words(self):
        title = "Research and technology infrastructures in the European hydrogen economy: Status, needs and innovation concepts"
        abstract = (
            "Research and Technology Infrastructures are central enablers of hydrogen technology development in Europe. "
            "This review assesses the European infrastructure landscape and identifies needs across the hydrogen value chain."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertTrue(ev["a_pass"])
        self.assertTrue(ev["centrality_pass"])
        self.assertEqual(ev["a_route"], "ri-relevance-assessment")

    def test_eu_quantum_policy_with_actual_research_funding_mechanism_still_passes(self):
        title = "How the European Commission aims to promote the EU quantum sector through the Cloud and AI Development Act"
        abstract = "The proposal creates a European framework for quantum and cloud capacity."
        body = "The measure supports funding for quantum research infrastructure and technology development in the EU."
        ev = scan.gate_scope(title, abstract, body, 3, source_kind="institutional")
        self.assertTrue(ev["a_pass"])
        self.assertTrue(ev["centrality_pass"])

    def test_admission_repair_reopens_targeted_a_recall_without_full_reset(self):
        previous = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        # Make the contract deterministic even when the uploaded post-scan state has
        # already completed this recovery version.
        previous = dict(previous)
        previous["scan_state"] = dict(previous.get("scan_state") or {})
        previous["scan_state"]["a_recall_recovery_version"] = "older-recovery-version"
        state = scan.initial_scan_state(previous)
        self.assertFalse(state.get("recall_reset_this_run"))
        self.assertEqual(state.get("openalex_cursor"), (previous.get("scan_state") or {}).get("openalex_cursor"))
        self.assertEqual(state.get("crossref_broad_cursor"), (previous.get("scan_state") or {}).get("crossref_broad_cursor"))
        self.assertNotEqual(state.get("a_recall_recovery_version"), scan.A_RECALL_RECOVERY_VERSION)
        self.assertGreaterEqual(scan.A_RECALL_RECOVERY_SOURCES_PER_SCAN, 10)

    def test_direct_eu_strategic_tech_can_use_main_ri_evidence_without_duplicate_centrality_vocabulary(self):
        title = "EUROPEAN CHIPS ACT 2.0: STRATEGIC AUTONOMY AND TECHNOLOGICAL LEADERSHIP OF THE EU IN THE GLOBAL SEMICONDUCTOR ECOSYSTEM"
        abstract = (
            "The analysis assesses semiconductor innovation capacity and technological leadership in the European Union. "
            "It examines how the Chips Act can strengthen research, scale-up capability and strategic autonomy."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertTrue(ev["a_pass"])
        self.assertTrue(ev["centrality_pass"])
        self.assertIn(ev["centrality_reason"], {"title_eu_ri_central", "eu_title_with_substantive_ri", "source_supported_eu_ri_bridge"})

    def test_eic_dual_use_innovation_source_is_not_lost_to_domain_vocabulary_mismatch(self):
        title = "The European Innovation Council opens to defence and dual-use technologies — amended EIC Work Programme 2026"
        abstract = (
            "The EIC now funds defence and dual-use start-ups directly, turning the civil-military innovation shift "
            "into an operating EU scale-up instrument rather than only a policy proposal."
        )
        ev = scan.gate_scope(title, abstract, "", 1, source_kind="institutional")
        self.assertTrue(ev["a_pass"])
        self.assertTrue(ev["centrality_pass"])
        self.assertIn("dual-use", " ".join(ev["ri_evidence"]).lower())

    def test_soft_centrality_rescue_still_rejects_incidental_europe_comparator(self):
        title = "AI startup innovation and competitiveness in China"
        abstract = (
            "The European Union is included as a comparator. "
            "We study artificial intelligence startup innovation, commercialization and competitiveness in China."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertFalse(ev["centrality_pass"])

    def test_eu_programme_list_on_unrelated_sector_page_is_not_ri_central(self):
        title = "EU support for the news media sector"
        abstract = (
            "The European Commission works to support a pluralistic media environment. "
            "Actions are part of innovation programmes (Digital Europe, Horizon Europe)."
        )
        ev = scan.gate_scope(title, abstract, "", 1, source_kind="institutional")
        self.assertFalse(ev["a_pass"])
        self.assertFalse(ev["centrality_pass"])
        self.assertEqual(ev["centrality_reason"], "ri_not_central")

    def test_institutional_event_recap_is_not_strand_a_evidence(self):
        title = "ALLEA and the Scientific Advice Mechanism Host Science Policy Events in Turin"
        abstract = "Members from across Europe met to discuss trust in science and future activities."
        ev = scan.gate_scope(title, abstract, "", 1, source_kind="institutional")
        self.assertFalse(ev["a_pass"])
        self.assertEqual(ev["centrality_reason"], "event_recap_not_substantive_evidence")

    def test_brain_data_sharing_eu_framework_can_link_across_adjacent_sentences(self):
        title = "Accelerating Research on Brain Aging: Enabling Brain Imaging Data Sharing in the Open Science Landscape"
        abstract = (
            "Substantial barriers for sharing neuroimaging data constrain scientific collaboration and medical innovation. "
            "We highlight the need for simplified and unified legal frameworks compliant with the General Data Protection Regulation of the European Union."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertTrue(ev["a_pass"])
        self.assertTrue(ev["centrality_pass"])

    def test_elite_journal_watchlist_is_source_first_and_not_news_only(self):
        watch = scan.CONFIG.get("top_journal_watchlist", [])
        self.assertIn("Nature", watch)
        self.assertIn("Science", watch)
        self.assertIn("Proceedings of the National Academy of Sciences", watch)
        self.assertGreaterEqual(len(watch), 6)

    def test_core_news_has_direct_source_lane_in_addition_to_google_news(self):
        direct = {x.get("domain") for x in scan.CONFIG.get("direct_news_sources", [])}
        self.assertIn("sciencebusiness.net", direct)
        self.assertIn("researchprofessionalnews.com", direct)

    def test_summer_school_page_is_not_strand_a_evidence(self):
        title = "ELLIS Summer School 2026: AI for Research | ELLIS Institute Finland"
        reason = scan.document_exclusion_reason(
            title,
            "This summer school brings together researchers and students to explore how AI can transform scientific research.",
            "https://www.ellisinstitute.fi/ellis-summer-school-2026",
        )
        self.assertIsNotNone(reason)
        self.assertIn("summer school", reason)

    def test_procurement_style_acquisition_notice_is_not_strand_a_evidence(self):
        title = "Acquisition, Delivery, Installation and Hardware and Software Maintenance to Upgrade INNOVATE, the EuroHPC Industrial Supercomputer"
        reason = scan.document_exclusion_reason(title, "EuroHPC infrastructure upgrade contract")
        self.assertEqual(reason, "hard exclusion: procurement/acquisition notice")

    def test_jrc_repository_handle_is_formal_evidence_not_weak_signal(self):
        title = "The adoption of Generative AI in EU public administrations: exploring individual behaviours and organisational approaches"
        link = "https://publications.jrc.ec.europa.eu/repository/handle/JRC147095"
        self.assertTrue(scan.formal_evidence_product(title, "", "JRC Publications Repository", link))
        item = {
            "headline": title,
            "source": "JRC Publications Repository",
            "date": "2026-06-19",
            "link": link,
            "_desc": "The report examines GenAI adoption in European public administrations.",
            "_themes": ["critical and emerging technologies"],
            "_entities": [],
        }
        self.assertEqual(scan.anchor_news([item], []), [])

    def test_jrc_visible_bibliographic_date_overrides_later_cms_metadata(self):
        html = """<html><head><meta name='date' content='2026-09-01'></head><body><main>
        <h1>The adoption of Generative AI in EU public administrations</h1>
        <p>Substantive report abstract.</p><div>MIKALEF Patrick; MEDAGLIA Rony;</div>
        <div>2026-06-19</div><div>Publications Office of the European Union</div>
        </main></body></html>"""
        soup = scan.BeautifulSoup(html, "html.parser")
        got = scan._jrc_repository_publication_date(
            soup, "https://publications.jrc.ec.europa.eu/repository/handle/JRC147095"
        )
        self.assertEqual(str(got), "2026-06-19")

    def test_routine_research_award_announcement_is_not_strand_a_evidence(self):
        title = "Six ERC grantees win 2024 Public Engagement with Research Award"
        abstract = (
            "The European Research Council announced winners of its public engagement award. "
            "The ERC is funded under Horizon Europe and supports frontier research across Europe."
        )
        ev = scan.gate_scope(title, abstract, "", 1, source_kind="institutional")
        self.assertFalse(ev["a_pass"])
        self.assertEqual(ev["centrality_reason"], "routine_award_or_prestige_announcement")

    def test_awards_landing_page_is_not_strand_a_evidence(self):
        title = "The European Capital of Innovation Awards"
        abstract = (
            "Cities in EU Member States or Horizon Europe Associated Countries can apply. "
            "The award promotes local innovation ecosystems, knowledge transfer and capacity building."
        )
        ev = scan.gate_scope(title, abstract, "", 1, source_kind="institutional")
        self.assertFalse(ev["a_pass"])
        self.assertEqual(ev["centrality_reason"], "routine_award_or_prestige_announcement")

    def test_horizon_project_provenance_does_not_make_marine_policy_paper_ri_central(self):
        title = "Assessing the role and functioning of Science-Policy-Society Interfaces in EU Green Deal-related marine policies"
        abstract = (
            "This paper uses a methodology from the Horizon Europe CrossGov project to assess SPSIs "
            "in EU marine-policy governance and delivery of Green Deal objectives."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertEqual(ev["centrality_reason"], "ri_not_central")

    def test_rd_expenditure_as_environmental_covariate_is_not_ri_central(self):
        title = "The impact of socio-economic factors and digital performance on environmental sustainability: the case of European Union"
        abstract = (
            "Increases in gross domestic product per capita, non-renewable energy consumption, agricultural value added, "
            "research and development expenditures and digital indicators are tested as factors associated with environmental degradation."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertEqual(ev["centrality_reason"], "ri_not_central")

    def test_academic_library_service_innovation_is_not_core_ri_system_evidence(self):
        title = "The usefulness of knowledge from library staff, faculty and students for developing service innovations in academic libraries"
        abstract = (
            "Drawing on innovation ecosystem perspectives, the study uses survey data from 290 academic libraries in 31 European countries "
            "to examine service innovation and collaboration."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertEqual(ev["centrality_reason"], "local_applied_study_not_ri_system_evidence")

    def test_local_clinical_service_research_is_not_core_eu_ri_evidence(self):
        title = "PS09 Building an integrated psychodermatology service in central Europe: clinical implementation and research experience from Pécs, Hungary"
        abstract = (
            "Alongside clinical implementation, a structured research programme was established at the local service. "
            "The work reports clinical experience from Pécs, Hungary."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertEqual(ev["centrality_reason"], "local_applied_study_not_ri_system_evidence")

    def test_european_conceptual_origin_does_not_make_china_innovation_study_eu_central(self):
        title = "How regions make missions work: regioning mechanisms in Zhongguancun's innovation trajectory"
        abstract = (
            "The study examines mission-oriented innovation policy in Zhongguancun, China. "
            "It extends the regioning concept beyond its original European federal contexts to China's governance system."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertFalse(ev["centrality_pass"])

    def test_signal_claim_falls_back_to_event_headline_when_body_is_fragment(self):
        got = scan._signal_what_claim(
            "as European industries scale up AI adoption.",
            "Second EU-Taiwan Semiconductor Industry Dialogue",
        )
        self.assertEqual(got, "The EU and Taiwan held their second semiconductor industry dialogue.")

    def test_bundle_history_merge_cannot_resurrect_fixed_precision_false_positives(self):
        bad_award = {
            "title": "Six ERC grantees win 2024 Public Engagement with Research Award",
            "summary": "The ERC announced award winners under Horizon Europe.",
            "type": "official notice / primary source",
        }
        bad_local = {
            "title": "PS09 Building an integrated psychodermatology service in central Europe: clinical implementation and research experience from Pécs, Hungary",
            "summary": "A clinical service in Pécs, Hungary established a structured research programme.",
            "type": "peer-reviewed article",
        }
        good = {
            "title": "Research and technology infrastructures in the European hydrogen economy: Status, needs and innovation concepts",
            "summary": "European research infrastructures enable hydrogen technology development and innovation.",
            "type": "peer-reviewed article",
        }
        self.assertTrue(scan._saved_ab_high_confidence_precision_reject(bad_award))
        self.assertTrue(scan._saved_ab_high_confidence_precision_reject(bad_local))
        self.assertFalse(scan._saved_ab_high_confidence_precision_reject(good))

    def test_new_ab_unique_count_uses_retained_new_rows_not_gate_candidates(self):
        a = [{
            "title": "New retained paper", "link": "https://doi.org/10.1/new",
            "source": "Journal", "strand": "A", "new_this_scan": True,
        }]
        b = [{
            "title": "Old retained method", "link": "https://doi.org/10.1/old",
            "source": "Journal", "strand": "B", "new_this_scan": True,
        }]
        old_id = scan.identity(scan.internalize_previous(b[0]))
        self.assertEqual(scan.new_ab_unique_count(a, b, {old_id}), 1)

    def test_historical_subject_without_current_implication_is_outside_live_radar_goal(self):
        title = "The Making of the ‘French Research Model’: Re-exploring the National and the International (1955-1965)"
        abstract = (
            "This article examines the French model for research governance that emerged in the 1960s. "
            "Drawing on transnational history, it reconstructs how scientific policy models circulated internationally."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertEqual(ev["centrality_reason"], "historical_subject_outside_live_ri_goal")

    def test_historical_material_with_explicit_current_ri_implication_can_still_pass(self):
        title = "Lessons from the French Research Model (1955-1965) for current European research governance"
        abstract = (
            "The paper uses historical evidence to derive implications for current European research governance, "
            "research funding and science policy reform."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertTrue(ev["a_pass"])
        self.assertTrue(ev["centrality_pass"])

    def test_early_modern_history_is_outside_live_radar_even_with_technology_transfer_language(self):
        title = "Genoese Migration and Technology Transfer in the Early-Modern Spanish Monarchy"
        abstract = (
            "The paper examines Genoese migration, manufacturing knowledge and technology transfer "
            "within the Spanish monarchy."
        )
        self.assertTrue(scan._historical_subject_without_current_ri_implication(title, abstract, ""))
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertEqual(ev["centrality_reason"], "historical_subject_outside_live_ri_goal")

    def test_current_neo_academic_cold_war_paper_is_not_mistaken_for_history(self):
        title = "The Neo-Academic Cold War: Political Traumas and Transnational Paranoia"
        abstract = (
            "A new Cold War is emerging, producing rival silos of transnational science cooperation and science diplomacy "
            "involving the European Union, the United States, China and Russia."
        )
        self.assertFalse(scan._historical_subject_without_current_ri_implication(title, abstract, ""))

    def test_saved_sanitizer_removes_early_modern_history_with_same_predicate(self):
        bad = {
            "title": "Genoese Migration and Technology Transfer in the Early-Modern Spanish Monarchy",
            "summary": "An early-modern study of technology transfer in the Spanish monarchy.",
            "type": "peer-reviewed article",
            "source": "Itinerario",
            "date": "2026-05-04",
            "link": "https://doi.org/10.1017/s0165115326100588",
        }
        saved = {"strand_a": [bad], "strand_b": [], "strand_c": []}
        clean, removed = scan._sanitize_saved_radar(saved)
        self.assertEqual(clean["strand_a"], [])
        self.assertEqual(removed["strand_a"], 1)

    def test_c_rescue_can_admit_directly_european_unanchored_emerging_signal(self):
        title = "EU launches pilot research security scheme for quantum universities"
        desc = (
            "The European Commission launched a pilot partnership to strengthen quantum research security "
            "and capability across European universities."
        )
        item = {
            "headline": title,
            "source": "Science|Business",
            "date": "2026-09-01",
            "link": "https://sciencebusiness.net/example",
            "_desc": desc,
            "_themes": scan.themes_for(title + " " + desc),
            "_entities": scan.distinct_matches(title + " " + desc, scan.ENTITY_TERMS + scan.GEO_ACTORS),
        }
        self.assertEqual(scan.anchor_news([item], []), [])
        rescued = scan.anchor_news([item], [], allow_unanchored=True)
        self.assertEqual(len(rescued), 1)
        self.assertEqual(rescued[0]["anchor_status"], "unanchored_emerging")
        self.assertEqual(rescued[0]["signal_confidence"], "lower")

    def test_c_rescue_unanchored_route_still_requires_direct_european_scope(self):
        title = "US launches pilot quantum research security scheme"
        desc = "A new pilot partnership will tighten quantum research security and technology access in the United States."
        item = {
            "headline": title,
            "source": "Reuters",
            "date": "2026-09-01",
            "link": "https://reuters.com/example",
            "_desc": desc,
            "_themes": scan.themes_for(title + " " + desc),
            "_entities": scan.distinct_matches(title + " " + desc, scan.ENTITY_TERMS + scan.GEO_ACTORS),
        }
        self.assertEqual(scan.anchor_news([item], [], allow_unanchored=True), [])

    def test_saved_unanchored_emerging_signal_survives_c_revalidation(self):
        title = "EU launches pilot research security scheme for quantum universities"
        desc = "The European Commission launched a pilot partnership to strengthen quantum research security across Europe."
        item = {
            "headline": title,
            "source": "Science|Business",
            "date": "2026-08-30",
            "link": "https://sciencebusiness.net/example-saved",
            "anchor": "",
            "anchor_basis": "unanchored-emerging",
            "anchor_status": "unanchored_emerging",
            "signal_confidence": "lower",
            "watch_theme": "research security / foreign interference",
            "signal_type": "instantiates",
            "signal_kind": "cooperation / alignment",
            "what": title + ".",
            "core_message": title + ".",
            "why_it_matters": "This may affect European research security and capability-building.",
            "signal_note": title + ". This may affect European research security and capability-building.",
            "evidence_status": "low",
            "evidence_role": "weak_signal",
            "reframing_dimensions": ["new actor move"],
        }
        out, stats = scan.revalidate_saved_c({"strand_a": [], "strand_c": [item]})
        self.assertEqual(stats["strand_c_kept"], 1)
        self.assertEqual(out["strand_c"][0]["anchor_status"], "unanchored_emerging")

    def test_c_floor_detailed_reasons_are_log_only_not_public_note(self):
        scanner_text = (ROOT / "scripts" / "scan_radar.py").read_text(encoding="utf-8")
        self.assertIn("Public scan health is intentionally unchanged", scanner_text)
        self.assertIn("if 0 < new_c_count < 3 else", scanner_text)
        index_text = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("C floor unmet", index_text)
        self.assertNotIn("C_INTERNAL", index_text)

    def test_global_medical_ai_review_with_europe_only_in_collaboration_list_is_not_a(self):
        title = "(457) The Role of Artificial Intelligence in Sexual Medicine and Sexual Health: Two Decades of Research and Innovation"
        abstract = (
            "The United States stands as the leading contributor, followed by the United Kingdom, "
            "with significant international collaborations involving Australia, China, India, Canada, "
            "and several others across Europe, Africa and Asia. The review maps two decades of AI research."
        )
        ev = scan.gate_scope(title, abstract, "", 2, source_kind="scholarly")
        self.assertFalse(ev["a_pass"])
        self.assertFalse(ev["centrality_pass"])

    def test_final_shared_worthiness_guard_catches_known_cross_route_false_positives(self):
        local = {
            "title": "PS09 Building an integrated psychodermatology service in central Europe: clinical implementation and research experience from Pécs, Hungary",
            "summary": "A structured research programme was established alongside local clinical implementation in Pécs, Hungary.",
            "type": "peer-reviewed article",
        }
        global_review = {
            "title": "The Role of Artificial Intelligence in Sexual Medicine and Sexual Health: Two Decades of Research and Innovation",
            "summary": "The United States is the leading contributor with international collaborations across Europe, Africa and Asia.",
            "type": "peer-reviewed article",
        }
        good = {
            "title": "IRIS—The Innovative Research Infrastructure on Applied Superconductivity in Italy",
            "summary": "IRIS establishes a distributed Italian research infrastructure supporting long-term R&D in superconducting technologies.",
            "type": "peer-reviewed article",
        }
        self.assertFalse(scan.final_ab_candidate_worthiness(local))
        self.assertFalse(scan.final_ab_candidate_worthiness(global_review))
        self.assertTrue(scan.final_ab_candidate_worthiness(good))

    def test_nature_science_and_policy_journals_are_first_class_watch_sources(self):
        elite = scan.CONFIG.get("top_journal_watchlist", [])
        policy = scan.CONFIG.get("priority_policy_journal_watchlist", [])
        direct = {x.get("name"): x for x in scan.CONFIG.get("direct_top_journal_sources", [])}
        self.assertIn("Nature", elite)
        self.assertIn("Science", elite)
        self.assertIn("Studies in Higher Education", policy)
        self.assertIn("New Political Economy", policy)
        self.assertTrue(direct["Nature"].get("always"))
        self.assertTrue(direct["Science"].get("always"))
        tier, rank, label = scan.source_rank_for_journal("Nature")
        self.assertEqual(tier, 1)
        self.assertIn("journal-watch", label)
        self.assertLess(rank, 2.0)

    def test_direct_nature_page_can_feed_a_without_crossref(self):
        html = """<html><head>
        <meta name='citation_title' content="Europe should adapt, not copy, China's practical PhD">
        <meta name='citation_publication_date' content='2026-09-01'>
        <meta name='citation_doi' content='10.1038/d41586-026-02736-6'>
        <meta name='citation_author' content='A. Żukowski'>
        <meta name='description' content='European universities should adapt doctoral training to strengthen research careers, industry links and innovation capability in Europe.'>
        <meta name='citation_article_type' content='Comment'>
        </head><body><main><p>Current European doctoral and research policy implications are discussed.</p></main></body></html>"""
        src = {"name": "Nature", "domain": "nature.com"}
        old_floor = scan.DATE_FLOOR
        try:
            scan.DATE_FLOOR = scan.dt.date(2026, 5, 1)
            item, c = scan._direct_journal_article_from_html(html, "https://www.nature.com/articles/example", src, scan.DATE_FLOOR)
        finally:
            scan.DATE_FLOOR = old_floor
        self.assertIsNotNone(item)
        self.assertEqual(item["strand"], "A")
        self.assertEqual(item["discovery_provenance"], "direct_top_journal")
        self.assertIsNone(c)

    def test_direct_major_journal_talent_news_can_feed_c_candidate_pool(self):
        html = """<html><head>
        <meta name='citation_title' content='India launches return fellowships to lure scientists back'>
        <meta name='citation_publication_date' content='2026-09-01'>
        <meta name='citation_doi' content='10.1038/example-talent'>
        <meta name='description' content='India launched a plan with return fellowships and research funding to attract scientists in AI, quantum, biotechnology and advanced materials.'>
        <meta name='citation_article_type' content='News'>
        </head><body><main><p>The move intensifies global competition for research talent.</p></main></body></html>"""
        src = {"name": "Nature", "domain": "nature.com"}
        old_floor = scan.DATE_FLOOR
        try:
            scan.DATE_FLOOR = scan.dt.date(2026, 5, 1)
            item, c = scan._direct_journal_article_from_html(html, "https://www.nature.com/articles/example-talent", src, scan.DATE_FLOOR)
        finally:
            scan.DATE_FLOOR = old_floor
        self.assertIsNone(item)
        self.assertIsNotNone(c)
        self.assertEqual(c["source"], "Nature")
        self.assertTrue(c.get("_direct_journal_source"))

    def test_c_floor_has_reserved_runtime_after_other_network_stages_stop(self):
        reserve = int(scan.CONFIG.get("network_reserve_seconds", 0))
        minimum = int(scan.CONFIG.get("c_floor_rescue_min_seconds_remaining", 0))
        post = int(scan.CONFIG.get("c_floor_post_reserve_seconds", 0))
        self.assertGreater(reserve, minimum)
        self.assertGreater(minimum, post + 20)
        scanner_text = (ROOT / "scripts" / "scan_radar.py").read_text(encoding="utf-8")
        self.assertIn("budget_remaining() <= post_reserve + 25", scanner_text)


    def test_direct_journal_feed_survives_blocked_publisher_hub(self):
        import types
        entry = types.SimpleNamespace(
            title="Europe should adapt, not copy, China's practical PhD",
            link="https://www.nature.com/articles/example-feed",
            summary="European universities should adapt doctoral training to strengthen research careers and innovation capability in Europe.",
            published_parsed=time.strptime("2026-09-01", "%Y-%m-%d"),
            tags=[{"term": "Comment"}],
            authors=[{"name": "A. Example"}],
        )
        class Resp:
            def __init__(self, status, content=b'', text='', ctype='text/html'):
                self.status_code=status; self.content=content; self.text=text; self.url='https://www.nature.com/nature/articles'; self.headers={'content-type':ctype}
        def fake_get(url, *args, **kwargs):
            if 'format=rss' in url:
                return Resp(200, content=b'<rss/>', ctype='application/rss+xml')
            return Resp(403)
        src={
            'name':'Nature','domain':'nature.com','hub':'https://www.nature.com/nature/articles',
            'feed_urls':['https://www.nature.com/nature/articles?format=rss'],
            'article_path_regex':'/articles/','always':True,
        }
        old_floor=scan.DATE_FLOOR
        try:
            scan.DATE_FLOOR=scan.dt.date(2026,5,1)
            with mock.patch.object(scan.SESSION, 'get', side_effect=fake_get), mock.patch.object(scan.feedparser, 'parse', return_value=types.SimpleNamespace(entries=[entry])):
                ab, cc=scan.collect_direct_top_journals([src], [], stage_deadline=time.monotonic()+30, execution_stats={})
        finally:
            scan.DATE_FLOOR=old_floor
        self.assertEqual(len(ab),1)
        self.assertEqual(ab[0]['source'],'Nature')
        self.assertEqual(cc,[])

    def test_top_journal_sources_have_non_html_fallbacks(self):
        direct={x.get('name'):x for x in scan.CONFIG.get('direct_top_journal_sources',[])}
        self.assertTrue(direct['Nature'].get('feed_urls'))
        self.assertTrue(direct['Science'].get('feed_urls'))
        self.assertTrue(direct['Science'].get('fallback_hubs'))
        self.assertTrue(direct['Proceedings of the National Academy of Sciences'].get('feed_urls'))

    def test_institutional_collection_and_topic_landing_pages_are_not_a_evidence(self):
        series={
            'title':'Research and innovation paper series',
            'summary':'Working documents from several years are listed here with links to publications.',
            'link':'https://research-and-innovation.ec.europa.eu/strategy/support-policy-making/support-national-research-and-innovation-policy-making/research-and-innovation-paper-series_en',
            'type':'research/policy paper',
        }
        open_science={
            'title':'Open science',
            'summary':"The Commission's open science policy, expert groups, aims, plans under Horizon Europe, latest news.",
            'link':'https://research-and-innovation.ec.europa.eu/strategy/strategy-research-and-innovation/our-digital-future/open-science_en',
            'type':'research/policy paper',
        }
        access_call={
            'title':'Open access calls to JRC Research Infrastructures',
            'summary':'The JRC offers access calls to facilities for researchers from EU Member States.',
            'link':'https://joint-research-centre.ec.europa.eu/open-access-research-infrastructures_en',
            'type':'research/policy paper',
        }
        self.assertFalse(scan.final_ab_candidate_worthiness(series))
        self.assertFalse(scan.final_ab_candidate_worthiness(open_science))
        self.assertFalse(scan.final_ab_candidate_worthiness(access_call))

    def test_jrc_distribution_notice_is_navigation_boilerplate(self):
        msg='You are not authorized to publish or distribute it outside the European Commission.'
        self.assertTrue(scan.source_navigation_boilerplate(msg))
        summary=(msg+' The Security Research & Innovation Campus will bring together researchers and practitioners to turn innovative ideas into real solutions for a stronger and safer Europe.')
        claim=scan.concise_core_message(scan._strip_relevance_boilerplate(summary), 'JRC Security Research and Innovation Campus')
        self.assertNotIn('authorized to publish', claim.lower())

    def test_nature_return_scientist_story_can_survive_c_claim_theme_check(self):
        data=json.loads((ROOT/'radar.json').read_text(encoding='utf-8'))
        desc=('India launched return fellowships and research funding to attract scientists in AI, quantum computing, '
              'biotechnology and advanced materials, amid global competition for research talent.')
        n={
            'headline':'India launches return fellowships to lure scientists back',
            'source':'Nature','date':'2026-09-01T00:00Z',
            'link':'https://doi.org/10.1038/d41586-026-02636-9',
            '_desc':desc,'_themes':scan.themes_for(desc),
            '_entities':scan.distinct_matches(desc, scan.ENTITY_TERMS+scan.GEO_ACTORS),
        }
        claim=scan._signal_what_claim(desc,n['headline'])
        self.assertIn('research talent', claim.lower())
        rows=scan.anchor_news([n], data.get('strand_a',[]), [])
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['source'],'Nature')

    def test_c_final_reserve_can_spend_below_normal_network_reserve(self):
        self.assertTrue(scan.CONFIG.get('c_floor_final_reserve_enabled'))
        self.assertLess(int(scan.CONFIG.get('c_floor_final_save_margin_seconds', 99)), int(scan.CONFIG.get('network_reserve_seconds', 0)))
        scanner_text=(ROOT/'scripts'/'scan_radar.py').read_text(encoding='utf-8')
        self.assertIn("'C-floor final reserve', collect_news", scanner_text)
        self.assertIn('False, final_save_margin', scanner_text)

    def test_signal_anchor_theme_must_be_supported_by_the_published_claim(self):
        a = [{
            "title": "EU-China research cooperation under de-risking",
            "summary": "The EU is changing research cooperation with China through de-risking and knowledge-security rules.",
            "source": "Example journal",
            "date": "2026-07-01",
            "link": "https://doi.org/10.1000/example",
            "strand": "A",
            "eu_relevance": "direct",
        }]
        n = {
            "headline": "The new golden age of radio astronomy",
            "source": "International Telecommunication Union",
            "date": "2026-08-31",
            "link": "https://www.itu.int/hub/2026/08/the-new-golden-age-of-radio-astronomy/",
            "_desc": (
                "Technology-driven advances are creating a second golden age of radio astronomy. "
                "Elsewhere the article notes European and Chinese research cooperation in astronomy."
            ),
            "_themes": ["EU–China S&T cooperation / de-risking"],
            "_entities": ["China"],
        }
        self.assertEqual(scan.anchor_news([n], a), [])



class V171912PrecisionAndJournalTests(unittest.TestCase):
    def test_theorist_nationality_does_not_create_european_study_scope(self):
        title='Illuhmannating Technological Innovation Systems: Towards a Systems Perspective'
        abstract=(
            'The Technological Innovation Systems framework is extended using the work of German sociologist Niklas Luhmann. '
            'The paper develops a systems-theory account of innovation systems and technological innovation in general.'
        )
        ok, reason, evidence=scan.eu_ri_centrality(title, abstract, '', 'scholarly')
        self.assertFalse(ok)
        self.assertEqual(reason, 'eu_or_ri_only_incidental')

    def test_radio_astronomy_cannot_anchor_to_ev_ai_fintech(self):
        a=[{
            'title':'Strengthening U.S. Global Leadership in Electric Vehicle Supply Chains Through AI-Driven Fintech Innovation',
            'summary':'The paper examines US electric-vehicle battery supply chains and AI-driven fintech innovation.',
            'source':'Example journal','date':'2026-07-01','link':'https://doi.org/10.1000/ev','strand':'A','eu_relevance':'direct',
        }]
        desc=('Radio astronomy in Africa is driving demand for high-performance computing, advanced networking, '
              'data-intensive infrastructure and artificial intelligence for observatories.')
        n={'headline':'Evolving radio astronomy and its impact on Africa','source':'International Telecommunication Union',
           'date':'2026-08-27','link':'https://www.itu.int/hub/example','_desc':desc,
           '_themes':scan.themes_for(desc),'_entities':scan.distinct_matches(desc, scan.ENTITY_TERMS+scan.GEO_ACTORS)}
        self.assertEqual(scan.anchor_news([n],a,[]),[])

    def test_signal_what_does_not_repeat_source_name(self):
        claim='Government of Canada Invests CAD $195 Million in Xanadu to Build the Quantum Supply Chain Financial Times.'
        cleaned=scan._clean_signal_claim_source_suffix(claim,'Financial Times')
        self.assertEqual(cleaned,'Government of Canada Invests CAD $195 Million in Xanadu to Build the Quantum Supply Chain.')

    def test_saved_tis_false_positive_cannot_be_resurrected(self):
        row={
            'title':'Illuhmannating Technological Innovation Systems: Towards a Systems Perspective',
            'summary':'The Technological Innovation Systems framework operates from an economic perspective and is linked to wider environment.',
            'source':'Systems Research and Behavioral Science','date':'2026-05-26',
            'link':'https://doi.org/10.1002/sres.70089','type':'peer-reviewed article','strand':'A',
        }
        self.assertTrue(scan._saved_ab_high_confidence_precision_reject(row))

    def test_saved_itu_radio_astronomy_false_signal_fails_saved_c_gate(self):
        row={
            'headline':'Evolving radio astronomy and its impact on Africa - ITU',
            'source':'International Telecommunication Union','date':'2026-08-27',
            'link':'https://www.itu.int/hub/2026/08/evolving-radio-astronomy-and-its-impact-on-africa/',
            'signal_note':'This transition has accelerated demand for high-performance computing and advanced networking.',
            'anchor':'Strengthening U.S. Global Leadership in Electric Vehicle Supply Chains Through AI-Driven Fintech Innovation (Strand A)',
        }
        self.assertFalse(scan._saved_signal_passes(row))

    def test_europe_practical_phd_nature_title_is_a_scope(self):
        title="Europe should adapt, not copy, China's practical PhD"
        ok, reason, evidence=scan.eu_ri_centrality(title, '', '', 'scholarly')
        self.assertTrue(ok)
        self.assertIn('doctoral training', evidence)

    def test_external_biomedical_regulation_can_enter_c_discovery(self):
        title="China's regulatory innovation for new biomedical technologies"
        desc=('China introduced a regulatory framework for new biomedical technologies, changing how biotechnology '
              'research and technology development can move toward clinical and industrial use.')
        self.assertTrue(scan.weak_signal_candidate_text(title,desc))
        self.assertTrue(scan.factual_news(title,desc))

    def test_nature_science_google_news_fallback_is_configured(self):
        direct={x.get('name'):x for x in scan.CONFIG.get('direct_top_journal_sources',[])}
        for name in ('Nature','Science'):
            self.assertTrue(direct[name].get('google_news_always'))
            self.assertTrue(direct[name].get('google_news_queries'))
        self.assertIn('New Political Economy',direct)
        self.assertIn('Studies in Higher Education',direct)
        self.assertTrue(direct['New Political Economy'].get('feed_urls'))
        self.assertTrue(direct['Studies in Higher Education'].get('feed_urls'))

    def test_nature_google_news_fallback_can_produce_c_when_primary_surfaces_403(self):
        src={
            'name':'Nature','hub':'https://www.nature.com/nature/articles','domain':'nature.com','article_path_regex':'/articles/',
            'always':True,'feed_urls':['https://www.nature.com/nature/articles?format=rss'],'google_news_always':True,
            'google_news_queries':['researchers scientists research funding talent'],
        }
        entry=types.SimpleNamespace(
            title='India has an ambitious plan to lure scientists back — will it work? - Nature',
            link='https://news.google.com/rss/articles/nature-example',
            summary=('India launched return fellowships and research funding to attract scientists in AI, quantum computing, '
                     'biotechnology and advanced materials amid global competition for research talent.'),
            source=types.SimpleNamespace(title='Nature',href='https://www.nature.com'),
            published_parsed=time.struct_time((2026,9,1,8,0,0,1,244,0)), updated_parsed=None,
            published='',updated='',tags=[],authors=[]
        )
        class R:
            def __init__(self,status,content=b'',headers=None,url=''):
                self.status_code=status; self.content=content; self.headers=headers or {}; self.url=url
        def fake_get(url,*args,**kwargs):
            if 'news.google.com/rss/search' in url:
                return R(200,b'<rss/>',{'content-type':'application/rss+xml'},url)
            return R(403,b'',{'content-type':'text/html'},url)
        old_floor=scan.DATE_FLOOR
        try:
            scan.DATE_FLOOR=scan.dt.date(2026,5,1)
            with mock.patch.object(scan.SESSION,'get',side_effect=fake_get), mock.patch.object(scan.feedparser,'parse',return_value=types.SimpleNamespace(entries=[entry])):
                ab,cc=scan.collect_direct_top_journals([src],[],stage_deadline=time.monotonic()+30,execution_stats={})
        finally:
            scan.DATE_FLOOR=old_floor
        self.assertEqual(ab,[])
        self.assertEqual(len(cc),1)
        self.assertEqual(cc[0]['source'],'Nature')
        self.assertEqual(cc[0]['source_domain'],'nature.com')
        self.assertEqual(cc[0]['discovery_provenance'],'direct_top_journal_google_news')


class FrontierBridgeTests(unittest.TestCase):
    def test_frontier_bridge_exposes_placements(self):
        data = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        counts, qualifying, placements, error = scan.frontier_matrix_snapshot(data)
        self.assertEqual(error, "")
        self.assertIsInstance(counts, dict)
        self.assertIsInstance(placements, list)
        self.assertEqual(qualifying, len(placements))
        # Matrix classification must not collapse the already-vetted Strand A corpus
        # behind a second ultra-narrow phrase-template gate.  Keep a meaningful share
        # of admitted evidence eligible for source-backed row/axis classification.
        evidence_total = len(data.get("strand_a", []))
        if evidence_total:
            self.assertGreaterEqual(qualifying, int(evidence_total * 0.25))
        if placements:
            self.assertIn("cell", placements[0])
            self.assertIn("title", placements[0])


class RotationAndReaderQualityTests(unittest.TestCase):
    def test_topic_bank_interleaves_coarse_families(self):
        queries = [
            "European research talent mobility",
            "European researcher careers",
            "EU semiconductor technology sovereignty",
            "EU quantum critical technology",
            "EU research security foreign interference",
            "trusted research knowledge security",
            "Horizon Europe framework programme geopolitics",
            "FP10 European Research Area",
        ]
        bank = scan.diversified_query_bank(queries)
        first_four = [scan.query_theme(q) for q in bank[:4]]
        self.assertGreaterEqual(len(set(first_four)), 4)

    def test_priorities_preserve_scanner_lenses_and_interpret_retained_evidence_without_matrix_inference(self):
        import subprocess
        js = r"""
const P=require('./priorities/priorities.js');
const data={
 strand_a:[
  {title:'Embedded scanner risk',date:'2026-09-01',link:'https://example.org/risk',matrix_auto_cell:'high-high',strategic_classification_source:'source_text',strategic_classification:{primary:'risk',lenses:[{type:'risk',status:'open',passage:'source passage',components:{mechanism:'could restrict',carrier:'government',asset:'research access'}}]}},
  {title:'Matrix only item',date:'2026-09-03',link:'https://example.org/matrix',matrix_auto_cell:'high-high',summary:'High impact and high sensitivity.'},
  {title:'Retained analytical risk',date:'2026-09-02',link:'https://example.org/derived-risk',summary:'A proposed White House rule could restrict international research collaboration, exposing European research access to United States government control.'},
  {title:'Open quantum call',date:'2026-09-02',link:'https://example.org/opp',summary:'EuroHPC call QTI-2026 aims to strengthen European quantum capability through Horizon Europe. Status Open; applications close in November 2026.'}
 ],
 strand_c:[{headline:'China places EU research organisations on its export control list, barring dual-use exports with immediate effect',date:'2026-07-24',link:'https://example.org/shock',signal_note:'China places EU research organisations on its export control list, barring dual-use exports with immediate effect.'}],
 strategic_pathways:[{title:'Filed opportunity',date:'2026-09-04',link:'https://example.org/filed-opportunity',strategic_classification_source:'source_text',strategic_classification:{primary:'opportunity',lenses:[{type:'opportunity',status:'open',passage:'source passage',components:{mechanism:'could leverage',actor:'agency',instrument:'procurement',gain:'capacity'}}]}}]
};
const v=P.buildPriorityView(data,{limit:8});
if(v.stats.risks!==2) process.exit(2);
if(!v.risks.some(x=>x.title==='Embedded scanner risk'&&x.interpretationBasis==='scanner_source_classification')) process.exit(3);
if(!v.risks.some(x=>x.title==='Retained analytical risk'&&x.interpretationBasis==='repository_evidence_interpretation')) process.exit(4);
if(v.risks.some(x=>x.title==='Matrix only item')||v.opportunities.some(x=>x.title==='Matrix only item')) process.exit(5);
if(v.stats.opportunities!==2||!v.opportunities.some(x=>x.title==='Open quantum call')) process.exit(6);
if(v.stats.externalShocks!==1||v.externalShocks[0].interpretationBasis!=='repository_evidence_interpretation') process.exit(7);
"""
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)

    def test_external_shock_interpretation_covers_non_policy_exogenous_event_families(self):
        import subprocess
        js = r"""
const P=require('./priorities/priorities.js');
const data={strand_c:[
 {headline:'Earthquake struck without prior notice, forcing a European research facility to shut down',date:'2026-09-02',link:'https://example.org/quake',signal_note:'A major earthquake struck without prior notice and forced a European research facility to shut down, suspending research operations and experiments.'},
 {headline:'Ransomware cyberattack hit a European university network overnight',date:'2026-09-02',link:'https://example.org/cyber',signal_note:'A ransomware cyberattack hit a European university network overnight and disrupted research data access and university operations.'},
 {headline:'Government plans sanctions next month',date:'2026-09-02',link:'https://example.org/plan',signal_note:'A foreign government plans to impose sanctions next month that could disrupt European research access.'}
]};
const v=P.buildPriorityView(data,{limit:50});
if(v.stats.externalShocks!==2) process.exit(2);
const families=new Set(v.externalShocks.map(x=>x.lens.shock_family));
if(!families.has('Natural disasters')) process.exit(3);
if(!families.has('Cyberattacks')) process.exit(4);
if(v.externalShocks.some(x=>x.title==='Government plans sanctions next month')) process.exit(5);
"""
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)

    def test_external_shock_taxonomy_exposes_all_supported_families(self):
        import subprocess
        js = r"""
const P=require('./priorities/priorities.js');
const text=[
 'earthquake','pandemic','armed conflict','terrorist attack','global financial crisis',
 'commodity price shock','energy supply disruption','food supply shock','export ban',
 'supply chain disruption','currency crisis','international sanctions','refugee surge',
 'cyberattack','technological disruption','extreme heat','political instability in a neighboring region',
 'foreign investment withdrawal','global demand shock','major infrastructure disruption'
].join(' | ');
const labels=new Set(P.shockFamilies(text).map(x=>x.label));
const required=['Natural disasters','Pandemics and epidemics','Armed conflicts','Terrorist attacks','Global financial crises','Commodity price shocks','Energy supply disruptions','Food supply shocks','Trade disruptions','Supply chain disruptions','Currency crises','International sanctions','Migration and refugee surges','Cyberattacks','Technological disruptions','Climate-related shocks','Political instability in neighboring regions','Sudden foreign investment withdrawal','Global demand shocks','Major infrastructure disruptions'];
for(const label of required) if(!labels.has(label)){console.error(label);process.exit(2)}
"""
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)

    def test_priority_interpretation_rejects_alarm_and_aspiration_without_required_components(self):
        import subprocess
        js = r"""
const P=require('./priorities/priorities.js');
const data={strand_a:[
 {title:'Alarm only',date:'2026-09-01',summary:'Experts warn this is a wake-up call and the stakes could not be higher.'},
 {title:'Aspiration only',date:'2026-09-01',summary:'Europe has the potential to become a global leader and must seize this unprecedented opportunity.'}
]};
const v=P.buildPriorityView(data,{limit:8});
if(v.stats.risks||v.stats.opportunities||v.stats.externalShocks) process.exit(2);
"""
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)

    def test_current_corpus_has_independent_risk_opportunity_and_shock_interpretations(self):
        import subprocess
        js = r"""
const P=require('./priorities/priorities.js');
const D=require('./radar.json');
const v=P.buildPriorityView(D,{limit:50});
if(v.stats.risks<10) process.exit(2);
if(v.stats.opportunities<10) process.exit(3);
if(v.stats.externalShocks<1) process.exit(4);
"""
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)

    def test_reader_why_line_rejects_jrc_repository_navigation_boilerplate(self):
        import subprocess
        js = r"""
const R=require('./briefing/insights.js');
const x={title:'A European research finding',strand:'A',summary:"Access to Joint Research Centre's publications.",core_message:"Access to Joint Research Centre's publications."};
const w=R.whyFor(x)||'';
if(/Joint Research Centre/i.test(w)) process.exit(2);
"""
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)

    def test_read_page_evidence_selection_does_not_use_source_quality_scores(self):
        source = (ROOT / "read" / "issues.js").read_text(encoding="utf-8")
        self.assertIn("readEvidenceScore", source)
        self.assertNotIn("RadarSourceMerit", source)
        self.assertNotIn("merit(", source)
        self.assertIn("Math.min(4,m.hits)", source)



class V17199AccumulationAndSignalTests(unittest.TestCase):
    def test_google_news_nature_redirect_keeps_configured_source_integrity(self):
        row = {
            "headline": "India launches return fellowships to lure scientists back",
            "source": "Nature",
            "source_domain": "nature.com",
            "discovery_provenance": "google_news_rss",
            "date": "2026-09-01T12:00Z",
            "link": "https://news.google.com/rss/articles/example",
        }
        self.assertTrue(scan.record_source_integrity_ok(row))
        bad = dict(row, source_domain="example.com")
        self.assertFalse(scan.record_source_integrity_ok(bad))

    def test_nature_google_news_candidate_survives_anchor_novelty_and_merge(self):
        data = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        desc = (
            "India launched return fellowships and research funding to attract scientists in AI, quantum computing, "
            "biotechnology and advanced materials, amid global competition for research talent."
        )
        row = {
            "headline": "India launches return fellowships to lure scientists back",
            "source": "Nature", "source_domain": "nature.com",
            "discovery_provenance": "google_news_rss",
            "date": "2026-09-01T12:00Z",
            "link": "https://news.google.com/rss/articles/example-nature",
            "_desc": desc,
            "_themes": scan.themes_for(desc),
            "_entities": scan.distinct_matches(desc, scan.ENTITY_TERMS + scan.GEO_ACTORS),
        }
        anchored = scan.anchor_news([row], data.get("strand_a", []), [])
        self.assertEqual(len(anchored), 1)
        novel = scan._novel_signal_rows(anchored, data.get("strand_c", []))
        self.assertEqual(len(novel), 1)
        merged = scan.merge_signal_corpus(data.get("strand_c", []), anchored, "2026-09-01T16:20Z")
        new_rows = [x for x in merged if x.get("new_this_scan")]
        self.assertEqual(len(new_rows), 1)
        self.assertEqual(new_rows[0]["source"], "Nature")
        self.assertEqual(new_rows[0]["first_seen"], "2026-09-01T16:20Z")

    def test_c_expires_60_days_from_first_seen_not_publication_date(self):
        now = scan.dt.datetime(2026, 9, 1, 12, 0, tzinfo=scan.dt.timezone.utc)
        recent_insert_old_source = {
            "headline": "Old-source-date signal inserted recently",
            "source": "Nature", "link": "https://doi.org/10.1038/example",
            "date": "2026-01-01", "first_seen": "2026-08-15T12:00Z",
        }
        expired = dict(recent_insert_old_source, headline="Expired signal", first_seen="2026-07-03T11:59Z")
        data={"strand_a":[],"strand_b":[],"strand_c":[recent_insert_old_source,expired],"frontier_evidence":[]}
        out, removed = scan.prune_public_window(data, scan.dt.date(2026,5,1), now=now)
        self.assertEqual(len(out["strand_c"]), 1)
        self.assertEqual(out["strand_c"][0]["headline"], "Old-source-date signal inserted recently")
        self.assertEqual(removed["strand_c"], 1)
        self.assertEqual(out["strand_c"][0]["retention_window_days"], 60)

    def test_ab_and_frontier_are_cumulative_regardless_of_publication_age(self):
        now = scan.dt.datetime(2026, 9, 1, 12, 0, tzinfo=scan.dt.timezone.utc)
        old_a={"title":"Older accepted A","source":"Nature","link":"https://doi.org/10.1038/olda","date":"2024-01-01","strand":"A"}
        old_b={"title":"Older accepted B","source":"Futures","link":"https://doi.org/10.1000/oldb","date":"2023-01-01","strand":"B"}
        old_f={"title":"Older frontier evidence","source":"JRC","link":"https://example.org/f","date":"2022-01-01"}
        out, removed=scan.prune_public_window({"strand_a":[old_a],"strand_b":[old_b],"strand_c":[],"frontier_evidence":[old_f]}, scan.dt.date(2026,5,1), now=now)
        self.assertEqual(len(out["strand_a"]),1)
        self.assertEqual(len(out["strand_b"]),1)
        self.assertEqual(len(out["frontier_evidence"]),1)
        self.assertEqual(removed["strand_a"],0)
        self.assertEqual(removed["strand_b"],0)
        self.assertEqual(removed["frontier_evidence"],0)

    def test_public_ui_makes_source_and_signal_what_explicit(self):
        html=(ROOT/'index.html').read_text(encoding='utf-8')
        self.assertIn('<strong>Source:</strong>', html)
        self.assertIn('<strong>What happened:</strong>', html)
        self.assertNotIn('automatic every 4 hours', html.lower())
        self.assertNotIn('60 days from first insertion', html)

    def test_historical_evidence_is_public_and_weak_signals_are_prominent(self):
        main=(ROOT/'index.html').read_text(encoding='utf-8')
        read=(ROOT/'read'/'index.html').read_text(encoding='utf-8')
        historical=(ROOT/'historical'/'index.html').read_text(encoding='utf-8')
        legacy=(ROOT/'history'/'index.html').read_text(encoding='utf-8')
        self.assertIn('href="historical/"', main)
        self.assertNotIn('href="history/"', main)
        self.assertLess(main.find('id="strand-c"'), main.find('id="strand-b"'))
        self.assertIn('Weak signals to watch', read)
        self.assertIn("fetch('historical.json?ts='+Date.now()", historical)
        self.assertIn('Evidence found before the live timeframe', historical)
        self.assertNotIn('scan_history', historical)
        self.assertNotIn('Scan-by-scan additions', historical)
        self.assertIn("location.replace('../historical/')", legacy)

    def test_nature_and_science_remain_first_class_sources(self):
        direct={x.get('name'):x for x in scan.CONFIG.get('direct_top_journal_sources',[])}
        self.assertIn('Nature', direct)
        self.assertIn('Science', direct)
        self.assertTrue(direct['Nature'].get('feed_urls'))
        self.assertTrue(direct['Science'].get('feed_urls'))

if __name__ == "__main__":
    unittest.main()

class ReaderFacingMatrixRotationTests(unittest.TestCase):
    def test_public_pages_do_not_expose_future_search_instructions(self):
        paths = [
            ROOT / "index.html",
            ROOT / "frontier" / "index.html",
            ROOT / "frontier" / "quick" / "index.html",
            ROOT / "read" / "index.html",
            ROOT / "read" / "issues.js",
        ]
        banned = (
            "search more next scan",
            "extra searching next scan",
            "more search effort later",
            "receive more search effort in later scans",
            "while the next scan builds",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8").lower()
            for phrase in banned:
                self.assertNotIn(phrase, text, f"{phrase!r} leaked into {path}")

    def test_rotation_note_is_internal_not_rendered_on_main_reader(self):
        text = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('sr.rotation_note', text)

    def test_matrix_rotation_remains_enabled_in_scanner_config(self):
        self.assertEqual(scan.CONFIG.get("matrix_balance_rotation_mode"), "recurring_every_scan")
        self.assertGreater(int(scan.CONFIG.get("frontier_gap_deepening_queries_per_wave", 0)), 0)
        self.assertGreater(int(scan.CONFIG.get("frontier_gap_deepening_max_waves", 0)), 0)


class V171913CadenceJournalAndCorpusCleanupTests(unittest.TestCase):
    def test_bare_member_states_are_not_eu_scope(self):
        title = "Green Growth and Technological Innovation in BRICS Economies"
        abstract = "The study compares Brazil, Russia, India, China and South Africa and discusses cooperation among member states."
        rel, ev = scan.eu_evidence(title, abstract, "")
        self.assertIsNone(rel)
        self.assertNotIn("member states", [str(x).lower() for x in ev])

    def test_eu_member_states_still_count_when_eu_is_explicit(self):
        rel, ev = scan.eu_evidence(
            "The Performance of EU Member States in Terms of Industry 5.0",
            "The study compares technological innovation across European Union member states.",
            "",
        )
        self.assertEqual(rel, "direct")
        self.assertTrue(ev)

    def test_fp10_requires_framework_programme_context(self):
        bad = "FP10 Dysregulated aryl hydrocarbon receptor expression in keratinocytes and immune cells"
        good = "LERU requests safeguards for dual-use research in FP10"
        self.assertFalse(scan._contextual_fp10(bad))
        self.assertTrue(scan._contextual_fp10(good))
        self.assertNotIn("fp10", [str(x).lower() for x in scan._ri_hits(bad)])
        self.assertIn("fp10", [str(x).lower() for x in scan._ri_hits(good)])

    def test_visible_old_institutional_date_blocks_stale_page(self):
        item = {
            "title": "The new generation of microscopic robots",
            "source": "European Research Council",
            "date": "2026-05-20",
            "link": "https://erc.europa.eu/projects-statistics/science-stories/new-generation-microscopic-robots",
            "type": "research/policy paper",
            "summary": "The new generation of microscopic robots 20 December 2011 Toxic spills can be devastating.",
        }
        self.assertTrue(scan._institutional_visible_old_date_conflict(item))
        self.assertFalse(scan.final_ab_candidate_worthiness(item))

    def test_short_official_landing_pages_are_not_evidence(self):
        for item in [
            {"title":"AI Watch","summary":"Discover our work Focus on News article Latest news","link":"https://ai-watch.ec.europa.eu/index_en","type":"research/policy paper"},
            {"title":"Science for policy","summary":"Latest news Publications and data Related links","link":"https://joint-research-centre.ec.europa.eu/index_en","type":"research/policy paper"},
            {"title":"Digital transformation, cybersecurity","summary":"Discover our work Latest news","link":"https://joint-research-centre.ec.europa.eu/what-we-do/scientific-portfolios/digital-transformation-cybersecurity_en","type":"research/policy paper"},
        ]:
            self.assertTrue(scan.institutional_evidence_landing_page(item), item["title"])

    def test_retired_cleanup_titles_cannot_return_from_history(self):
        item = {
            "title": "Insights into the development and key factors of five European governance innovations for forest ecosystem service provision",
            "source": "Forest Policy and Economics",
            "date": "2026-08-20",
            "link": "https://doi.org/10.1016/j.forpol.2026.103891",
            "type": "peer-reviewed article",
            "summary": "Five European governance innovations for forest ecosystem service provision.",
        }
        self.assertTrue(scan._saved_ab_high_confidence_precision_reject(item))
        self.assertFalse(scan.final_ab_candidate_worthiness(item))


    def test_loader_precision_removal_is_marked_as_explicit_cleanup(self):
        award = {
            "title": "ERC awards Proof of Concept Grants to 182 researchers",
            "authors": "European Research Council",
            "source": "European Research Council",
            "date": "2026-07-14",
            "link": "https://erc.europa.eu/news-events/news/erc-awards-proof-concept-grants-182-researchers",
            "type": "research/policy paper",
            "summary": "The ERC awards Proof of Concept grants to researchers.",
        }
        current = {
            "last_updated": "2026-09-01T20:23Z",
            "quality_profile_version": scan.QUALITY_PROFILE_VERSION,
            "inherited_corpus_audit_complete": True,
            "strand_a": [award], "strand_b": [], "strand_c": [],
        }
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "radar.json"
            path.write_text(json.dumps(current), encoding="utf-8")
            with mock.patch.object(scan, "OUT_PATH", path):
                loaded = scan.load_previous()
        self.assertEqual(loaded.get("strand_a"), [])
        self.assertEqual(scan.LOAD_SANITIZE_REMOVED.get("strand_a"), 1)
        inherited = scan.needs_inherited_corpus_audit(loaded)
        preload = sum(scan.LOAD_SANITIZE_REMOVED.get(k, 0) for k in ("strand_a", "strand_b"))
        precision = (not inherited) and (scan.needs_precision_corpus_cleanup(loaded) or preload > 0)
        self.assertTrue(precision)

    def test_news_source_domain_suffix_is_removed_from_public_claim(self):
        cleaned = scan._clean_signal_claim_source_suffix(
            "UK venture capital investment rebounds as software and biotech attract funding ft.com.",
            "Financial Times",
            "ft.com",
        )
        self.assertEqual(cleaned, "UK venture capital investment rebounds as software and biotech attract funding.")

    def test_nature_news_feed_is_a_first_class_direct_route(self):
        direct = {x.get('name'): x for x in scan.CONFIG.get('direct_top_journal_sources', [])}
        nature = direct['Nature']
        self.assertIn('https://www.nature.com/nature/articles?format=rss&type=news', nature.get('feed_urls', []))
        self.assertEqual(nature.get('hub'), 'https://www.nature.com/news')
        self.assertIn('https://www.nature.com/nature/articles', nature.get('fallback_hubs', []))
        import types, time
        entry = types.SimpleNamespace(
            title="India has an ambitious plan to lure scientists back — will it work?",
            link="https://www.nature.com/articles/d41586-026-02636-9",
            summary=("India is trying to entice researchers who moved abroad to return with generous fellowships and research funding. "
                     "Researchers will be selected from strategic fields such as artificial intelligence, quantum computing, biotechnology and advanced materials."),
            description="",
            published_parsed=time.struct_time((2026,9,1,0,0,0,1,244,-1)),
            updated_parsed=None, published="1 Sep 2026", updated="", tags=[], authors=[],
        )
        _a, c = scan._direct_journal_article_from_feed_entry(entry, nature, scan.dt.date(2026,5,1))
        self.assertIsNotNone(c)
        self.assertEqual(c.get('source'), 'Nature')

    def test_nature_news_hub_card_can_feed_same_day_talent_signal(self):
        direct = {x.get('name'): x for x in scan.CONFIG.get('direct_top_journal_sources', [])}
        nature = dict(direct['Nature'])
        nature['parse_hub_cards'] = True
        html = """<html><body><ul><li class='app-article-list-row__item'>
        <a href='/articles/d41586-026-02636-9'>India has an ambitious plan to lure scientists back — will its plan work?</a>
        <p>Initiatives to attract Indian researchers who are working abroad do not offer long-term income security, some scientists say. India launched a return programme for researchers.</p>
        <span>News | 01 Sep 2026</span>
        </li></ul></body></html>"""
        entries = scan._direct_journal_hub_entries(html, 'https://www.nature.com/news', nature, 10)
        self.assertEqual(len(entries), 1)
        _a, c = scan._direct_journal_article_from_feed_entry(entries[0], nature, scan.dt.date(2026,5,1))
        self.assertIsNotNone(c)
        self.assertIn('research talent / mobility / brain drain', c.get('_themes', []))

    def test_full_nature_feed_does_not_suppress_newer_news_hub_card(self):
        import types, time
        from unittest import mock
        direct = {x.get('name'): x for x in scan.CONFIG.get('direct_top_journal_sources', [])}
        nature = dict(direct['Nature'])
        nature['google_news_always'] = False
        nature['google_news_queries'] = []
        nature['fallback_hubs'] = []
        feed_entries = [types.SimpleNamespace(
            title=f'Unrelated Nature research item number {i}',
            link=f'https://www.nature.com/articles/example-{i}',
            summary='A basic science result without European research policy relevance.',
            description='', published_parsed=time.struct_time((2026,8,31,0,0,0,0,243,-1)),
            updated_parsed=None, published='', updated='', tags=[], authors=[]
        ) for i in range(4)]
        hub_html = """<html><body><article>
        <a href='/articles/d41586-026-02636-9'>India has an ambitious plan to lure scientists back — will its plan work?</a>
        <p>News | 01 Sep 2026 India launched a public programme to entice overseas researchers to return with research grants.</p>
        </article></body></html>"""
        class Resp:
            def __init__(self, url, text='', content=b''):
                self.status_code=200; self.url=url; self.text=text; self.content=content
                self.headers={'content-type':'text/html' if text else 'application/rss+xml'}
        def fake_get(url, **kwargs):
            if 'format=rss' in url:
                return Resp(url, content=b'<rss/>')
            if url == nature['hub']:
                return Resp(url, text=hub_html, content=hub_html.encode('utf-8'))
            return Resp(url, text='<html></html>', content=b'<html></html>')
        with mock.patch.object(scan.SESSION, 'get', side_effect=fake_get), \
             mock.patch.object(scan.feedparser, 'parse', return_value=types.SimpleNamespace(entries=feed_entries)), \
             mock.patch.dict(scan.CONFIG, {'direct_top_journal_links_per_source':4, 'direct_top_journal_pages_per_source':2}, clear=False):
            _ab, cc = scan.collect_direct_top_journals([nature], [], stage_deadline=None, execution_stats={})
        self.assertTrue(any(x.get('source') == 'Nature' and 'lure scientists back' in x.get('headline','') for x in cc))

    def test_nature_scientist_return_signal_prefers_talent_anchor_over_broad_tech_anchor(self):
        import types, time
        direct = {x.get('name'): x for x in scan.CONFIG.get('direct_top_journal_sources', [])}
        nature = direct['Nature']
        entry = types.SimpleNamespace(
            title='India has an ambitious plan to lure scientists back — will its plan work?',
            link='https://www.nature.com/articles/d41586-026-02636-9',
            summary=('India launched a public programme to entice overseas researchers to return, with research grants. '
                     'The scheme also targets artificial intelligence, quantum computing, biotechnology and advanced materials.'),
            description='', published_parsed=time.struct_time((2026,9,1,0,0,0,1,244,-1)),
            updated_parsed=None, published='', updated='', tags=[], authors=[]
        )
        _a, c = scan._direct_journal_article_from_feed_entry(entry, nature, scan.dt.date(2026,5,1))
        anchors = [
            {'title':'Europe research talent attraction and brain circulation', 'summary':'Europe competes globally to attract and retain research talent and researchers.', 'source':'Policy source', 'date':'2026-08-01', 'link':'https://example.org/talent', 'type':'research/policy paper', 'strand':'A', 'eu_relevance':'direct'},
            {'title':'The critical in critical technologies', 'summary':'Europe needs quantum, AI and biotechnology capability.', 'source':'Policy source', 'date':'2026-08-01', 'link':'https://example.org/tech', 'type':'research/policy paper', 'strand':'A', 'eu_relevance':'direct'},
        ]
        rows = scan.anchor_news([c], anchors)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['watch_theme'], 'research talent / mobility / brain drain')
        self.assertEqual(rows[0]['signal_kind'], 'research / talent')
        self.assertIn('research talent', rows[0]['anchor'].lower())

    def test_run_trigger_falls_back_to_native_github_event_name(self):
        from unittest import mock
        with mock.patch.dict(scan.os.environ, {'GITHUB_EVENT_NAME':'workflow_dispatch'}, clear=True):
            self.assertEqual(scan.run_trigger_label(), 'manual')
        with mock.patch.dict(scan.os.environ, {'GITHUB_EVENT_NAME':'schedule'}, clear=True):
            self.assertEqual(scan.run_trigger_label(), 'scheduled')

    def test_matrix_auto_cell_annotation_is_non_circular_display_metadata(self):
        rows = [[{'title':'Example A','link':'https://example.org/a','strand':'A'}]]
        placements = [{'title':'Example A','link':'https://example.org/a','cell':'knowledge-A'}]
        placed = scan.annotate_automatic_matrix_cells(rows, placements)
        self.assertEqual(placed, 1)
        self.assertEqual(rows[0][0]['matrix_auto_cell'], 'knowledge-A')
        self.assertNotIn('matrix_quadrant', rows[0][0])

    def test_next_automatic_slot_is_fixed_four_hour_schedule(self):
        after = scan.dt.datetime(2026, 9, 1, 18, 45, tzinfo=scan.dt.timezone.utc)
        nxt = scan.next_automatic_scan_slot(after)
        self.assertEqual(nxt.isoformat(), '2026-09-01T20:17:00+00:00')
        html = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.assertNotIn('id="scheduleState"', html)
        self.assertNotIn('Next automatic', html)
        stuff = (ROOT / 'stuff' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('Stuff', stuff)


class EuRelevanceScannerGateTests(unittest.TestCase):
    def test_strand_a_requires_direct_eu_scope(self):
        no_eu = scan.gate_scope(
            "Research security and semiconductor export controls",
            "The study analyses research and innovation dependencies, export controls and strategic technology competition in advanced semiconductors.",
            "", 1, source_kind="scholarly"
        )
        self.assertFalse(no_eu["a_pass"])
        self.assertIsNone(no_eu["eu_relevance"])

        with_eu = scan.gate_scope(
            "EU research security and semiconductor export controls",
            "The European Union study analyses research and innovation dependencies, export controls and strategic technology competition in advanced semiconductors.",
            "", 1, source_kind="scholarly"
        )
        self.assertEqual(with_eu["eu_relevance"], "direct")

    def test_strategic_pathways_require_eu_scope_before_classification_is_filed(self):
        foreign_only = (
            "Laboratories are dependent on a sole supplier for advanced chips. "
            "The government could restrict export licences, which would deny access to the supply line."
        )
        ok, reason = scan.strategic_pathway_scope_gate(foreign_only)
        self.assertFalse(ok)
        self.assertEqual(reason, "no_direct_or_material_europe_link")

        eu_text = (
            "European laboratories are dependent on a sole supplier for advanced chips. "
            "Access is subject to United States export licences and the government could restrict approvals, "
            "which would deny EU researchers access to the supply line."
        )
        ok, reason = scan.strategic_pathway_scope_gate(eu_text)
        self.assertTrue(ok)
        self.assertEqual(reason, "direct_european_scope")


class StrategicSignalClassificationTests(unittest.TestCase):
    def test_risk_requires_mechanism_carrier_and_asset(self):
        text = (
            "European laboratories are dependent on a sole supplier for advanced lithography components. "
            "Access is subject to United States export licences and the government could restrict approvals, "
            "which would deny access to the supply line."
        )
        out = scan.classify_strategic_source_text(text)
        self.assertEqual(out["primary"], "risk")
        self.assertTrue(any(x["type"] == "risk" for x in out["lenses"]))

    def test_alarm_without_pathway_is_not_risk(self):
        out = scan.classify_strategic_source_text(
            "Experts warn Europe is at a critical juncture and cannot afford to fall behind in quantum technology."
        )
        self.assertEqual(out["primary"], "")
        self.assertEqual(out["lenses"], [])

    def test_opportunity_requires_actionable_instrument_actor_and_gain(self):
        text = (
            "The European Commission could leverage the existing EuroHPC procurement instrument. "
            "Procurement could scale European compute capacity and strengthen research access; "
            "co-funding is available now for participating centres."
        )
        out = scan.classify_strategic_source_text(text)
        self.assertEqual(out["primary"], "opportunity")
        self.assertTrue(any(x["type"] == "opportunity" for x in out["lenses"]))

    def test_aspiration_without_instrument_is_not_opportunity(self):
        out = scan.classify_strategic_source_text(
            "Europe has the potential to become a global leader in biotechnology and must seize the opportunity."
        )
        self.assertEqual(out["primary"], "")

    def test_external_shock_requires_external_imposed_fast_effect(self):
        text = (
            "The United States imposed an export ban with immediate effect. "
            "European research centres were cut off from access to the controlled accelerators overnight."
        )
        out = scan.classify_strategic_source_text(text)
        self.assertEqual(out["primary"], "external_shock")

    def test_eu_own_policy_move_is_not_external_shock(self):
        text = (
            "The European Commission imposed new research-security conditions with immediate effect, "
            "restricting access to several EU-funded facilities."
        )
        out = scan.classify_strategic_source_text(text)
        self.assertNotEqual(out["primary"], "external_shock")

    def test_climate_action_is_trend_context_not_generic_news(self):
        text = (
            "The European Investment Bank launched a new programme funding climate adaptation research infrastructure. "
            "The investment builds laboratory resilience against extreme weather and climate change."
        )
        out = scan.classify_strategic_source_text(text)
        self.assertIn("climate_change", out["trend_context"])
        self.assertTrue(out["trend_action"])

    def test_weak_signal_drops_plan_without_pathway_or_action(self):
        self.assertFalse(scan.weak_signal_candidate_text(
            "Europe plans to become a global leader in quantum",
            "Experts warn the stakes could not be higher and the initiative is expected in the coming months."
        ))

    def test_weak_signal_keeps_proposal_when_strict_risk_pathway_is_present(self):
        title = "US proposes tighter export licensing for advanced chips"
        desc = (
            "European laboratories are dependent on a sole supplier for advanced chips. "
            "Licences require US government approval and the proposal could restrict approvals, "
            "which would deny access to the supply line."
        )
        self.assertTrue(scan.weak_signal_candidate_text(title, desc))

    def test_weak_signal_attention_budget_is_raised(self):
        self.assertGreaterEqual(scan.CONFIG.get("c_min_new_per_successful_scan", 0), 2)
        self.assertGreaterEqual(scan.CONFIG.get("max_c_per_scan", 0), 12)
        self.assertGreaterEqual(scan.CONFIG.get("weak_signal_evidence_followup_per_scan", 0), 10)
        self.assertGreaterEqual(scan.CONFIG.get("c_floor_rescue_queries_per_wave", 0), 6)
        self.assertTrue(any("climate" in q.lower() for q in scan.CONFIG.get("c_floor_rescue_queries", [])))

    def test_active_pathway_queries_cover_all_three_products(self):
        news = scan.strategic_pathway_queries("news")
        scholarly = scan.strategic_pathway_queries("scholarly")
        self.assertTrue(scan.CONFIG.get("strategic_pathway_scan_enabled"))
        self.assertGreaterEqual(len(news), 12)
        self.assertTrue(any("could restrict" in q.lower() or "subject to approval" in q.lower() for q in news))
        self.assertTrue(any("could leverage" in q.lower() or "regulatory sandbox" in q.lower() for q in news))
        self.assertTrue(any("immediate effect" in q.lower() or "cut off" in q.lower() for q in news))
        self.assertGreaterEqual(len(scholarly), 4)

    def test_active_pathway_corpus_can_file_items_without_main_radar_admission(self):
        cases = [
            {
                "title": "Cloud access risk", "source": "Reuters", "link": "https://reuters.com/risk", "date": "2026-09-02",
                "_strategic_source_text": "European universities are dependent on a United States-controlled cloud supplier for research data. The United States government could restrict access under export licensing, which would deny access to European research data.",
            },
            {
                "title": "Pilot line opportunity", "source": "Reuters", "link": "https://reuters.com/opportunity", "date": "2026-09-02",
                "_strategic_source_text": "The European Commission could leverage its existing instrument: procurement could fund a pilot line now, strengthening European semiconductor research capacity while co-funding is available.",
            },
            {
                "title": "GPU access shock", "source": "Reuters", "link": "https://reuters.com/shock", "date": "2026-09-02",
                "_strategic_source_text": "On 2 September 2026, a United States supplier cut off European research laboratories from GPU compute without prior notice, shutting down access overnight.",
            },
        ]
        rows = scan.build_strategic_pathway_corpus([], cases, [], "2026-09-02T12:00:00Z", [])
        kinds = {r["strategic_classification"]["primary"] for r in rows}
        self.assertEqual(kinds, {"risk", "opportunity", "external_shock"})
        self.assertTrue(all(r["source_quality_gate"]["admissible"] for r in rows))

    def test_strategic_source_quality_gate_is_separate_from_eu_relevance(self):
        direct={"source":"Reuters","link":"https://reuters.com/a","eu_relevance":"direct"}
        derived={"source":"Reuters","link":"https://reuters.com/b","eu_relevance":"derived"}
        self.assertEqual(scan.strategic_source_quality_gate(direct), scan.strategic_source_quality_gate(derived))
        self.assertFalse(scan.strategic_source_quality_gate({"source":"Unknown Blog","link":"https://unknown.invalid/x"})[0])

    def test_dedicated_scholarly_pathway_can_be_filed_without_ab_strand(self):
        text = (
            "European laboratories are dependent on a sole supplier for advanced semiconductors. "
            "Access is subject to United States export licences and the government could restrict approvals, "
            "which would deny European research centres access to the chips."
        )
        candidate = scan._strategic_scholarly_candidate(
            title="European semiconductor access exposure", authors="A. Researcher",
            source="Research Policy", date=scan.dt.date(2026, 9, 1),
            link="https://doi.org/10.0000/example", item_type="peer-reviewed article",
            tier_label="Tier 2", text=text,
        )
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["strand"], "strategic")
        self.assertTrue(candidate["_strategic_discovery"])
        filed = scan.strategic_pathway_record(candidate, [])
        self.assertIsNotNone(filed)
        self.assertEqual(filed["strategic_classification"]["primary"], "risk")

    def test_classifier_records_required_components_and_transition_key(self):
        text = (
            "European laboratories are dependent on a sole supplier for advanced chips. "
            "Access is subject to United States export licences and the government could restrict approvals, "
            "which would deny access to the supply line."
        )
        lens = scan.classify_strategic_source_text(text)["lenses"][0]
        self.assertEqual(set(lens["components"]), {"mechanism", "carrier", "asset"})
        self.assertTrue(all(lens["components"].values()))
        self.assertEqual(lens["transition_key"], "united_states|compute_chips|export_licensing")

    def test_external_shock_requires_discreteness_not_just_an_imposed_measure(self):
        out = scan.classify_strategic_source_text(
            "The United States imposed an export ban. European research centres were restricted from advanced chip access."
        )
        self.assertNotEqual(out["primary"], "external_shock")

    def test_newer_matching_shock_closes_older_risk(self):
        risk = {
            "title": "Conditional chip-access risk", "date": "2026-08-01",
            "strategic_classification_source": "source_text",
            "strategic_classification": scan.classify_strategic_source_text(
                "European laboratories are dependent on a sole supplier for advanced chips. "
                "Access is subject to United States export licences and the government could restrict approvals, "
                "which would deny access to the supply line."
            ),
        }
        shock = {
            "title": "Chip-access shock", "date": "2026-08-02",
            "strategic_classification_source": "source_text",
            "strategic_classification": scan.classify_strategic_source_text(
                "The United States imposed an export ban with immediate effect. "
                "European laboratories were cut off from access to advanced chips overnight."
            ),
        }
        self.assertEqual(scan.apply_strategic_risk_shock_lifecycle([[risk, shock]]), 1)
        lens = risk["strategic_classification"]["lenses"][0]
        self.assertEqual(lens["status"], "closed_into_shock")
        self.assertEqual(lens["closed_by"]["title"], "Chip-access shock")

class StrategicSignalGuardrailTests(unittest.TestCase):
    def test_opportunity_without_named_actor_fails_even_with_procurement_phrase(self):
        out = scan.classify_strategic_source_text(
            "Procurement could leverage existing capacity and strengthen European compute access; co-funding is available now."
        )
        self.assertNotEqual(out["primary"], "opportunity")

    def test_climate_action_can_be_a_weak_signal_theme_with_ri_and_strategic_stakes(self):
        text = (
            "The EU launched climate adaptation research infrastructure funding to strengthen resilience "
            "and reduce strategic dependencies in critical research facilities."
        )
        themes = set(scan.themes_for(text))
        self.assertIn("climate transition / adaptation", themes)
        self.assertTrue(scan.strong_watch_signal_text(text, themes))

    def test_routine_new_pi_profile_is_hard_excluded(self):
        title = "Meet our new PIs: Simone Parisi on intelligent exploration, autonomy, and AI awareness"
        self.assertEqual(
            scan.document_exclusion_reason(title, "Simone Parisi joined a European institute."),
            "hard exclusion: routine personnel profile",
        )
        self.assertTrue(scan._saved_ab_high_confidence_precision_reject({
            "title": title,
            "summary": "Simone Parisi joined ELLIS Institute Finland and Tampere University in April 2026.",
            "type": "institutional report",
            "date": "2026-06-05",
            "link": "https://example.org/pi",
            "source": "ELLIS Institute Finland",
        }))
