import copy
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.active_corpus import build_active_document, record_key
from scripts.deep_read_works import identity_hash, source_hash

ROOT = Path(__file__).resolve().parents[1]


def row(link="https://example.test/paper", strand="A"):
    return {
        "title": "Example European research work",
        "authors": "A. Researcher",
        "source": "Wrong Prestigious Source",
        "source_tier": "Tier 1",
        "source_merit_score": 100,
        "date": "2026-08-01",
        "link": link,
        "type": "peer-reviewed article",
        "strand": strand,
        "summary": "Automatic scanner interpretation.",
        "relevance_note": "Automatic relevance claim.",
    }


def v2_result(r, *, decision="keep", attempts=None, recovered=None):
    key = record_key(r)
    return {
        "format": "radar-deep-scan-results-v2",
        "package_id": "pkg-test",
        "results": [{
            "record_key": key,
            "source_hash": source_hash(r),
            "identity_hash": identity_hash(r),
            "verification": {
                "identity_verified": decision != "drop_unverifiable",
                "evidence_depth": "full_text_or_substantive_primary" if decision != "drop_unverifiable" else "unrecoverable",
                "retrieval_attempts": attempts or [{"step": "supplied_url", "outcome": "success", "note": "matching substantive source"}],
                "recovered_sources": recovered if recovered is not None else ([{"kind": "publisher_full_text", "url": "https://example.test/full", "title": "Example", "evidence_used": True}] if decision != "drop_unverifiable" else []),
                "verification_note": "Verified carefully against the recovered work.",
            },
            "admission": {"decision": decision, "target_strand": "A", "reason_code": "A_SUBSTANTIVE_EU_RI" if decision == "keep" else "UNVERIFIABLE_WORK", "reason": "Evidence-grounded decision after verification."},
            "metadata_correction": {"fields": {"source": "Actual Journal"} if decision == "keep" else {}, "unset": ["source_tier"] if decision == "keep" else [], "reason": "Primary source identifies outlet."},
            "duplicate": {"status": "unique", "duplicate_of": "", "reason": ""},
            "reader_title": "Verified research work",
            "reader_what": "Verified evidence establishes the work's central research finding.",
            "reader_why": "",
            "reader_more": "The full source was checked against the scanner record. The interpretation reflects the recovered work.",
            "deep_analysis": {"work_kind": "empirical study", "research_question": "Question", "main_finding": "Finding", "method_or_basis": "Full text", "qualification": "Bounded finding", "radar_relevance": "Substantive European R&I relevance", "why_supported": False, "confidence": "high"},
        }],
    }


