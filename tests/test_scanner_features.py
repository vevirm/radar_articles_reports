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

    def test_signal_quality_version_triggers_new_c_cleanup(self):
        self.assertIn("v17.17.3", scan.SIGNAL_QUALITY_PROFILE_VERSION)
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
        self.assertEqual(funnel["substantive_ri_remaining"], 20)
        self.assertEqual(funnel["strategic_context_remaining"], 15)
        self.assertEqual(funnel["genuinely_new_unique_ab"], 3)
        self.assertEqual(funnel["metadata_text_rescue"]["admitted_after_recovery"], 1)

    def test_workflow_has_exactly_one_full_rescue_dispatch_guard(self):
        text = (ROOT / ".github" / "workflows" / "radar-scan.yml").read_text(encoding="utf-8")
        self.assertIn("rescue_mode:", text)
        self.assertIn("actions: write", text)
        self.assertIn("full low-yield rescue run", text.lower())
        self.assertIn('/actions/workflows/radar-scan.yml/dispatches', text)
        self.assertIn("not already_rescue", text)



class CuratorCandidateQueueTests(unittest.TestCase):
    def test_round_xiv_queue_covers_all_groups_and_companions(self):
        doc = json.loads((ROOT / "curator_candidate_tests.json").read_text(encoding="utf-8"))
        rows = doc["candidates"]
        self.assertEqual(doc["group_count"], 17)
        self.assertEqual(doc["work_count"], 26)
        self.assertEqual(len(rows), 26)
        self.assertEqual(len({x["candidate_id"] for x in rows}), 26)
        self.assertEqual(
            {x["group_id"] for x in rows},
            {"K42", "K43", "K44", "I58", "I59", "I60", "C50", "C51", "C52", "C53", "R56", "R57", "R58", "R59", "R60", "R61", "W25"},
        )
        # Curator row hints are audit/discovery metadata only; they must never be
        # pre-written as authoritative matrix classification fields.
        for row in rows:
            self.assertNotIn("matrix_dimension", row)
            self.assertNotIn("matrix_quadrant", row)
            self.assertNotIn("quadrant_implied", row)
            self.assertNotIn("matrix_classification_source", row)

    def test_candidate_lane_tags_but_does_not_force_matrix(self):
        fake_crossref = {
            "title": ["Academic Craftsmanship: Reclaiming Values, Practices, and Sovereignty in the University"],
            "DOI": "10.1007/s11024-026-09654-x",
            "published": {"date-parts": [[2026, 7, 1]]},
            "type": "journal-article",
            "container-title": ["Minerva"],
            "publisher": "Springer",
            "abstract": "source text",
        }
        fake_candidate = {
            "title": fake_crossref["title"][0],
            "authors": "Example Author",
            "source": "Minerva",
            "date": "2026-07-01",
            "link": "https://doi.org/10.1007/s11024-026-09654-x",
            "type": "peer-reviewed article",
            "strand": "A",
            "eu_relevance": "direct",
            "summary": "Source-derived summary.",
            "source_tier": "Tier 2 broad journal",
        }
        original_limit = scan.CONFIG.get("curator_candidate_tests_per_scan")
        scan.CONFIG["curator_candidate_tests_per_scan"] = 1
        try:
            with mock.patch.object(scan, "_curator_candidate_known", return_value=False), \
                 mock.patch.object(scan, "_curator_crossref_lookup", return_value=(fake_crossref, "crossref_doi")), \
                 mock.patch.object(scan, "candidate_from_crossref", return_value=fake_candidate), \
                 mock.patch.object(scan, "_curator_crossref_gate_status", return_value=("passed_gate", {"resolved_title": fake_candidate["title"]})), \
                 mock.patch.object(scan, "highest_source_merit", return_value=False):
                admitted, state = scan.collect_curator_candidate_tests({}, [], time.monotonic() + 30, {})
        finally:
            scan.CONFIG["curator_candidate_tests_per_scan"] = original_limit
        self.assertEqual(len(admitted), 1)
        self.assertEqual(state["admitted_candidates_this_scan"], 1)
        item = admitted[0]
        self.assertEqual(item["discovery_provenance"], "curator_candidate_test")
        self.assertEqual(item["curator_candidate_test"]["candidate_id"], "K42")
        self.assertNotIn("matrix_dimension", item)
        self.assertNotIn("matrix_quadrant", item)
        self.assertNotIn("quadrant_implied", item)

    def test_matrix_placement_is_read_back_from_browser_classifier_output(self):
        state = {
            "results": [{
                "candidate_id": "K42",
                "title": "Academic Craftsmanship: Reclaiming Values, Practices, and Sovereignty in the University",
                "resolved_link": "https://doi.org/10.1007/s11024-026-09654-x",
            }]
        }
        placements = [{
            "title": "Academic Craftsmanship: Reclaiming Values, Practices, and Sovereignty in the University",
            "link": "https://doi.org/10.1007/s11024-026-09654-x",
            "cell": "knowledge-B",
            "row": "knowledge",
            "column": "B",
        }]
        published = {"strand_a": [{"title": state["results"][0]["title"], "strand": "A"}], "strand_b": [], "frontier_evidence": []}
        out = scan.apply_curator_matrix_placements(state, placements, published)
        self.assertTrue(out["results"][0]["matrix_placed"])
        self.assertEqual(out["results"][0]["matrix_cell"], "knowledge-B")
        self.assertEqual(out["matrix_placed"], 1)


class OpenAlexAndSnowballTests(unittest.TestCase):
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

    def test_source_family_rotation_has_eu_and_journal_first_class_lanes(self):
        self.assertTrue(scan.CONFIG.get("source_family_parallel_scan"))
        self.assertGreater(scan.CONFIG.get("official_eu_priority_sources_per_scan", 0), 0)
        self.assertGreater(scan.CONFIG.get("crossref_source_first_journals_per_scan", 0), 0)
        source = SCAN_PATH.read_text(encoding="utf-8")
        self.assertIn("ThreadPoolExecutor(max_workers=4)", source)
        self.assertIn("fut_inst = ex.submit(", source)
        self.assertIn('safe_stage, "institutional reports", collect_institutions', source)

    def test_frontier_quality_order_uses_same_source_merit_score(self):
        import subprocess
        js = "const F=require('./frontier/frontier.js'); const hi={overall:10,sourceMerit:{score:100}}; const lo={overall:10,sourceMerit:{score:65}}; if(!(F.qualityAwareScore(hi)>F.qualityAwareScore(lo))) process.exit(2);"
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)

    def test_priorities_quality_is_material_not_tiny_tiebreak(self):
        import subprocess
        js = "const P=require('./priorities/priorities.js'); const hi={overall:10,sourceMerit:{score:100},confidence:70,materiality:3}; const lo={overall:10,sourceMerit:{score:65},confidence:70,materiality:3}; if(P.structuralScore(hi)-P.structuralScore(lo)<30) process.exit(2);"
        subprocess.run(["node", "-e", js], cwd=ROOT, check=True, timeout=20)

    def test_read_page_evidence_selection_is_quality_aware(self):
        source = (ROOT / "read" / "issues.js").read_text(encoding="utf-8")
        self.assertIn("readEvidenceScore", source)
        self.assertIn("merit(m.x)+Math.min(4,m.hits)*12", source)
        self.assertIn(".35+.65*(merit(x)/100)", source)


if __name__ == "__main__":
    unittest.main()
