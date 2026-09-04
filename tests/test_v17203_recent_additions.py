import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RecentAdditionReaderContract(unittest.TestCase):
    def test_radar_shows_only_total_items_and_new_items_in_compact_strip(self):
        html = (ROOT / "radar" / "index.html").read_text(encoding="utf-8")
        for needle in (
            'id="itemsCount"',
            'id="newCount"',
            'id="newOnly"',
            'function productiveWindow(d,items)',
            'function newItem(x)',
            'firstSeenMs(x)',
            '>Items</span>',
            '>New</span>',
        ):
            self.assertIn(needle, html)
        for obsolete in (
            'id="papersCount"',
            'id="signalsCount"',
            'id="checkedCount"',
            'id="addedScanCount"',
            'id="added24Count"',
            'id="runtimeCount"',
            'Added last scan',
            'Added in 24h',
            'Scan runtime',
            'Records checked',
        ):
            self.assertNotIn(obsolete, html)

    def test_new_filter_uses_latest_productive_scan_and_insertion_time(self):
        html = (ROOT / "radar" / "index.html").read_text(encoding="utf-8")
        self.assertIn("d?.latest_productive_scan", html)
        self.assertIn("d?.scan_history", html)
        self.assertIn("Date.parse(x?.first_seen||'')", html)
        self.assertIn("state.newStart", html)
        self.assertIn("state.newEnd", html)
        self.assertIn("state.newOnly", html)

    def test_current_data_exposes_latest_productive_scan(self):
        data = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        self.assertIn("scan_history", data)
        self.assertIn("latest_productive_scan", data)
        latest = data["latest_productive_scan"]
        self.assertIsInstance(latest, dict)
        self.assertGreater(int(latest.get("new_items", 0) or 0), 0)
        self.assertTrue(latest.get("started_at"))
        items = data.get("strand_a", []) + data.get("strand_b", []) + data.get("strand_c", [])
        self.assertTrue(any(x.get("first_seen") for x in items))

    def test_scanner_preserves_latest_productive_scan_without_forcing_low_quality_admission(self):
        py = (ROOT / "scripts" / "scan_radar.py").read_text(encoding="utf-8")
        self.assertIn('"latest_productive_scan": latest_productive_scan', py)
        self.assertIn('for hist in reversed(scan_history):', py)
        self.assertIn('productive_n <= 0', py)
        self.assertIn('never', py.lower())
        self.assertIn('force-admits', py.lower())

    def test_read_topic_tree_connectors_keep_red_black_white_hierarchy(self):
        html = (ROOT / "read" / "index.html").read_text(encoding="utf-8")
        self.assertIn('class="root-link"', html)
        self.assertIn('class="branch-link"', html)
        self.assertIn('class="junction root-junction"', html)


if __name__ == "__main__":
    unittest.main()
