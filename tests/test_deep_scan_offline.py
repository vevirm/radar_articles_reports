import json
import subprocess
import sys
import zipfile
from pathlib import Path

from scripts.deep_read_works import record_key, source_hash

ROOT = Path(__file__).resolve().parents[1]


def _radar_doc():
    row = {
        "title": "Example research work",
        "date": "2026-09-01",
        "link": "https://example.test/work",
        "summary": "Researchers compare two approaches and report a bounded result for a specific setting.",
        "relevance_note": "The scanner considers the result relevant to research capability.",
        "source": "Example Journal",
        "type": "peer-reviewed article",
    }
    return {"strand_a": [row], "strand_b": [], "strand_c": []}, row


def test_offline_package_contains_instructions_manifest_and_all_pending(tmp_path):
    doc, _row = _radar_doc()
    corpus = tmp_path / "radar.json"
    sidecar = tmp_path / "reader_text.json"
    out = tmp_path / "out"
    corpus.write_text(json.dumps(doc), encoding="utf-8")
    sidecar.write_text(json.dumps({"version": 2, "profile": "deep-reader-offline-v1", "generated_at": None, "records": {}}), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "prepare_deep_scan_package.py"),
            "--corpus", str(corpus),
            "--sidecar", str(sidecar),
            "--output-dir", str(out),
            "--no-fetch",
        ],
        cwd=ROOT,
        check=True,
    )

    package = out / "deep_scan_package.zip"
    assert package.exists()
    with zipfile.ZipFile(package) as zf:
        assert zf.testzip() is None
        names = zf.namelist()
        root = names[0].split("/", 1)[0]
        instructions = zf.read(f"{root}/INSTRUCTIONS.md").decode("utf-8")
        manifest = json.loads(zf.read(f"{root}/manifest.json"))
        batch = json.loads(zf.read(f"{root}/batches/batch_001.json"))
    assert "understand each work" in instructions
    assert "Partial completion" in instructions
    assert manifest["works_in_package"] == 1
    assert len(batch["jobs"]) == 1
    assert batch["jobs"][0]["record_key"] == record_key(doc["strand_a"][0])


def test_offline_import_accepts_current_hash_and_removes_inbox_file(tmp_path):
    doc, row = _radar_doc()
    corpus = tmp_path / "radar.json"
    sidecar = tmp_path / "reader_text.json"
    inbox = tmp_path / "deep_scan_inbox"
    inbox.mkdir()
    corpus.write_text(json.dumps(doc), encoding="utf-8")
    sidecar.write_text(json.dumps({"version": 2, "profile": "deep-reader-offline-v1", "generated_at": None, "records": {}}), encoding="utf-8")

    result = {
        "format": "radar-deep-scan-results-v1",
        "package_id": "test-package",
        "results": [{
            "record_key": record_key(row),
            "source_hash": source_hash(row),
            "reader_title": "What this research work actually found",
            "reader_what": "Researchers report a bounded difference between two approaches in the setting they studied.",
            "reader_why": "",
            "reader_more": "The work compares two approaches in a specific setting. Its result should not be assumed to apply more broadly.",
            "deep_analysis": {
                "work_kind": "empirical study",
                "research_question": "How do the two approaches compare?",
                "main_finding": "They differ in the studied setting.",
                "method_or_basis": "comparative study",
                "qualification": "The result is setting-specific.",
                "radar_relevance": "research capability",
                "why_supported": False,
                "confidence": "medium",
            },
        }],
    }
    returned = inbox / "deep_scan_results.json"
    returned.write_text(json.dumps(result), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "import_deep_scan_results.py"),
            "--corpus", str(corpus),
            "--sidecar", str(sidecar),
            "--inbox", str(inbox),
        ],
        cwd=ROOT,
        check=True,
    )

    saved = json.loads(sidecar.read_text(encoding="utf-8"))
    entry = saved["records"][record_key(row)]
    assert entry["profile"] == "deep-reader-offline-v1"
    assert entry["reader_what"].startswith("Researchers report")
    assert not returned.exists()


def test_offline_import_skips_stale_hash(tmp_path):
    doc, row = _radar_doc()
    corpus = tmp_path / "radar.json"
    sidecar = tmp_path / "reader_text.json"
    inbox = tmp_path / "deep_scan_inbox"
    inbox.mkdir()
    old_hash = source_hash(row)
    row["relevance_note"] = "The automatic scanner later stored materially different semantic evidence."
    corpus.write_text(json.dumps(doc), encoding="utf-8")
    sidecar.write_text(json.dumps({"version": 2, "profile": "deep-reader-offline-v1", "generated_at": None, "records": {}}), encoding="utf-8")
    returned = inbox / "deep_scan_results.json"
    returned.write_text(json.dumps({
        "format": "radar-deep-scan-results-v1",
        "package_id": "old-package",
        "results": [{
            "record_key": record_key(row),
            "source_hash": old_hash,
            "reader_what": "An interpretation based on the older package evidence.",
            "reader_why": "",
            "reader_more": "This should be skipped because the scanner material changed.",
            "deep_analysis": {"why_supported": False, "confidence": "low"},
        }],
    }), encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "import_deep_scan_results.py"),
            "--corpus", str(corpus),
            "--sidecar", str(sidecar),
            "--inbox", str(inbox),
        ],
        cwd=ROOT,
        check=True,
    )
    saved = json.loads(sidecar.read_text(encoding="utf-8"))
    assert saved["records"] == {}
    assert not returned.exists()


def test_offline_package_does_not_requeue_completed_work_after_scanner_change(tmp_path):
    doc, row = _radar_doc()
    old_hash = source_hash(row)
    row["relevance_note"] = "The fast scanner later changed this wording."
    corpus = tmp_path / "radar.json"
    sidecar = tmp_path / "reader_text.json"
    out = tmp_path / "out"
    corpus.write_text(json.dumps(doc), encoding="utf-8")
    sidecar.write_text(json.dumps({
        "version": 2,
        "profile": "deep-reader-offline-v1",
        "generated_at": None,
        "records": {record_key(row): {
            "profile": "deep-reader-offline-v1",
            "source_hash": old_hash,
            "reader_what": "A valid earlier Deep Scan interpretation.",
        }},
    }), encoding="utf-8")

    subprocess.run([
        sys.executable, str(ROOT / "scripts" / "prepare_deep_scan_package.py"),
        "--corpus", str(corpus), "--sidecar", str(sidecar),
        "--output-dir", str(out), "--no-fetch",
    ], cwd=ROOT, check=True)

    assert (out / "NO_DEEP_SCAN_NEEDED.txt").exists()
    assert not (out / "deep_scan_package.zip").exists()
