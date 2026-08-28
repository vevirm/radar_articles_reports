import unittest
import sys, types
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
try:
    import feedparser  # noqa: F401
except ModuleNotFoundError:
    sys.modules["feedparser"] = types.ModuleType("feedparser")

import scripts.scan_radar as scanner
from scripts.scan_radar import gate_scope, make_finding, backfill_finding, build_findings_data


class FindingsTests(unittest.TestCase):
    def test_strand_a_finding_prefers_substantive_bridge(self):
        title = "Research security and European scientific cooperation"
        abstract = (
            "European Union research and innovation policy is increasingly linking research security "
            "to geopolitical competition and de-risking in international scientific cooperation. "
            "The paper discusses implementation choices for Horizon Europe and member states."
        )
        ev = gate_scope(title, abstract, "", 2)
        self.assertTrue(ev["a_pass"])
        finding = make_finding(f"{title}. {abstract}", ev, "A", title)
        self.assertIn("research security", finding.lower())
        self.assertNotIn("automated admission gate", finding.lower())
        self.assertTrue(finding.endswith((".", "!", "?", "…")))

    def test_legacy_summary_backfill_avoids_gate_sentence(self):
        item = {
            "title": "Legacy source",
            "summary": (
                "Research security is reshaping international scientific cooperation in Europe. "
                "The automated admission gate found R&I: research security; geopolitics: de-risk. "
                "Its EU relevance is classified as direct."
            ),
        }
        finding = backfill_finding(item)
        self.assertTrue(finding.startswith("Research security"))
        self.assertNotIn("automated", finding.lower())

    def test_pending_upgrade_recovers_previous_committed_corpus(self):
        current_path = scanner.OUT_PATH
        previous = {
            "last_updated": "2026-08-17T09:00Z",
            "first_scan_complete": True,
            "strand_a": [{"title": "Existing paper"}],
            "strand_b": [],
        }
        with tempfile.TemporaryDirectory() as td:
            pending = Path(td) / "radar.json"
            pending.write_text(json.dumps({
                "last_updated": None,
                "first_scan_complete": False,
                "strand_a": [],
                "strand_b": [],
            }))
            scanner.OUT_PATH = pending
            fake = type("Proc", (), {"stdout": json.dumps(previous)})()
            try:
                with patch.object(scanner.subprocess, "run", return_value=fake):
                    loaded = scanner.load_previous()
            finally:
                scanner.OUT_PATH = current_path
        self.assertTrue(loaded["first_scan_complete"])
        self.assertEqual(loaded["strand_a"][0]["title"], "Existing paper")

    def test_findings_dataset_contains_theme_digest_and_signal(self):
        a = [{
            "title": "Research security in Europe",
            "date": "2026-08-01",
            "source": "Example Journal",
            "authors": "A. Author",
            "link": "https://example.org/a",
            "type": "journal article",
            "strand": "A",
            "eu_relevance": "direct",
            "source_tier": "Tier 2",
            "summary": "Research security is becoming central to European research policy under geopolitical competition.",
            "finding": "Research security is becoming central to European research policy under geopolitical competition.",
            "new_this_scan": True,
        }]
        c = [{
            "headline": "EU expands research-security screening",
            "date": "2026-08-18T08:00Z",
            "source": "Example News",
            "link": "https://example.org/c",
            "signal_type": "accelerates",
            "anchor": "Research security in Europe (Strand A)",
            "signal_note": "The EU expanded research-security screening for sensitive cooperation. This accelerates the anchor.",
        }]
        out = build_findings_data(a, [], c, "2026-08-18T09:00Z", "ok", True)
        self.assertEqual(out["counts"]["unique_ab_publications"], 1)
        self.assertEqual(len(out["weak_signals"]), 1)
        self.assertTrue(any(x["theme"] == "research security / foreign interference" for x in out["emerging_picture"]))


if __name__ == "__main__":
    unittest.main()
