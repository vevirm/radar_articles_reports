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


if __name__ == "__main__":
    unittest.main()
