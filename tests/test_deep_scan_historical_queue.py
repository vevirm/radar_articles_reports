import copy
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.deep_read_works import (
    historical_pending,
    historical_record_key,
    identity_hash,
    source_hash,
)
from scripts.deep_scan_work_state import (
    MAX_RECOVERY_ATTEMPTS, empty_state, fill_lane, mark_recovery_failure,
    prioritize_pending_keys, write_status_markdown, update_record_metadata,
)
from scripts.import_deep_scan_results import validate_v2_result
from scripts.rebuild_active_radar import _add_historical_context
from scripts.active_corpus import build_active_document

ROOT = Path(__file__).resolve().parents[1]


def _main_row(name="Main work"):
    return {
        "title": name,
        "date": "2026-09-12",
        "link": f"https://example.test/{name.lower().replace(' ', '-')}",
        "summary": "A substantive current European research and innovation work.",
        "source": "Example Journal",
        "type": "peer-reviewed article",
        "first_seen": "2026-09-14T08:00:00Z",
    }


def _hist_row(idx=1, strand="A"):
    return {
        "id": f"hist-{idx}",
        "title": f"Historical work {idx}",
        "date": "2024-06-01",
        "url": f"https://example.test/historical-{idx}",
        "source": "Historical Journal",
        "type": "peer-reviewed article",
        "strand": strand,
        "reader_point": "The historical study documents a substantive European research-system development.",
        "why_it_matters": "Useful historical context for judging later structural change.",
    }


def _historical_deep_row(raw):
    row = copy.deepcopy(raw)
    row["_deep_scan_record_key"] = historical_record_key(raw)
    row["_deep_scan_scope"] = "historical"
    return row


def _valid_v2_result(raw_hist, target="A"):
    row = _historical_deep_row(raw_hist)
    return {
        "record_key": historical_record_key(raw_hist),
        "source_hash": source_hash(row),
        "identity_hash": identity_hash(row),
        "verification": {
            "identity_verified": True,
            "evidence_depth": "full_text_primary",
            "retrieval_attempts": [{
                "step": "supplied_url",
                "outcome": "success",
                "note": "Opened the supplied URL and matched the complete work identity.",
            }],
            "recovered_sources": [{
                "url": raw_hist["url"],
                "kind": "full_text_primary",
                "evidence_used": True,
            }],
            "verification_note": "Full matching source verified the identity and substantive historical evidence.",
        },
        "admission": {
            "decision": "keep",
            "target_strand": target,
            "reason_code": "HISTORICAL_EVIDENCE_VERIFIED",
            "reason": "The recovered work meets the substantive historical Radar evidence standard.",
        },
        "metadata_correction": {"fields": {}, "unset": [], "reason": ""},
        "duplicate": {"status": "unique", "duplicate_of": "", "reason": "No duplicate identified."},
        "reader_title": "Historical research-system evidence",
        "reader_what": "The study documents a bounded European research-system development in its historical period.",
        "reader_why": "",
        "reader_more": "The work documents a historical European research-system development. It provides structural context without claiming a current event.",
        "deep_analysis": {
            "work_kind": "historical empirical study",
            "research_question": "What changed in the European research system during the studied period?",
            "main_finding": "The work documents a bounded historical change in the European research system.",
            "method_or_basis": "Primary-source analysis and empirical comparison.",
            "qualification": "The finding describes the studied historical period rather than the present.",
            "radar_relevance": "It provides historical context for later European research-system developments.",
            "why_supported": False,
            "confidence": "high",
        },
    }


def _valid_defer_result(raw, *, historical=False):
    if historical:
        row = _historical_deep_row(raw)
        key = historical_record_key(raw)
    else:
        row = copy.deepcopy(raw)
        key = f"link:{raw['link']}"
    notes = {
        "supplied_url": "Supplied page matched the work identity but did not expose substantive content.",
        "doi": "DOI resolution confirmed the publication identity but the substantive text stayed inaccessible.",
        "exact_title": "Exact-title search confirmed the work but returned no usable primary full text.",
        "title_author_year": "Title, author and year search confirmed identity without substantive accessible evidence.",
        "official_publisher_or_repository": "Official publisher and repository routes were checked but no substantive copy was accessible.",
        "broader_identity_search": "Broader identity search found corroborating metadata only, not substantive evidence.",
    }
    return {
        "record_key": key,
        "source_hash": source_hash(row),
        "identity_hash": identity_hash(row),
        "verification": {
            "identity_verified": True,
            "evidence_depth": "identity_only_after_recovery",
            "retrieval_attempts": [
                {"step": step, "outcome": "unavailable", "note": note}
                for step, note in notes.items()
            ],
            "recovered_sources": [],
            "verification_note": "Identity is credible, but all recovery routes failed to expose substantive evidence.",
        },
        "admission": {
            "decision": "defer",
            "target_strand": "",
            "reason_code": "EVIDENCE_ACCESS_LIMITED",
            "reason": "The work clearly exists, but substantive evidence remains inaccessible after the full recovery ladder.",
        },
        "metadata_correction": {"fields": {}, "unset": [], "reason": ""},
        "duplicate": {"status": "unique", "duplicate_of": "", "reason": "No duplicate identified."},
        "reader_title": "", "reader_what": "", "reader_why": "", "reader_more": "",
        "deep_analysis": {
            "work_kind": "", "research_question": "", "main_finding": "", "method_or_basis": "",
            "qualification": "", "radar_relevance": "", "why_supported": False, "confidence": "low",
        },
    }


