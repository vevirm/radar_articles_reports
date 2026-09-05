import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_scan_v172041", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


class _Resp:
    status_code = 200
    headers = {}
    def json(self):
        return {"results": []}


class RecallAndOpenAlexBudgetTests(unittest.TestCase):
    def test_high_confidence_horizon_europe_system_item_is_restored(self):
        ev = scan.gate_scope(
            "Japan officially joins Horizon Europe",
            "Japan has joined Horizon Europe, the European Union research and innovation framework programme, strengthening international research cooperation and access to collaborative research funding.",
            "", 2, source_kind="scholarly",
        )
        self.assertTrue(ev["a_pass"])
        self.assertEqual(ev["a_route"], "eu-ri-system-relevance")

    def test_known_generic_regional_false_positive_stays_out(self):
        ev = scan.gate_scope(
            "Regional knowledge base and firm efficiency: Evidence from start-ups and fast-growing medium-sized firms",
            "Using micro-level data across European regions, we examine production efficiency. The study evaluates how access to regional knowledge and technological capabilities influences firm performance and innovation strategies.",
            "", 2, source_kind="scholarly",
        )
        self.assertFalse(ev["a_pass"])
        self.assertNotEqual(ev.get("a_route"), "eu-ri-system-relevance")

    def test_keyless_openalex_request_cap_is_shared_across_callers(self):
        old_key = scan.OPENALEX_API_KEY
        old_count = scan.OPENALEX_KEYLESS_REQUEST_COUNT
        old_cap = scan.CONFIG.get("openalex_keyless_requests_per_scan")
        try:
            scan.OPENALEX_API_KEY = ""
            scan.OPENALEX_KEYLESS_REQUEST_COUNT = 0
            scan.CONFIG["openalex_keyless_requests_per_scan"] = 2
            with mock.patch.object(scan.SESSION, "get", return_value=_Resp()) as get:
                a = scan.openalex_get("works", params={"search": "a"})
                b = scan.openalex_get("authors", params={"search": "b"})
                c = scan.openalex_get("works", params={"search": "c"})
            self.assertEqual(a.status_code, 200)
            self.assertEqual(b.status_code, 200)
            self.assertTrue(scan._openalex_local_budget_response(c))
            self.assertEqual(get.call_count, 2)
        finally:
            scan.OPENALEX_API_KEY = old_key
            scan.OPENALEX_KEYLESS_REQUEST_COUNT = old_count
            if old_cap is None:
                scan.CONFIG.pop("openalex_keyless_requests_per_scan", None)
            else:
                scan.CONFIG["openalex_keyless_requests_per_scan"] = old_cap


if __name__ == "__main__":
    unittest.main()
