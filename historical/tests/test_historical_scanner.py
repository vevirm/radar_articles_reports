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
        self.assertGreater(H.year_bonus(H.dt.date(2025, 6, 1)), H.year_bonus(H.dt.date(2024, 6, 1)))
        self.assertGreater(H.year_bonus(H.dt.date(2024, 6, 1)), H.year_bonus(H.dt.date(2023, 6, 1)))

    def test_rotation_is_topic_not_time_slice(self):
        topics = H.CONFIG["topics"]
        chosen, next_cursor = H.rotating(topics, 0, 4)
        self.assertEqual(len(chosen), 4)
        self.assertEqual(next_cursor, 4)
        self.assertEqual(H.DATE_FROM.isoformat(), "2023-01-01")
        self.assertEqual(H.DATE_TO.isoformat(), "2025-12-31")

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
        self.assertIn("source concerns", basis)

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

    def test_low_yield_has_one_full_rescue_rule(self):
        self.assertTrue(H.CONFIG["full_rescue_run_enabled"])
        self.assertEqual(H.CONFIG["full_rescue_run_trigger_max_new_items"], 3)
        self.assertEqual(H.CONFIG["low_yield_trigger_max_new_items"], 3)

    def test_rejection_funnel_exposes_main_stages(self):
        H.DIAG.update({"raw_records": 12, "source_eligible": 9, "enough_text": 8, "eu_scope": 7, "ri_scope": 6, "strategic_scope": 5, "topic_match": 4, "gate_passed": 3})
        f = H.rejection_funnel(2, 3)
        self.assertEqual(f["raw_records"], 12)
        self.assertEqual(f["genuinely_new_items"], 2)
        self.assertIn("metadata_text_rescue", f)
        self.assertIn("source_adapter_jobs", f)

    def test_workflow_dispatches_only_historical_scanner(self):
        workflow = (ROOT / ".github" / "workflows" / "historical-scan.yml").read_text(encoding="utf-8")
        self.assertIn("historical-scan.yml/dispatches", workflow)
        self.assertNotIn("radar-scan.yml/dispatches", workflow)
        self.assertIn("git add -- historical/historical.json", workflow)
        self.assertNotIn("git add -- radar.json", workflow)

    def test_historical_scan_has_ten_minute_minimum_runtime(self):
        self.assertEqual(H.CONFIG["minimum_runtime_seconds"], 600)
        self.assertEqual(H.MIN_RUNTIME_SECONDS, 600)
        workflow = (ROOT / ".github" / "workflows" / "historical-scan.yml").read_text(encoding="utf-8")
        self.assertIn("HISTORICAL_MIN_RUNTIME_SECONDS: '600'", workflow)

    def test_deeper_result_pages_are_supported_for_minimum_runtime_rotation(self):
        import inspect
        self.assertIn("result_page", inspect.signature(H.collect_openalex).parameters)
        self.assertIn("result_page", inspect.signature(H.collect_crossref).parameters)
        self.assertGreaterEqual(H.CONFIG["minimum_runtime_max_extra_waves"], 3)


if __name__ == "__main__":
    unittest.main()
