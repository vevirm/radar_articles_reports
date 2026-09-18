from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import import_reader_language_results as imp  # noqa: E402
import reader_language_common as common  # noqa: E402


class ReaderLanguageRoundTripTests(unittest.TestCase):
    def test_script_prose_is_collected_again(self):
        store = {}
        common.collect_js(store)
        self.assertTrue(store, "JS prose collection must find reader-facing strings")
        self.assertTrue(all(not common.CODEISH.search(c.source) for c in store.values()))

    def test_js_string_decoding(self):
        self.assertEqual(common._decode_js_string(r"It\'s a \u2014 test\nline"), "It's a \u2014 test line")

    def test_negation_rule_blocks_flips_but_allows_rephrasing(self):
        src = "The sources do not establish an outcome measure, so the gap is open rather than proof that no metric exists."
        imp.validate_rewrite(src, "The sources show no outcome measure yet; the gap is open, not proof that none exists.")
        with self.assertRaises(ValueError):
            imp.validate_rewrite("Funding rose sharply this year.", "Funding did not rise this year.")

    def _run_import(self, items, current):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            inbox = tmp / "inbox"; inbox.mkdir()
            (tmp / "reader_language").mkdir()
            (inbox / "reader_language_results.json").write_text(json.dumps(
                {"schema": imp.SCHEMA, "package_id": "p1", "items": items}), encoding="utf-8")
            summary = tmp / "summary.md"
            with patch.object(imp, "ROOT", tmp), \
                 patch.object(imp, "collect_candidates", lambda: current), \
                 patch.object(imp, "load_approved", lambda: {"items": {}}), \
                 patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary)}), \
                 patch.object(sys, "argv", ["x", "--inbox", "inbox"]):
                self.assertEqual(imp.main(), 0)
            approved = json.loads((tmp / "reader_language" / "approved.json").read_text(encoding="utf-8"))
            return approved["items"], summary.read_text(encoding="utf-8"), list(inbox.iterdir())

    def test_one_bad_or_outdated_item_does_not_discard_the_review(self):
        good = "European teams are building shared computing capacity quickly."
        bad = "Funding rose sharply this year."
        cur = [
            {"id": common.item_id(t), "source": t, "display_text": t, "source_sha256": common.fingerprint(t),
             "routes": ["shocks"], "origins": ["x"], "match_variants": [t]}
            for t in (good, bad)
        ]
        items = [
            {"id": cur[0]["id"], "source": good, "display_text": good, "source_sha256": cur[0]["source_sha256"],
             "decision": "REWRITE", "replacement": "European teams are quickly building shared computing power."},
            {"id": cur[1]["id"], "source": bad, "display_text": bad, "source_sha256": cur[1]["source_sha256"],
             "decision": "REWRITE", "replacement": "Funding did not rise this year."},
            {"id": "rl_gone", "source": "Old text", "display_text": "Old text", "source_sha256": "0",
             "decision": "KEEP", "replacement": ""},
        ]
        saved, summary, left = self._run_import(items, cur)
        self.assertIn(cur[0]["id"], saved)
        self.assertEqual(saved[cur[0]["id"]]["status"], "rewrite")
        self.assertNotIn(cur[1]["id"], saved)  # unsafe rewrite comes back later
        self.assertIn("Not imported: **2**", summary)
        self.assertEqual(left, [])  # processed file removed from the inbox

    def test_shock_card_explanation_is_collected(self):
        doc = {"high_order_inference": {
            "publications": {"shock": ["s1"]},
            "candidates": [{"id": "s1", "reader_title": "Title here for the card.",
                            "reader_consequence": "A cyber incident could take the facility offline."}]}}
        store = {}
        with patch.object(common, "_reader_reasoning_document", lambda: (Path("radar.json"), doc)):
            common.collect_radar_reader_fields(store)
        self.assertIn("A cyber incident could take the facility offline.", {c.source for c in store.values()})


if __name__ == "__main__":
    unittest.main()
