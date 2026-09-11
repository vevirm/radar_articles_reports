"""Regression tests for the one-time full accepted-corpus revalidator."""
from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "full_corpus_revalidate.py"
spec = importlib.util.spec_from_file_location("full_corpus_revalidate_test", SCRIPT)
R = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = R
spec.loader.exec_module(R)

NOW = dt.datetime(2026, 9, 11, 0, 0, tzinfo=dt.timezone.utc)


def ab(title: str, strand: str, link: str | None = None) -> dict:
    return {
        "title": title,
        "source": "Test source",
        "date": "2026-09-01",
        "link": link or f"https://example.org/{title.lower().replace(' ', '-')}",
        "summary": "Saved source evidence.",
        "source_tier": "Tier 1",
        "type": "peer-reviewed article",
        "strand": strand,
        "first_seen": "2026-09-02T00:00Z",
        "new_this_scan": False,
    }


def ev(a: bool, b: bool) -> dict:
    return {
        "a_pass": a,
        "b_pass": b,
        "a_focus_pass": a,
        "aboutness_pass": a,
        "aboutness_reason": "about" if a else "no_supported_eu_scope",
        "centrality_pass": a,
        "centrality_reason": "test",
        "eu_relevance": "direct" if a else ("derived" if b else None),
        "eu_evidence": ["European Union"] if a else (["method suitable for analysing future EU R&I/geopolitics"] if b else []),
        "ri_evidence": ["research system"] if a else [],
        "geo_evidence": ["research security"] if a else [],
        "a_route": "eu-ri-system-relevance" if a else "",
        "a_context_evidence": ["research capacity"] if a else [],
        "bridge_sentence": "",
        "method_evidence": ["horizon scanning"] if b else [],
        "method_bridge": "The study evaluates a horizon-scanning method." if b else "",
        "b_route": "method-evaluation" if b else "",
        "text_mode": "abstract",
    }


def c(headline: str, link: str, *, expired: bool = False) -> dict:
    return {
        "headline": headline,
        "what": "Europe opened a new strategic research compute facility.",
        "core_message": "Europe opened a new strategic research compute facility.",
        "signal_note": "Europe opened a new strategic research compute facility.",
        "why_it_matters": "This changes European research compute capacity.",
        "source": "Test news",
        "source_domain": "example.org",
        "date": "2026-09-10",
        "c_event_date": "2026-09-10",
        "event_status": "DONE",
        "c_admission_route": "event",
        "link": link,
        "first_seen": "2026-09-10T00:00Z",
        "anchor_status": "anchored",
        "signal_kind": "policy / strategy",
        "realisation_status": "operating",
        "force_expired": expired,
        "new_this_scan": False,
    }


