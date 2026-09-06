"""Compatibility replacement for the obsolete v17.20.47 fresh-start test.

The live GitHub repository can retain files that a later browser-uploaded ZIP no longer
contains.  The old version of this test asserted a destructive one-time 200-item reset
API that was deliberately superseded by v17.20.50's active-core + archive model.  Keep
this filename in every release so browser uploads overwrite the stale copy, while still
protecting the original intent: compact active corpus, complete dedupe memory,
incremental discovery and DOI-first OpenAlex snowballing.
"""
from __future__ import annotations
import datetime as dt
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_PATH = ROOT / "scripts" / "scan_radar.py"
spec = importlib.util.spec_from_file_location("radar_scan_v172047_compat", SCAN_PATH)
scan = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)


def _paper(i: int):
    return {
        "title": f"European research policy evidence paper {i}",
        "date": "2026-09-01",
        "link": f"https://doi.org/10.1234/paper-{i}",
        "type": "peer-reviewed article",
        "source_tier": "Tier 2",
        "eu_relevance": "direct",
        "strand": "A",
        "summary": "European research and innovation policy evidence.",
    }


class CurrentFreshStartContract(unittest.TestCase):
    def test_packaged_radar_is_compact_but_history_is_preserved(self):
        radar = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        active = len(radar.get("strand_a", [])) + len(radar.get("strand_b", []))
        archive = radar.get("ab_archive", [])
        self.assertEqual(active, 200)
        self.assertIsInstance(archive, list)
        self.assertGreater(len(archive), 0)
        self.assertEqual(active + len(archive), radar.get("active_core_stats", {}).get("accepted_history_total"))

    def test_archived_items_remain_in_dedupe_memory(self):
        item = _paper(999)
        previous = {"strand_a": [], "strand_b": [], "strand_c": [], "ab_archive": [item]}
        identities, links, _signals, doi_titles = scan.known_sets_from_previous(previous)
        self.assertIn(scan.stable_item_identity(item["title"], item["link"]), identities)
        self.assertIn(scan.normalized_link(item["link"]), links)
        self.assertIn("title:" + scan.norm_title(item["title"]), doi_titles)

    def test_snowball_pool_is_doi_first_and_has_twenty_slots(self):
        rows = [_paper(i) for i in range(30)]
        rows += [{
            "title": f"EU institutional announcement {i}",
            "date": "2026-09-05",
            "link": f"https://example.eu/news/{i}",
            "type": "official notice",
            "source_tier": "Tier 1",
            "eu_relevance": "direct",
            "strand": "A",
        } for i in range(25)]
        old_floor = scan.DATE_FLOOR
        scan.DATE_FLOOR = dt.date(2026, 5, 1)
        try:
            seeds = scan._snowball_seed_pool({"strand_a": rows}, [], None)
        finally:
            scan.DATE_FLOOR = old_floor
        self.assertEqual(len(seeds), 20)
        self.assertTrue(all(scan._snowball_seed_doi(x) for x in seeds))
        self.assertFalse(any("announcement" in x["title"].lower() for x in seeds))

    def test_normal_discovery_is_incremental_not_four_month_reset(self):
        previous = {
            "last_updated": "2026-09-05T12:00:00Z",
            "source_expansion_version": "older-marker",
            "scan_state": {"version": scan.INCREMENTAL_STATE_VERSION},
        }
        self.assertFalse(scan.CONFIG.get("force_backfill_on_source_expansion"))
        self.assertFalse(scan.needs_source_expansion_backfill(previous))
        floor, bootstrap = scan.scan_from_date(previous, dt.date(2026, 9, 6))
        self.assertFalse(bootstrap)
        self.assertGreaterEqual(floor, dt.date(2026, 8, 20))


if __name__ == "__main__":
    unittest.main()
