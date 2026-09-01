import importlib.util
import json
import os
import sys
import time
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
        self.assertGreaterEqual(scan.CONFIG.get("source_failure_reallocation_institution_sources", 0), 8)
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
        self.assertIn("v17.17.5", scan.SIGNAL_QUALITY_PROFILE_VERSION)
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


class FrontierBridgeTests(unittest.TestCase):
    def test_frontier_bridge_exposes_placements(self):
        data = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        counts, qualifying, placements, error = scan.frontier_matrix_snapshot(data)
        self.assertEqual(error, "")
        self.assertIsInstance(counts, dict)
        self.assertIsInstance(placements, list)
        self.assertEqual(qualifying, len(placements))
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

    def test_priorities_quality_is_material_not_tiny_tiebreak(self):
        import subprocess
        js = "const P=require('./priorities/priorities.js'); const hi={overall:10,sourceMerit:{score:100},confidence:70,materiality:3}; const lo={overall:10,sourceMerit:{score:65},confidence:70,materiality:3}; if(P.structuralScore(hi)-P.structuralScore(lo)<30) process.exit(2);"
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

    def test_read_page_evidence_selection_is_quality_aware(self):
        source = (ROOT / "read" / "issues.js").read_text(encoding="utf-8")
        self.assertIn("readEvidenceScore", source)
        self.assertIn("merit(m.x)+Math.min(4,m.hits)*12", source)
        self.assertIn(".35+.65*(merit(x)/100)", source)


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
