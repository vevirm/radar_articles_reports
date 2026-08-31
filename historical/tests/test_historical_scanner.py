import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
HIST = ROOT / "historical"
SPEC = importlib.util.spec_from_file_location("scan_historical", HIST / "scan_historical.py")
H = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(H)


class HistoricalScannerTests(unittest.TestCase):
    def setUp(self):
        H.DIAG.clear()

    def test_year_preference_is_recent_first(self):
        self.assertGreater(H.year_bonus(H.dt.date(2026, 2, 1)), H.year_bonus(H.dt.date(2025, 6, 1)))
        self.assertGreater(H.year_bonus(H.dt.date(2025, 6, 1)), H.year_bonus(H.dt.date(2024, 6, 1)))

    def test_rotation_is_topic_not_time_slice(self):
        topics = H.CONFIG["topics"]
        chosen, next_cursor = H.rotating(topics, 0, 4)
        self.assertEqual(len(chosen), 4)
        self.assertEqual(next_cursor, 4)
        self.assertEqual(H.DATE_FROM.isoformat(), "2015-01-01")
        self.assertEqual(H.MAIN_RADAR_WINDOW_MONTHS, 6)
        self.assertEqual(H.DATE_TO, H.CUTOFF_EXCLUSIVE - H.dt.timedelta(days=1))
        self.assertEqual(H.CUTOFF_EXCLUSIVE, H.historical_cutoff_exclusive())

    def test_non_elite_source_is_rejected(self):
        raw = {
            "title": "Europe research innovation and strategic technology dependence",
            "abstract": "A long analytical report on European research and innovation, strategic autonomy, technology dependence and competition with China and the United States. " * 3,
            "date": "2025-06-01",
            "url": "https://example.com/report",
            "venue": "Unknown outlet",
        }
        self.assertIsNone(H.admit(raw))
        self.assertEqual(H.DIAG["reject_source_not_elite"], 1)

    def test_top_tier_eu_report_can_pass(self):
        raw = {
            "title": "European research and innovation capacity under strategic technology dependencies",
            "abstract": "This report analyses European research and innovation capacity, strategic autonomy, technology dependence, computing infrastructure and competition with China and the United States. " * 3,
            "date": "2025-06-01",
            "url": "https://research-and-innovation.ec.europa.eu/example-report_en",
            "venue": "European Commission",
        }
        item = H.admit(raw)
        self.assertIsNotNone(item)
        self.assertGreaterEqual(item["source_merit_score"], H.MIN_SCORE)
        self.assertTrue(item["topics"])
        self.assertEqual(H.DIAG["gate_passed"], 1)

    def test_historical_matrix_uses_plain_four_by_four_axes(self):
        row, col, basis = H.matrix_classification(
            "Europe built new computing infrastructure and increased capacity, but still relied on foreign cloud suppliers."
        )
        self.assertEqual(row, "infrastructure")
        self.assertIn(col, {"A", "C"})
        self.assertIn("Source evidence:", basis)


    def test_topic_matching_does_not_treat_ai_as_substring(self):
        self.assertNotIn("ai-compute", H.topic_matches("European researchers study brain metastasis and cancer treatment."))
        self.assertIn("ai-compute", H.topic_matches("European researchers use AI compute for science."))

    def test_matrix_does_not_force_generic_europe_china_mentions_into_cell(self):
        row, col, basis = H.matrix_classification(
            "European researchers compare scientific publication patterns in China and the United States."
        )
        self.assertEqual((row, col, basis), ("", "", ""))

    def test_matrix_requires_directional_evidence(self):
        row, col, basis = H.matrix_classification(
            "Europe experienced brain drain as researchers left for the United States, weakening the European research workforce."
        )
        self.assertEqual(row, "knowledge")
        self.assertEqual(col, "D")
        self.assertIn("brain drain", basis.lower())

    def test_curated_workbook_seed_queue_is_loaded(self):
        seeds = H.curated_seed_items()
        self.assertGreaterEqual(len(seeds), 190)
        self.assertTrue(any("Choose Europe" in str(x.get("title")) for x in seeds))
        self.assertTrue(any(int(x.get("year", 0) or 0) <= 2022 for x in seeds))

    def test_manual_geopolitical_layer_is_persistent_and_people_heavy(self):
        items = H.manual_evidence_items()
        self.assertEqual(len(items), 21)
        self.assertGreaterEqual(sum(1 for x in items if x.get("matrix_dimension") == "knowledge"), 16)
        self.assertTrue(any(x.get("date") == "2026-02-03" for x in items))
        self.assertTrue(all(x.get("manual_curated") for x in items))

    def test_administrative_documents_are_rejected_before_topic_gates(self):
        raw = {
            "title": "JRC privacy statement",
            "abstract": "European research innovation strategic autonomy and AI policy report. " * 3,
            "date": "2025-06-01",
            "url": "https://publications.jrc.ec.europa.eu/privacy.pdf",
            "venue": "JRC Publications Repository",
        }
        self.assertIsNone(H.admit(raw))
        self.assertEqual(H.DIAG["reject_administrative_document"], 1)

    def test_main_radar_paths_are_not_outputs(self):
        self.assertEqual(H.OUT_PATH, ROOT / "historical" / "historical.json")
        self.assertNotEqual(H.OUT_PATH, ROOT / "radar.json")

    def test_metadata_rescue_prioritizes_strong_eu_ri_title(self):
        src = H.source_for("research-and-innovation.ec.europa.eu")
        strong = H.metadata_rescue_priority(
            "European research security and strategic technology dependence report",
            "EU research security technology",
            src,
            H.dt.date(2025, 5, 1),
        )
        weak = H.metadata_rescue_priority("A study of materials", "materials", None, H.dt.date(2023, 5, 1))
        self.assertGreater(strong, weak)
        self.assertGreaterEqual(strong, H.CONFIG["metadata_rescue_priority_min_score"])

    def test_crossref_uses_title_mode(self):
        self.assertEqual(H.CONFIG["crossref_relevance_query_mode"], "title")

    def test_source_specific_adapters_exist_for_hard_eu_sources(self):
        adapters = H.CONFIG["source_adapters"]
        for domain in ("research-and-innovation.ec.europa.eu", "op.europa.eu", "europarl.europa.eu", "consilium.europa.eu", "bruegel.org"):
            self.assertIn(domain, adapters)
            self.assertTrue(adapters[domain])

    def test_low_yield_rescue_tracks_eight_item_search_target(self):
        self.assertTrue(H.CONFIG["full_rescue_run_enabled"])
        target = H.CONFIG["target_new_items_per_scan"]
        self.assertEqual(target, 8)
        self.assertEqual(H.CONFIG["full_rescue_run_trigger_max_new_items"], target - 1)
        self.assertEqual(H.CONFIG["low_yield_trigger_max_new_items"], target - 1)

    def test_rejection_funnel_exposes_main_stages(self):
        H.DIAG.update({"raw_records": 12, "source_eligible": 9, "enough_text": 8, "eu_scope": 7, "ri_scope": 6, "strategic_scope": 5, "topic_match": 4, "gate_passed": 3})
        f = H.rejection_funnel(2, 3)
        self.assertEqual(f["raw_records"], 12)
        self.assertEqual(f["genuinely_new_items"], 2)
        self.assertIn("metadata_text_rescue", f)
        self.assertIn("source_adapter_jobs", f)

    def test_historical_scan_is_target_driven_not_time_padded(self):
        # Scanner behavior must not depend on the GitHub workflow text. Workflow
        # cadence is checked separately as a non-blocking deployment contract.
        self.assertEqual(H.CONFIG["minimum_runtime_seconds"], 0)
        self.assertEqual(H.MIN_RUNTIME_SECONDS, 0)
        self.assertEqual(H.CONFIG["target_new_items_per_scan"], 8)

    def test_deeper_result_pages_are_supported_for_minimum_runtime_rotation(self):
        import inspect
        self.assertIn("result_page", inspect.signature(H.collect_openalex).parameters)
        self.assertIn("result_page", inspect.signature(H.collect_crossref).parameters)
        self.assertGreaterEqual(H.CONFIG["minimum_runtime_max_extra_waves"], 3)


if __name__ == "__main__":
    unittest.main()
