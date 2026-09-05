import importlib.util
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_scan_v172046", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}
        self.headers = {}

    def json(self):
        return self._data


def inverted(text: str):
    out = {}
    for pos, word in enumerate(text.split()):
        out.setdefault(word, []).append(pos)
    return out


class MetadataResilienceTests(unittest.TestCase):
    def test_source_health_never_authorises_yield_pruning(self):
        self.assertTrue(scan.source_health_is_diagnostic_only())
        self.assertFalse(scan.CONFIG.get("source_yield_pruning_enabled"))
        self.assertIn("Never disable", scan.CONFIG.get("source_yield_policy", ""))

    def test_core_policy_journals_remain_configured_independent_of_yield(self):
        configured = set(scan.CONFIG.get("crossref_priority_journals", [])) | set(scan.CONFIG.get("tier2_journals", []))
        for journal in (
            "Research Policy",
            "Technological Forecasting and Social Change",
            "Futures",
            "Technology in Society",
        ):
            with self.subTest(journal=journal):
                self.assertIn(journal, configured)

    def test_authenticated_openalex_can_enrich_crossref_doi(self):
        abstract = (
            "The European Union Horizon Europe research and innovation system strengthens deep tech scale-up, "
            "research infrastructures and scientific capabilities while reducing strategic dependencies and "
            "improving European competitiveness and economic security."
        )

        def fake_get(url, *args, **kwargs):
            self.assertIn("api.openalex.org/works", url)
            return FakeResponse(200, {"results": [{"abstract_inverted_index": inverted(abstract)}]})

        with mock.patch.object(scan, "OPENALEX_API_KEY", "test-key"), mock.patch.object(scan.SESSION, "get", side_effect=fake_get):
            text = scan.openalex_abstract_by_doi("10.1234/example", 3)
        self.assertIn("Horizon Europe", text)
        self.assertGreaterEqual(len(text.split()), 20)

    def test_metadata_sparse_research_policy_batch_is_rescued_not_misread_as_zero_quality(self):
        abstract = (
            "The European Union Horizon Europe research and innovation system strengthens deep tech scale-up, "
            "research infrastructures, scientific capabilities and technology transfer while reducing strategic "
            "dependencies and improving European competitiveness and economic security."
        )
        works = []
        for i in range(8):
            works.append({
                "DOI": f"10.1234/metadata-{i}",
                "title": [f"European Horizon Europe deep tech capability report {i}"],
                "container-title": ["Research Policy"],
                "publisher": "Elsevier BV",
                "published": {"date-parts": [[2026, 9, 1]]},
                "type": "journal-article",
                "URL": f"https://doi.org/10.1234/metadata-{i}",
            })

        def fake_get(url, *args, **kwargs):
            if "api.crossref.org/works" in url:
                return FakeResponse(200, {"message": {"items": works}})
            if "api.openalex.org/works" in url:
                return FakeResponse(200, {"results": [{"abstract_inverted_index": inverted(abstract)}]})
            raise AssertionError(f"unexpected URL: {url}")

        stats = {}
        warnings = []
        with (
            mock.patch.object(scan, "OPENALEX_API_KEY", "test-key"),
            mock.patch.object(scan.SESSION, "get", side_effect=fake_get),
            mock.patch.dict(scan.CONFIG, {
                "crossref_public_min_interval_seconds": 0,
                "scholarly_public_retries": 0,
                "metadata_sparse_source_min_records": 8,
                "metadata_sparse_source_max_abstract_coverage": 0.15,
                "metadata_sparse_openalex_enrichment_per_journal": 8,
                "metadata_sparse_openalex_enrichment_per_scan": 32,
            }, clear=False),
        ):
            out = scan.collect_crossref(
                scan.dt.date(2026, 5, 1),
                warnings,
                queries_override=[],
                priority_tasks_override=[],
                source_sweep_journals_override=["Research Policy"],
                stage_deadline=time.monotonic() + 20,
                execution_stats=stats,
            )

        health = stats["source_metadata_health"]["Research Policy"]
        self.assertEqual(health["records_seen"], 8)
        self.assertEqual(health["crossref_abstract_present"], 0)
        self.assertEqual(health["crossref_abstract_missing"], 8)
        self.assertTrue(health["metadata_sparse_detected"])
        self.assertEqual(health["openalex_doi_enrichment_attempted"], 8)
        self.assertEqual(health["openalex_doi_enrichment_recovered"], 8)
        self.assertEqual(health["judgeable_after_enrichment"], 8)
        self.assertTrue(health["health_is_diagnostic_only"])
        self.assertGreater(len(out), 0)
        self.assertFalse(warnings)


if __name__ == "__main__":
    unittest.main()
