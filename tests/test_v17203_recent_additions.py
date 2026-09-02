import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RecentAdditionReaderContract(unittest.TestCase):
    def test_radar_exposes_scan_counts_and_pressable_addition_filters(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        for needle in (
            'id="papersCount"',
            'id="signalsCount"',
            'id="checkedCount"',
            'id="addedScanCount"',
            'id="added24Count"',
            'id="runtimeCount"',
            'id="addedLastScan"',
            'id="added24h"',
            "function addedLastScan(x)",
            "function added24h(x)",
            "firstSeenMs(x)",
            "Added last scan",
            "Added 24h",
        ):
            self.assertIn(needle, html)

    def test_recent_filter_uses_insertion_time_not_publication_date(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("Date.parse(x?.first_seen||'')", html)
        self.assertIn("state.added24Floor=state.lastUpdated-24*86400000", html)
        self.assertIn("seen>=state.runStart", html)

    def test_current_data_has_fields_needed_for_transparent_counts(self):
        data = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        self.assertIn("run_started_at", data)
        self.assertIn("run_completed_at", data)
        self.assertIn("last_updated", data)
        self.assertIn("scan_results", data)
        self.assertIn("stats", data)
        self.assertIn("runtime_seconds", data["stats"])
        self.assertIn("rejection_funnel", data["scan_results"])
        self.assertIn("raw_records_seen", data["scan_results"]["rejection_funnel"])
        items = data.get("strand_a", []) + data.get("strand_b", []) + data.get("strand_c", [])
        self.assertTrue(any(x.get("first_seen") for x in items))

    def test_read_topic_tree_connectors_keep_red_black_white_hierarchy(self):
        html = (ROOT / "read" / "index.html").read_text(encoding="utf-8")
        self.assertIn('class="root-link"', html)
        self.assertIn('class="branch-link"', html)
        self.assertIn('class="junction root-junction"', html)


if __name__ == "__main__":
    unittest.main()