class HistoricalDeepScanQueueTests(unittest.TestCase):
    def test_historical_pending_uses_separate_namespace_and_skips_verified(self):
        raw = _hist_row(1)
        hist = {"items": [raw]}
        todo = historical_pending(hist, {"records": {}})
        self.assertEqual(len(todo), 1)
        self.assertEqual(todo[0][1], "historical:id:hist-1")
        self.assertEqual(todo[0][3]["_deep_scan_scope"], "historical")
        sidecar = {"records": {"historical:id:hist-1": {"profile": "deep-reader-v2-authoritative"}}}
        self.assertEqual(historical_pending(hist, sidecar), [])

    def test_free_lane_slots_take_new_main_before_more_historical(self):
        state = empty_state()
        state["lanes"]["A"]["assigned"] = ["historical:id:old-1"]
        state["records"]["historical:id:old-1"] = {"status": "assigned", "lane": "A"}
        assigned = fill_lane(
            state, "A",
            ["link:https://example.test/new-main", "historical:id:old-1", "historical:id:old-2"],
            target_size=3,
        )
        self.assertEqual(assigned, [
            "historical:id:old-1", "link:https://example.test/new-main", "historical:id:old-2"
        ])

    def test_worker_package_fills_main_first_then_historical(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            corpus = tmp_path / "radar.json"
            historical = tmp_path / "historical" / "historical.json"
            historical.parent.mkdir()
            sidecar = tmp_path / "reader_text.json"
            work_state = tmp_path / "deep_scan_work_state.json"
            status = tmp_path / "DEEP_SCAN_STATUS.md"
            out = tmp_path / "out"
            corpus.write_text(json.dumps({
                "strand_a": [_main_row("Main one"), _main_row("Main two")],
                "strand_b": [], "strand_c": [], "frontier_evidence": [],
            }), encoding="utf-8")
            historical.write_text(json.dumps({"items": [_hist_row(1), _hist_row(2), _hist_row(3)]}), encoding="utf-8")
            sidecar.write_text(json.dumps({"version": 3, "records": {}}), encoding="utf-8")
            subprocess.run([
                sys.executable, str(ROOT / "scripts" / "prepare_deep_scan_package.py"),
                "--corpus", str(corpus), "--historical", str(historical), "--sidecar", str(sidecar),
                "--output-dir", str(out), "--no-fetch", "--lane", "A", "--lane-size", "4",
                "--work-state", str(work_state), "--status-file", str(status), "--write-work-state",
            ], cwd=ROOT, check=True)
            with zipfile.ZipFile(out / "deep_scan_package.zip") as zf:
                root = zf.namelist()[0].split("/", 1)[0]
                batch = json.loads(zf.read(f"{root}/batches/batch_001.json"))
                manifest = json.loads(zf.read(f"{root}/manifest.json"))
            jobs = batch["jobs"]
            self.assertEqual([j["corpus_scope"] for j in jobs], ["main", "main", "historical", "historical"])
            self.assertEqual(manifest["scope_counts"], {"main": 2, "historical": 2})
            self.assertEqual(manifest["main_pending_total"], 2)
            self.assertEqual(manifest["historical_pending_total"], 3)

    def test_import_accepts_historical_v2_without_rewriting_raw_archive(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            corpus = tmp_path / "radar.json"
            historical = tmp_path / "historical" / "historical.json"
            historical.parent.mkdir()
            sidecar = tmp_path / "reader_text.json"
            inbox = tmp_path / "deep_scan_inbox"
            work_state = tmp_path / "deep_scan_work_state.json"
            inbox.mkdir()
            raw_hist = _hist_row(1)
            corpus.write_text(json.dumps({"strand_a": [], "strand_b": [], "strand_c": [], "frontier_evidence": []}), encoding="utf-8")
            historical.write_text(json.dumps({"items": [raw_hist]}, indent=2), encoding="utf-8")
            before = historical.read_text(encoding="utf-8")
            sidecar.write_text(json.dumps({"version": 3, "records": {}}), encoding="utf-8")
            (inbox / "deep_scan_results.json").write_text(json.dumps({
                "format": "radar-deep-scan-results-v2",
                "package_id": "historical-test-package",
                "results": [_valid_v2_result(raw_hist)],
            }), encoding="utf-8")
            subprocess.run([
                sys.executable, str(ROOT / "scripts" / "import_deep_scan_results.py"),
                "--corpus", str(corpus), "--historical", str(historical), "--sidecar", str(sidecar),
                "--inbox", str(inbox), "--work-state", str(work_state),
            ], cwd=ROOT, check=True)
            saved = json.loads(sidecar.read_text(encoding="utf-8"))
            key = historical_record_key(raw_hist)
            self.assertEqual(saved["records"][key]["profile"], "deep-reader-v2-authoritative")
            self.assertEqual(saved["records"][key]["corpus_scope"], "historical")
            admission = json.loads((tmp_path / "admission_state.json").read_text(encoding="utf-8"))
            self.assertEqual(admission["records"][key]["decision"], "keep")
            self.assertEqual(historical.read_text(encoding="utf-8"), before)

    def test_historical_jobs_cannot_be_reclassified_as_current_c(self):
        raw_hist = _hist_row(1)
        result = _valid_v2_result(raw_hist, target="C")
        problems = validate_v2_result(
            result, key=historical_record_key(raw_hist),
            current_keys={historical_record_key(raw_hist)}, allowed_target_strands={"A", "B"},
        )
        self.assertTrue(any("target_strand A/B" in p for p in problems))

    def test_historical_context_respects_drop_and_a_to_b_reclassification(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            a1, a2, b1 = _hist_row(1, "A"), _hist_row(2, "A"), _hist_row(3, "B")
            path = tmp_path / "historical.json"
            path.write_text(json.dumps({"items": [a1, a2, b1]}), encoding="utf-8")
            admission = {"records": {
                historical_record_key(a1): {"decision": "drop", "target_strand": "A"},
                historical_record_key(a2): {"decision": "keep", "target_strand": "B"},
                historical_record_key(b1): {"decision": "keep", "target_strand": "A"},
            }}
            reader = {"records": {
                historical_record_key(x): {"profile": "deep-reader-v2-authoritative"} for x in (a1, a2, b1)
            }}
            doc = {}
            coverage = _add_historical_context(
                doc, admission=admission, corrections={"records": {}}, reader=reader, historical_path=path
            )
            self.assertEqual([r["id"] for r in doc["historical_context"]], ["hist-3"])
            self.assertEqual(coverage, {
                "total_records": 3, "v2_verified": 3, "v2_pending": 0, "active_a_context": 1
            })


    def test_recovery_is_capped_at_three_then_moves_to_hands_on(self):
        state = empty_state()
        key = "link:https://example.test/access-limited"
        state["lanes"]["A"]["assigned"] = [key]
        state["records"][key] = {"status": "assigned", "lane": "A"}
        verification = {"identity_verified": True, "evidence_depth": "identity_only_after_recovery"}
        self.assertEqual(mark_recovery_failure(state, key, "pkg-1", reason="access unavailable", verification=verification), "recovery_retry")
        self.assertEqual(state["records"][key]["recovery_attempts"], 1)
        state["lanes"]["A"]["assigned"] = [key]
        state["records"][key]["status"] = "assigned"
        self.assertEqual(mark_recovery_failure(state, key, "pkg-2", reason="still unavailable", verification=verification), "recovery_retry")
        state["lanes"]["A"]["assigned"] = [key]
        state["records"][key]["status"] = "assigned"
        self.assertEqual(mark_recovery_failure(state, key, "pkg-3", reason="still unavailable", verification=verification), "needs_manual_verification")
        self.assertEqual(state["records"][key]["recovery_attempts"], MAX_RECOVERY_ATTEMPTS)
        self.assertNotIn(key, state["lanes"]["A"]["assigned"])

    def test_hands_on_work_is_never_reassigned(self):
        state = empty_state()
        manual = "link:https://example.test/manual"
        fresh = "link:https://example.test/fresh"
        state["records"][manual] = {"status": "needs_manual_verification", "recovery_attempts": 3}
        assigned = fill_lane(state, "A", [manual, fresh], target_size=2)
        self.assertEqual(assigned, [fresh])

    def test_retries_do_not_monopolize_historical_capacity(self):
        state = empty_state()
        retry_keys = [f"link:https://example.test/retry-{i}" for i in range(4)]
        hist_keys = [f"historical:id:h-{i}" for i in range(22)]
        for key in retry_keys:
            state["records"][key] = {"status": "recovery_retry", "recovery_attempts": 1}
        ordered = prioritize_pending_keys(state, hist_keys + retry_keys)
        # First twelve background slots contain eleven fresh Historical works and one retry.
        self.assertEqual(sum(1 for k in ordered[:12] if k in retry_keys), 1)
        self.assertEqual(sum(1 for k in ordered[:12] if k in hist_keys), 11)

    def test_status_contains_persistent_hands_on_list(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "DEEP_SCAN_STATUS.md"
            state = empty_state()
            key = "link:https://example.test/manual-work"
            row = _main_row("Manual work")
            update_record_metadata(state, key, row)
            state["records"][key].update({
                "status": "needs_manual_verification",
                "recovery_attempts": 3,
                "manual_verification_reason": "Substantive content remained inaccessible.",
            })
            write_status_markdown(state, {"records": {}}, [key], path)
            text = path.read_text(encoding="utf-8")
            self.assertIn("## Hands-on verification needed", text)
            self.assertIn("Manual work", text)
            self.assertIn("attempts: 3/3", text)

    def test_manual_verification_admission_is_inactive(self):
        row = _main_row("Manual inactive")
        key = f"link:{row['link']}"
        raw = {"strand_a": [row], "strand_b": [], "strand_c": [], "frontier_evidence": []}
        active = build_active_document(raw, admission={"records": {key: {
            "decision": "needs_manual_verification",
            "reason_code": "NEEDS_MANUAL_VERIFICATION",
            "reason": "Substantive evidence could not be recovered automatically.",
        }}}, corrections={"records": {}}, reader={"records": {}})
        self.assertEqual(active["strand_a"], [])
        self.assertEqual(active["active_corpus"]["decision_counts"]["needs_manual_verification"], 1)

    def test_importer_retries_twice_then_writes_terminal_manual_admission(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            corpus = tmp / "radar.json"
            hist = tmp / "historical" / "historical.json"
            hist.parent.mkdir()
            sidecar = tmp / "reader_text.json"
            admission = tmp / "admission_state.json"
            corrections = tmp / "record_corrections.json"
            inbox = tmp / "deep_scan_inbox"
            work_state = tmp / "deep_scan_work_state.json"
            inbox.mkdir()
            row = _main_row("Three-pass access case")
            corpus.write_text(json.dumps({"strand_a": [row], "strand_b": [], "strand_c": [], "frontier_evidence": []}), encoding="utf-8")
            hist.write_text(json.dumps({"items": []}), encoding="utf-8")
            sidecar.write_text(json.dumps({"version": 3, "records": {}}), encoding="utf-8")
            for attempt in range(1, 4):
                result = _valid_defer_result(row)
                (inbox / "deep_scan_results.json").write_text(json.dumps({
                    "format": "radar-deep-scan-results-v2",
                    "package_id": f"attempt-{attempt}",
                    "results": [result],
                }), encoding="utf-8")
                subprocess.run([
                    sys.executable, str(ROOT / "scripts" / "import_deep_scan_results.py"),
                    "--corpus", str(corpus), "--historical", str(hist), "--sidecar", str(sidecar),
                    "--admission", str(admission), "--corrections", str(corrections),
                    "--inbox", str(inbox), "--work-state", str(work_state),
                ], cwd=ROOT, check=True)
                state = json.loads(work_state.read_text(encoding="utf-8"))
                key = f"link:{row['link']}"
                expected = "recovery_retry" if attempt < 3 else "needs_manual_verification"
                self.assertEqual(state["records"][key]["status"], expected)
                self.assertEqual(state["records"][key]["recovery_attempts"], attempt)
            adm = json.loads(admission.read_text(encoding="utf-8"))
            key = f"link:{row['link']}"
            self.assertEqual(adm["records"][key]["decision"], "needs_manual_verification")
            self.assertEqual(adm["records"][key]["recovery_attempts"], 3)


if __name__ == "__main__":
    unittest.main()
