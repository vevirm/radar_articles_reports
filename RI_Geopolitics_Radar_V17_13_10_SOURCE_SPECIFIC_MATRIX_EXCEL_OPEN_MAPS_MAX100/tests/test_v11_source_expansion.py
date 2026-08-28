import datetime as dt
import unittest

from scripts import scan_radar as s


class V11SourceExpansionTests(unittest.TestCase):
    def test_first_v11_scan_uses_four_calendar_months(self):
        today = dt.date(2026, 8, 20)
        from_date, bootstrap = s.scan_from_date({}, today)
        self.assertTrue(bootstrap)
        self.assertEqual(from_date, dt.date(2026, 4, 20))

    def test_upgrade_without_v11_marker_forces_backfill(self):
        today = dt.date(2026, 8, 20)
        previous = {"last_updated": "2026-08-19T20:00Z", "source_expansion_version": "v10"}
        from_date, bootstrap = s.scan_from_date(previous, today)
        self.assertTrue(bootstrap)
        self.assertEqual(from_date, dt.date(2026, 4, 20))

    def test_second_v11_scan_uses_overlap_not_four_months(self):
        today = dt.date(2026, 8, 20)
        previous = {
            "last_updated": "2026-08-20T01:00Z",
            "source_expansion_version": s.SOURCE_EXPANSION_VERSION,
        }
        old_floor = s.DATE_FLOOR
        try:
            s.DATE_FLOOR = dt.date(2026, 4, 20)
            from_date, bootstrap = s.scan_from_date(previous, today)
        finally:
            s.DATE_FLOOR = old_floor
        self.assertFalse(bootstrap)
        self.assertEqual(from_date, dt.date(2026, 8, 6))

    def test_broad_journal_article_is_eligible_for_quality_gate(self):
        work = {
            "type": "article",
            "primary_location": {"source": {"display_name": "A Relevant Specialist Journal", "type": "journal"}},
            "locations": [],
        }
        ok, tier, rank, source, label = s.quality_from_openalex(work)
        self.assertTrue(ok)
        self.assertEqual(tier, 2)
        self.assertIn("broad", label.lower())


if __name__ == "__main__":
    unittest.main()
