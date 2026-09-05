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

    def test_rotation_covers_topics_and_time_bands(self):
        topics = H.CONFIG["topics"]
        chosen, next_cursor = H.rotating(topics, 0, 4)
        self.assertEqual(len(chosen), 4)
        self.assertEqual(next_cursor, 4)
        bands = H.historical_time_bands()
        self.assertGreaterEqual(len(bands), 5)
        self.assertEqual(bands[0]["date_from"], H.DATE_FROM)
        self.assertEqual(bands[-1]["date_to"], H.DATE_TO)
        self.assertTrue(all((b["date_to"].year - b["date_from"].year) <= 1 for b in bands))
        picked, next_band = H.rotating(bands, 0, 1)
        self.assertEqual(len(picked), 1)
        self.assertEqual(next_band, 1 % len(bands))
        self.assertEqual(H.MAIN_RADAR_WINDOW_MONTHS, 6)
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

    def test_generic_eu_research_capacity_without_geopolitical_mechanism_is_rejected(self):
        raw = {
            "title": "Working conditions and careers of researchers in European universities",
            "abstract": "This study examines researcher careers, postdoctoral working conditions, mobility and doctoral employment across European universities. " * 4,
            "date": "2022-06-01",
            "url": "https://research-and-innovation.ec.europa.eu/example-careers-report_en",
            "venue": "European Commission",
        }
        self.assertIsNone(H.admit(raw))
        self.assertEqual(H.DIAG["reject_no_strategic_context"], 1)

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

    def test_low_yield_continuation_tracks_eight_item_search_target_without_second_job(self):
        self.assertFalse(H.CONFIG["full_rescue_run_enabled"])
        target = H.CONFIG["target_new_items_per_scan"]
        self.assertEqual(target, 8)
        self.assertEqual(H.CONFIG["low_yield_trigger_max_new_items"], target - 1)
        self.assertGreaterEqual(H.CONFIG["minimum_runtime_max_extra_waves"], 3)

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


    def test_existing_historical_evidence_is_cumulative(self):
        old = {
            "id": "legacy-accepted-row",
            "title": "A legacy accepted item whose wording would fail today's gates",
            "date": "2020-05-01",
            "url": "https://example.invalid/legacy",
            "reader_point": "Previously accepted historical evidence.",
            "source_merit_score": 40,
        }
        kept = H.refresh_existing_item(old)
        self.assertIsNotNone(kept)
        self.assertEqual(kept["id"], old["id"])
        self.assertEqual(kept["title"], old["title"])

    def test_cumulative_merge_never_shrinks_previous_archive(self):
        previous = [
            {"id": "p1", "title": "Previous one", "date": "2020-01-01", "url": "https://example.invalid/p1"},
            {"id": "p2", "title": "Previous two", "date": "2021-01-01", "url": "https://example.invalid/p2"},
        ]
        duplicate = {"id": "new-id", "title": "Previous one", "date": "2020-01-01", "url": "https://other.invalid/p1", "source_merit_score": 100}
        fresh = {"id": "p3", "title": "New three", "date": "2022-01-01", "url": "https://example.invalid/p3"}
        merged, new_count = H.cumulative_merge(previous, [], [duplicate, fresh])
        self.assertGreaterEqual(len(merged), len(previous))
        self.assertEqual(len(merged), 3)
        self.assertEqual(new_count, 1)
        self.assertTrue(all(any(x.get("id") == pid for x in merged) for pid in ("p1", "p2")))

    def test_cumulative_history_has_no_eviction_cap(self):
        self.assertTrue(H.CONFIG["cumulative_retention"])
        self.assertEqual(H.CONFIG["max_items"], 0)

    def test_deeper_result_pages_and_source_depth_are_supported(self):
        import inspect
        self.assertIn("result_page", inspect.signature(H.collect_openalex).parameters)
        self.assertIn("window_from", inspect.signature(H.collect_openalex).parameters)
        self.assertIn("window_to", inspect.signature(H.collect_crossref).parameters)
        self.assertIn("depth_page", inspect.signature(H.collect_direct_sources).parameters)
        self.assertGreaterEqual(H.CONFIG["direct_source_depth_pages"], 3)
        self.assertGreaterEqual(H.CONFIG["minimum_runtime_max_extra_waves"], 3)

    def test_direct_date_fallback_recovers_old_historical_years(self):
        self.assertEqual(H.historical_date_from_text("Published 2018-07-14"), H.dt.date(2018, 7, 14))
        self.assertEqual(H.historical_date_from_text("archive/2016/research-security-report"), H.dt.date(2016, 1, 1))

    def test_gap_cells_prefer_undercovered_topic_band_but_rotate(self):
        bands = H.historical_time_bands()
        topic_id = H.CONFIG["topics"][0]["id"]
        populated = [{"date": bands[0]["date_from"].isoformat(), "topics": [topic_id]} for _ in range(8)]
        first, cursor = H.select_gap_cells(populated, bands, 0, 2)
        second, _ = H.select_gap_cells(populated, bands, cursor, 2)
        self.assertEqual(len(first), 2)
        self.assertEqual(len(second), 2)
        self.assertNotEqual([(x[0]["id"], x[1]["id"]) for x in first], [(x[0]["id"], x[1]["id"]) for x in second])
        self.assertTrue(all(x[2] == 0 for x in first))

    def test_known_good_author_pool_is_deduplicated(self):
        rows = [
            {"authors": "Ada Lovelace; Someone Else"},
            {"authors": "Ada Lovelace; Another"},
            {"authors": "Marie Curie"},
            {"authors": ""},
        ]
        self.assertEqual(H.author_seed_pool(rows), ["Ada Lovelace", "Marie Curie"])


if __name__ == "__main__":
    unittest.main()