class ActiveCorpusV2Tests(unittest.TestCase):
    def test_drop_filters_active_view_without_mutating_raw(self):
        r = row()
        doc = {"strand_a": [r], "strand_b": [], "strand_c": [], "frontier_evidence": []}
        before = copy.deepcopy(doc)
        key = record_key(r)
        active = build_active_document(doc, admission={"records": {key: {"decision": "drop", "reason_code": "FAIL", "reason": "Fails criteria."}}}, corrections={"records": {}}, reader={"records": {}})
        self.assertEqual(active["strand_a"], [])
        self.assertEqual(doc, before)

    def test_review_remains_active_and_metadata_correction_applies(self):
        r = row()
        doc = {"strand_a": [r], "strand_b": [], "strand_c": [], "frontier_evidence": []}
        key = record_key(r)
        active = build_active_document(
            doc,
            admission={"records": {key: {"decision": "review", "target_strand": "A", "reason_code": "AMBIGUOUS", "reason": "Real judgement needed."}}},
            corrections={"records": {key: {"fields": {"source": "Actual Journal"}, "unset": ["source_tier"]}}},
            reader={"records": {}},
        )
        self.assertEqual(len(active["strand_a"]), 1)
        self.assertEqual(active["strand_a"][0]["source"], "Actual Journal")
        self.assertNotIn("source_tier", active["strand_a"][0])
        self.assertNotIn("source_merit_score", active["strand_a"][0])
        self.assertEqual(active["strand_a"][0]["admission_status"], "review")

    def test_authoritative_v2_semantics_replace_scanner_semantics_only_in_active_copy(self):
        r = row()
        r.update({
            "eu_evidence": ["scanner EU hit"], "ri_evidence": ["scanner R&I hit"],
            "geo_evidence": ["scanner geopolitical hit"], "a_context_evidence": ["scanner context"],
            "a_route": "triangulated-strategic-context", "bridge_sentence": "Automatic bridge.",
            "strategic_classification": {"primary": "risk", "lenses": [{"type": "risk", "passage": "Automatic scanner passage."}]},
            "strategic_classification_source": "source_text", "why_it_matters": "Automatic unsupported WHY.",
        })
        doc = {"strand_a": [r], "strand_b": [], "strand_c": [], "frontier_evidence": []}
        key = record_key(r)
        reader = {"records": {key: {
            "profile": "deep-reader-v2-authoritative",
            "reader_what": "Verified finding replaces scanner wording.",
            "reader_why": "Verified European mechanism.",
            "reader_more": "Full verification found a different substantive interpretation.",
            "deep_analysis": {"main_finding": "Verified main finding.", "radar_relevance": "Verified relevance.", "why_supported": True, "confidence": "high"},
        }}}
        active = build_active_document(doc, admission={"records": {key: {"decision": "keep", "target_strand": "A", "source": "deep_scan_v2"}}}, corrections={"records": {}}, reader=reader)
        got = active["strand_a"][0]
        self.assertTrue(got["summary"].startswith("Full verification"))
        self.assertEqual(got["core_message"], "Verified main finding.")
        self.assertEqual(got["semantic_source"], "deep_scan_v2")
        for stale in ("eu_evidence", "ri_evidence", "geo_evidence", "a_context_evidence", "a_route", "bridge_sentence", "strategic_classification", "strategic_classification_source", "eu_relevance"):
            self.assertNotIn(stale, got)
        self.assertEqual(got["why_it_matters"], "Verified European mechanism.")
        self.assertEqual(doc["strand_a"][0]["summary"], "Automatic scanner interpretation.")
        self.assertIn("eu_evidence", doc["strand_a"][0])

    def test_v2_verified_same_key_variants_coalesce_only_after_verification(self):
        a = row(strand="A")
        b = {**row(strand="B"), "title": "Same work, methods framing"}
        doc = {"strand_a": [a], "strand_b": [b], "strand_c": [], "frontier_evidence": []}
        key = record_key(a)
        provisional = build_active_document(doc, admission={"records": {}}, corrections={"records": {}}, reader={"records": {}})
        self.assertEqual(len(provisional["strand_a"]) + len(provisional["strand_b"]), 2)
        verified = build_active_document(doc, admission={"records": {key: {"decision": "keep", "target_strand": "B", "source": "deep_scan_v2"}}}, corrections={"records": {}}, reader={"records": {}})
        self.assertEqual(len(verified["strand_a"]), 0)
        self.assertEqual(len(verified["strand_b"]), 1)

    def test_lazy_drop_unverifiable_is_rejected_but_exhaustive_one_is_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            r = row()
            corpus = tmp_path / "radar.json"
            sidecar = tmp_path / "reader_text.json"
            inbox = tmp_path / "deep_scan_inbox"
            inbox.mkdir()
            corpus.write_text(json.dumps({"strand_a": [r], "strand_b": [], "strand_c": []}), encoding="utf-8")
            sidecar.write_text(json.dumps({"version": 2, "records": {}}), encoding="utf-8")

            lazy = v2_result(r, decision="drop_unverifiable", attempts=[{"step": "supplied_url", "outcome": "failed", "note": "blocked"}], recovered=[])
            (inbox / "deep_scan_results.json").write_text(json.dumps(lazy), encoding="utf-8")
            subprocess.run([sys.executable, str(ROOT / "scripts/import_deep_scan_results.py"), "--corpus", str(corpus), "--sidecar", str(sidecar), "--inbox", str(inbox)], cwd=ROOT, check=True)
            admission = json.loads((tmp_path / "admission_state.json").read_text()) if (tmp_path / "admission_state.json").exists() else {"records": {}}
            self.assertNotIn(record_key(r), admission.get("records", {}))

            steps = ["supplied_url", "doi", "exact_title", "title_author_year", "official_publisher_or_repository", "broader_identity_search"]
            notes = {
                "supplied_url": "Original page was opened but no matching work was available.",
                "doi": "No DOI is present in the scanner record or recovered metadata.",
                "exact_title": "Exact-title search returned no source matching this claimed work.",
                "title_author_year": "Title plus author and year search returned no defensible match.",
                "official_publisher_or_repository": "Publisher, repository and author-copy searches found no matching work.",
                "broader_identity_search": "Distinctive title fragments and identifiers produced no matching source.",
            }
            thorough = v2_result(r, decision="drop_unverifiable", attempts=[{"step": s, "outcome": "not_applicable" if s == "doi" else "failed", "note": notes[s]} for s in steps], recovered=[])
            (inbox / "deep_scan_results.json").write_text(json.dumps(thorough), encoding="utf-8")
            subprocess.run([sys.executable, str(ROOT / "scripts/import_deep_scan_results.py"), "--corpus", str(corpus), "--sidecar", str(sidecar), "--inbox", str(inbox)], cwd=ROOT, check=True)
            admission = json.loads((tmp_path / "admission_state.json").read_text())
            self.assertEqual(admission["records"][record_key(r)]["decision"], "drop_unverifiable")

    def test_v2_import_survives_ordinary_scanner_semantic_change_using_identity_hash(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            r = row()
            exported = v2_result(r)
            r["summary"] = "Scanner later changed its provisional wording."
            corpus = tmp_path / "radar.json"
            sidecar = tmp_path / "reader_text.json"
            inbox = tmp_path / "deep_scan_inbox"
            inbox.mkdir()
            corpus.write_text(json.dumps({"strand_a": [r], "strand_b": [], "strand_c": []}), encoding="utf-8")
            sidecar.write_text(json.dumps({"version": 2, "records": {}}), encoding="utf-8")
            (inbox / "deep_scan_results.json").write_text(json.dumps(exported), encoding="utf-8")
            subprocess.run([sys.executable, str(ROOT / "scripts/import_deep_scan_results.py"), "--corpus", str(corpus), "--sidecar", str(sidecar), "--inbox", str(inbox)], cwd=ROOT, check=True)
            saved = json.loads(sidecar.read_text())
            self.assertEqual(saved["records"][record_key(r)]["profile"], "deep-reader-v2-authoritative")


    def test_v2_confirmed_duplicate_is_stored_as_duplicate_decision(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            canonical = row("https://example.test/canonical")
            duplicate = row("https://example.test/repository-copy")
            duplicate["title"] = canonical["title"]
            corpus = tmp_path / "radar.json"
            sidecar = tmp_path / "reader_text.json"
            inbox = tmp_path / "deep_scan_inbox"
            inbox.mkdir()
            corpus.write_text(json.dumps({"strand_a": [duplicate, canonical], "strand_b": [], "strand_c": []}), encoding="utf-8")
            sidecar.write_text(json.dumps({"version": 2, "records": {}}), encoding="utf-8")
            result = v2_result(duplicate, decision="keep")
            item = result["results"][0]
            item["admission"] = {"decision": "drop", "target_strand": "A", "reason_code": "DUPLICATE_WORK", "reason": "This is the same underlying publication as the canonical record."}
            item["duplicate"] = {"status": "duplicate", "duplicate_of": record_key(canonical), "reason": "Exact normalized title identifies the same publication."}
            item["metadata_correction"] = {"fields": {}, "unset": [], "reason": ""}
            (inbox / "deep_scan_results.json").write_text(json.dumps(result), encoding="utf-8")
            subprocess.run([sys.executable, str(ROOT / "scripts/import_deep_scan_results.py"), "--corpus", str(corpus), "--sidecar", str(sidecar), "--inbox", str(inbox)], cwd=ROOT, check=True)
            admission = json.loads((tmp_path / "admission_state.json").read_text())
            state = admission["records"][record_key(duplicate)]
            self.assertEqual(state["decision"], "duplicate")
            self.assertEqual(state["duplicate_of"], record_key(canonical))

    def test_v2_import_refuses_cherry_picked_out_of_order_result(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            hard_first = row("https://example.test/hard-first")
            hard_first["first_seen"] = "2026-01-01T00:00:00Z"
            easy_later = row("https://example.test/easy-later")
            easy_later["first_seen"] = "2026-02-01T00:00:00Z"
            corpus = tmp_path / "radar.json"
            sidecar = tmp_path / "reader_text.json"
            inbox = tmp_path / "deep_scan_inbox"
            inbox.mkdir()
            corpus.write_text(json.dumps({"strand_a": [hard_first, easy_later], "strand_b": [], "strand_c": []}), encoding="utf-8")
            sidecar.write_text(json.dumps({"version": 2, "records": {}}), encoding="utf-8")
            (inbox / "deep_scan_results.json").write_text(json.dumps(v2_result(easy_later)), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts/import_deep_scan_results.py"), "--corpus", str(corpus), "--sidecar", str(sidecar), "--inbox", str(inbox)],
                cwd=ROOT, text=True, capture_output=True, check=True,
            )
            self.assertIn("out of FIFO order", proc.stdout)
            saved = json.loads(sidecar.read_text())
            self.assertEqual(saved.get("records", {}), {})
            admission_path = tmp_path / "admission_state.json"
            admission = json.loads(admission_path.read_text()) if admission_path.exists() else {"records": {}}
            self.assertEqual(admission.get("records", {}), {})

    def test_abstract_only_v2_keep_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            r = row()
            corpus = tmp_path / "radar.json"
            sidecar = tmp_path / "reader_text.json"
            inbox = tmp_path / "deep_scan_inbox"
            inbox.mkdir()
            corpus.write_text(json.dumps({"strand_a": [r], "strand_b": [], "strand_c": []}), encoding="utf-8")
            sidecar.write_text(json.dumps({"version": 2, "records": {}}), encoding="utf-8")
            result = v2_result(r, decision="keep")
            result["results"][0]["verification"]["evidence_depth"] = "abstract_only"
            (inbox / "deep_scan_results.json").write_text(json.dumps(result), encoding="utf-8")
            subprocess.run([sys.executable, str(ROOT / "scripts/import_deep_scan_results.py"), "--corpus", str(corpus), "--sidecar", str(sidecar), "--inbox", str(inbox)], cwd=ROOT, check=True)
            admission_path = tmp_path / "admission_state.json"
            admission = json.loads(admission_path.read_text()) if admission_path.exists() else {"records": {}}
            self.assertNotIn(record_key(r), admission.get("records", {}))


    def test_live_repository_known_bad_record_not_in_active_excel(self):
        needle = b"10.55186/25876740_2026_69_3_373"
        workbook = ROOT / "stuff" / "source_merit_ranking.xlsx"
        self.assertTrue(workbook.exists())
        hits = []
        with zipfile.ZipFile(workbook) as zf:
            for name in zf.namelist():
                if name.endswith(".xml") and needle in zf.read(name):
                    hits.append(name)
        self.assertEqual(hits, [])

    def test_live_repository_known_bad_russian_oecd_record_is_raw_but_not_active(self):
        raw = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
        active = json.loads((ROOT / "radar_active.json").read_text(encoding="utf-8"))
        needle = "10.55186/25876740_2026_69_3_373"
        raw_hits = [r for r in raw.get("strand_a", []) if needle in str(r.get("link", ""))]
        active_hits = [r for r in active.get("strand_a", []) if needle in str(r.get("link", ""))]
        self.assertTrue(raw_hits)
        self.assertEqual(raw_hits[0].get("source"), "OECD")
        self.assertEqual(active_hits, [])


if __name__ == "__main__":
    unittest.main()