class FullCorpusRevalidationTests(unittest.TestCase):
    def base_doc(self) -> dict:
        return {
            "strand_a": [], "strand_b": [], "ab_archive": [],
            "strand_c": [], "signal_archive": [],
            "strategic_pathways": [{"id": "keep-me"}],
            "external_shock_watch": [{"id": "keep-me-too"}],
            "shock_inference": {"unchanged": True},
            "high_order_inference": {"unchanged": True},
        }

    @mock.patch.object(R.sr, "record_date_integrity_ok", return_value=True)
    @mock.patch.object(R.sr, "record_source_integrity_ok", return_value=True)
    def test_a_to_b_reclassification_when_current_a_fails_and_b_passes(self, _src, _date):
        doc = self.base_doc(); doc["strand_a"] = [ab("Method paper", "A")]
        with mock.patch.object(R, "_ab_gate", return_value=ev(False, True)):
            out, report = R.revalidate_document(doc, now=NOW, network_refresh=False, workers=1)
        self.assertEqual(len(out["strand_a"]), 0)
        self.assertEqual(len(out["strand_b"]), 1)
        self.assertEqual(out["strand_b"][0]["strand"], "B")
        self.assertEqual(report["diagnostics"]["A"]["reclassified_to_B"], 1)

    @mock.patch.object(R.sr, "record_date_integrity_ok", return_value=True)
    @mock.patch.object(R.sr, "record_source_integrity_ok", return_value=True)
    def test_b_to_a_reclassification_when_current_b_fails_and_a_passes(self, _src, _date):
        doc = self.base_doc(); doc["strand_b"] = [ab("European system report", "B")]
        with mock.patch.object(R, "_ab_gate", return_value=ev(True, False)):
            out, report = R.revalidate_document(doc, now=NOW, network_refresh=False, workers=1)
        self.assertEqual(len(out["strand_b"]), 0)
        self.assertEqual(len(out["strand_a"]), 1)
        self.assertEqual(report["diagnostics"]["B"]["reclassified_to_A"], 1)

    @mock.patch.object(R.sr, "record_date_integrity_ok", return_value=True)
    @mock.patch.object(R.sr, "record_source_integrity_ok", return_value=True)
    def test_both_pass_keeps_existing_strand_not_ratio_driven_move(self, _src, _date):
        doc = self.base_doc(); doc["strand_a"] = [ab("Both paper", "A")]
        with mock.patch.object(R, "_ab_gate", return_value=ev(True, True)):
            out, report = R.revalidate_document(doc, now=NOW, network_refresh=False, workers=1)
        self.assertEqual(len(out["strand_a"]), 1)
        self.assertEqual(len(out["strand_b"]), 0)
        self.assertEqual(report["diagnostics"]["soft_mix_policy"]["hard_quota"], False)
        self.assertEqual(report["diagnostics"]["soft_mix_policy"]["used_for_accept_reject"], False)

    @mock.patch.object(R.sr, "record_date_integrity_ok", return_value=True)
    @mock.patch.object(R.sr, "record_source_integrity_ok", return_value=True)
    def test_failed_ab_is_removed_in_strict_one_time_mode(self, _src, _date):
        doc = self.base_doc(); doc["strand_a"] = [ab("Bad A", "A")]
        with mock.patch.object(R, "_ab_gate", return_value=ev(False, False)):
            out, report = R.revalidate_document(doc, now=NOW, network_refresh=False, workers=1)
        self.assertEqual(out["strand_a"], [])
        self.assertEqual(report["diagnostics"]["A"]["removed"], 1)
        self.assertEqual(report["decision_count"], 1)

    def test_refresh_cannot_bypass_current_saved_record_document_exclusion(self):
        item = ab(
            "EU research policy announcement",
            "A",
            "https://example.org/news/eu-research-policy-announcement",
        )
        refreshed = (
            item["title"],
            "European Union research and innovation capacity, research security and strategic autonomy.",
            "Substantive European R&I system evidence.",
        )
        with mock.patch.object(R.sr, "document_exclusion_reason", return_value="hard exclusion URL: /news/"), \
             mock.patch.object(R.sr, "gate_scope", return_value=ev(True, False)) as gate_scope:
            result = R._ab_gate(item, refreshed)
        self.assertFalse(result["a_pass"])
        self.assertFalse(result["b_pass"])
        self.assertTrue(result["document_rejected"])
        self.assertIn("/news/", result["aboutness_reason"])
        gate_scope.assert_not_called()

    @mock.patch.object(R.sr, "record_date_integrity_ok", return_value=True)
    @mock.patch.object(R.sr, "record_source_integrity_ok", return_value=True)
    def test_failed_saved_ab_is_reopened_before_final_decision(self, _src, _date):
        doc = self.base_doc(); doc["strand_a"] = [ab("Thin saved A", "A")]
        refreshed = {0: ("Thin saved A", "European research system capacity and research security evidence.", "") }
        with mock.patch.object(R, "_ab_gate", side_effect=[ev(False, False), ev(True, False)]), \
             mock.patch.object(R, "_refresh_failed_ab", return_value=(refreshed, {"attempted": 1, "succeeded": 1, "unavailable": 0})):
            out, report = R.revalidate_document(doc, now=NOW, network_refresh=True, workers=1)
        self.assertEqual(len(out["strand_a"]), 1)
        self.assertEqual(report["decisions"][0]["evidence_refresh"], "refreshed")
        self.assertEqual(report["decisions"][0]["decision"], "keep")

    @mock.patch.object(R.sr, "record_date_integrity_ok", return_value=True)
    @mock.patch.object(R.sr, "record_source_integrity_ok", return_value=True)
    def test_broad_refresh_outage_stops_before_mass_deletion(self, _src, _date):
        doc = self.base_doc(); doc["strand_a"] = [ab(f"Thin A {i}", "A") for i in range(20)]
        with mock.patch.object(R, "_ab_gate", return_value=ev(False, False)), \
             mock.patch.object(R, "_refresh_failed_ab", return_value=({}, {"attempted": 20, "succeeded": 0, "unavailable": 20})):
            with self.assertRaisesRegex(RuntimeError, "Safety stop"):
                R.revalidate_document(doc, now=NOW, network_refresh=True, workers=1)

    @mock.patch.object(R.sr, "record_date_integrity_ok", return_value=True)
    @mock.patch.object(R.sr, "record_source_integrity_ok", return_value=True)
    def test_ab_identity_duplicate_is_removed_once_with_audit(self, _src, _date):
        doc = self.base_doc()
        doc["strand_a"] = [ab("Same evidence", "A", "https://example.org/one"), ab("Same evidence", "A", "https://example.org/two")]
        with mock.patch.object(R, "_ab_gate", return_value=ev(True, False)):
            out, report = R.revalidate_document(doc, now=NOW, network_refresh=False, workers=1)
        self.assertEqual(len(out["strand_a"]), 1)
        self.assertEqual(report["diagnostics"]["duplicates_removed"], 1)
        self.assertEqual(sum(1 for d in report["decisions"] if d.get("reason_code") == "AB_DUPLICATE_IDENTITY"), 1)

    def test_c_expiry_and_same_event_dedupe_use_current_c_controls(self):
        doc = self.base_doc()
        doc["strand_c"] = [
            c("Europe opens strategic compute facility", "https://example.org/a"),
            c("Europe opens strategic compute facility", "https://example.org/b"),
            c("Older valid signal", "https://example.org/old", expired=True),
        ]
        with mock.patch.object(R.sr, "_saved_signal_passes", return_value=True), \
             mock.patch.object(R.sr, "signal_is_retired", return_value=False), \
             mock.patch.object(R.sr, "signal_retention_expired", side_effect=lambda item, now: bool(item.get("force_expired"))):
            out, report = R.revalidate_document(doc, now=NOW, network_refresh=False, workers=1)
        self.assertEqual(len(out["strand_c"]), 1)
        self.assertEqual(len(out["signal_archive"]), 1)
        self.assertEqual(report["diagnostics"]["C"]["moved_to_archive"], 1)
        self.assertEqual(report["diagnostics"]["duplicates_removed"], 1)

    def test_invalid_archived_c_is_removed_not_preserved_as_accepted_history(self):
        doc = self.base_doc(); doc["signal_archive"] = [c("Invalid old signal", "https://example.org/old")]
        with mock.patch.object(R.sr, "_saved_signal_passes", return_value=False), \
             mock.patch.object(R.sr, "signal_is_retired", return_value=False), \
             mock.patch.object(R, "c_failure_reason", return_value=("C_TEST_FAIL", "fails current C")):
            out, report = R.revalidate_document(doc, now=NOW, network_refresh=False, workers=1)
        self.assertEqual(out["signal_archive"], [])
        self.assertEqual(report["diagnostics"]["C"]["removed"], 1)

    def test_higher_order_reasoning_is_untouched(self):
        doc = self.base_doc()
        before = {k: doc[k] for k in R.PROTECTED_HIGHER_ORDER_KEYS}
        out, _ = R.revalidate_document(doc, now=NOW, network_refresh=False, workers=1)
        self.assertEqual({k: out[k] for k in R.PROTECTED_HIGHER_ORDER_KEYS}, before)

    def test_workflow_commits_backup_before_mutation_and_reruns_tests(self):
        wf = (ROOT / ".github" / "workflows" / "one-time-full-corpus-revalidation.yml").read_text(encoding="utf-8")
        self.assertIn("name: ONE-TIME Full Corpus Revalidation", wf)
        self.assertIn("Commit backup before changing corpus", wf)
        self.assertIn("scripts/full_corpus_revalidate.py", wf)
        self.assertLess(wf.index("Commit backup before changing corpus"), wf.index("Revalidate the complete accepted evidence corpus"))
        self.assertGreaterEqual(wf.count("python -m unittest discover -s tests -p 'test_*.py'"), 2)
        self.assertIn("actions/upload-artifact@v4", wf)
        self.assertIn("group: ri-radar-research-scanners", wf)
        self.assertIn("Determine first run or v1.0 correction rerun", wf)
        self.assertIn("Restore exact original backup in runner for v1.0 correction", wf)
        self.assertIn("v1.1-current-scanner-rules", wf)

    def test_restore_prefers_new_full_revalidation_backup(self):
        wf = (ROOT / ".github" / "workflows" / "restore-corpus-backup.yml").read_text(encoding="utf-8")
        new = "backups/one-time-full-corpus-revalidation/LATEST_BACKUP.txt"
        old = "backups/one-time-corpus-cleanup/LATEST_BACKUP.txt"
        self.assertIn(new, wf); self.assertIn(old, wf)
        self.assertLess(wf.index(new), wf.index(old))


    def test_validator_explicitly_allows_intentional_full_revalidation_cleanup(self):
        text = (ROOT / "scripts" / "validate_scanner_output.py").read_text(encoding="utf-8")
        self.assertIn('new.get("full_corpus_revalidation")', text)
        self.assertIn('full_revalidation.get("discovery_scan") is False', text)


if __name__ == "__main__":
    unittest.main()
