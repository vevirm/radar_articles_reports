import copy
import json
import zipfile
from pathlib import Path

import pytest

from scripts.backfill_claims import (
    PACKAGE_FORMAT,
    RESULT_FORMAT,
    _job_hash,
    build_jobs,
    import_results,
    prepare,
)
from scripts.claims_schema import load_vocabulary

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "reasoning-reform" / "claim_fixtures.json"
VOCAB = ROOT / "claims_vocabulary.json"


def fixture_claim():
    return copy.deepcopy(json.loads(FIXTURE.read_text(encoding="utf-8"))["claims"][0])


def sample_job():
    claim = fixture_claim()
    job = {
        "record_key": claim["record_key"],
        "source_hash": "deadbeef",
        "identity_hash": "0123456789abcdef",
        "era": "current",
        "strand": "strand_a",
        "decision": "keep",
        "decision_weight": 1.0,
        "merit": claim["merit"],
        "stored_text": {
            "reader_title": "EuroHPC opens AI Gigafactory call",
            "reader_what": claim["text"],
            "reader_why": "The call expands EU compute procurement capacity.",
            "reader_more": "Stored Deep Scan text only.",
            "deep_analysis": {
                "work_kind": "official call",
                "research_question": "",
                "main_finding": claim["text"],
                "method_or_basis": "Official EuroHPC call",
                "qualification": claim["qualification"],
                "radar_relevance": "EU compute infrastructure",
                "confidence": "high",
                "why_supported": True,
            },
        },
    }
    job["job_hash"] = _job_hash(job)
    return job


def write_state(tmp_path: Path, job: dict, *, decision: str = "keep", include_drop=False):
    records = {
        job["record_key"]: {
            "profile": "deep-reader-v2-authoritative",
            "source_hash": job["source_hash"],
            "identity_hash": job["identity_hash"],
            "deep_analysis": {"main_finding": job["stored_text"]["deep_analysis"]["main_finding"], "qualification": job["stored_text"]["deep_analysis"]["qualification"]},
            "admission": {"decision": decision},
        }
    }
    admission = {"records": {job["record_key"]: {"decision": decision}}}
    if include_drop:
        records["id:dropped"] = {
            "profile": "deep-reader-v2-authoritative",
            "deep_analysis": {"main_finding": "Old finding"},
            "claims": [{"claim_id": "c:dropped:1"}],
            "admission": {"decision": "drop"},
        }
        admission["records"]["id:dropped"] = {"decision": "drop"}
    reader_path = tmp_path / "reader_text.json"
    admission_path = tmp_path / "admission_state.json"
    reader_path.write_text(json.dumps({"records": records}), encoding="utf-8")
    admission_path.write_text(json.dumps(admission), encoding="utf-8")
    return reader_path, admission_path


def write_result(tmp_path: Path, job: dict, claim: dict, *, job_hash=None):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    result = {
        "format": RESULT_FORMAT,
        "package_id": "test-package",
        "results": [{
            "record_key": job["record_key"],
            "source_hash": job["source_hash"],
            "identity_hash": job["identity_hash"],
            "job_hash": job_hash or job["job_hash"],
            "claims": [claim],
        }],
        "rejected": [],
    }
    path = inbox / "claims_backfill_results.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    return inbox, path


def test_real_job_selection_never_revives_dropped_or_stale_current_records():
    jobs = build_jobs(include_existing=True)
    assert jobs
    assert all(j["decision"] in {"keep", "review", "needs_manual_verification"} for j in jobs)
    assert all(j["era"] in {"current", "historical"} for j in jobs)
    assert all(0 <= j["merit"] <= 100 for j in jobs)
    assert all(len(j["job_hash"]) == 24 for j in jobs)
    # The repository currently has both eras in the authoritative Deep Scan store.
    assert any(j["era"] == "current" for j in jobs)
    assert any(j["era"] == "historical" for j in jobs)


def test_prepare_makes_self_contained_offline_zip(tmp_path):
    out = tmp_path / "out"
    summary = prepare(out, batch_size=2, max_records=2)
    assert summary["format"] == PACKAGE_FORMAT
    assert summary["packaged_records"] == 2
    zips = list(out.glob("*.zip"))
    assert len(zips) == 1
    with zipfile.ZipFile(zips[0]) as zf:
        names = set(zf.namelist())
        assert {"START_HERE.txt", "claims_jobs.json", "claims_vocabulary.json", "claims_backfill_results.json"} <= names
        instructions = zf.read("START_HERE.txt").decode("utf-8")
        assert "Do not browse the web" in instructions
        jobs = json.loads(zf.read("claims_jobs.json"))
        assert len(jobs["jobs"]) == 2
        assert all("stored_text" in j and "job_hash" in j for j in jobs["jobs"])


def test_import_is_atomic_and_writes_only_valid_claims(tmp_path):
    job = sample_job()
    claim = fixture_claim()
    reader_path, admission_path = write_state(tmp_path, job, include_drop=True)
    inbox, result_path = write_result(tmp_path, job, claim)
    summary = import_results(
        inbox,
        reader_path=reader_path,
        admission_path=admission_path,
        expected_jobs={job["record_key"]: job},
        vocabulary=load_vocabulary(VOCAB),
    )
    assert summary["records_imported"] == 1
    assert summary["claims_imported"] == 1
    assert summary["claims_removed_for_drop"] == 1
    assert not result_path.exists()
    reader = json.loads(reader_path.read_text(encoding="utf-8"))
    assert reader["records"][job["record_key"]]["claims"] == [claim]
    assert "claims" not in reader["records"]["id:dropped"]
    assert reader["claims_profile"] == "radar-claims-v1"


def test_import_rejects_stale_job_hash_without_touching_reader(tmp_path):
    job = sample_job()
    claim = fixture_claim()
    reader_path, admission_path = write_state(tmp_path, job)
    before = reader_path.read_bytes()
    inbox, result_path = write_result(tmp_path, job, claim, job_hash="stale")
    with pytest.raises(ValueError, match="stale or altered job_hash"):
        import_results(
            inbox,
            reader_path=reader_path,
            admission_path=admission_path,
            expected_jobs={job["record_key"]: job},
            vocabulary=load_vocabulary(VOCAB),
        )
    assert reader_path.read_bytes() == before
    assert result_path.exists()


def test_import_rejects_changed_merit_and_qualification(tmp_path):
    job = sample_job()
    claim = fixture_claim()
    claim["merit"] = claim["merit"] - 1
    claim["qualification"] = "Paraphrased instead of verbatim."
    reader_path, admission_path = write_state(tmp_path, job)
    inbox, _ = write_result(tmp_path, job, claim)
    with pytest.raises(ValueError) as exc:
        import_results(
            inbox,
            reader_path=reader_path,
            admission_path=admission_path,
            expected_jobs={job["record_key"]: job},
            vocabulary=load_vocabulary(VOCAB),
        )
    text = str(exc.value)
    assert "merit must exactly equal packaged merit" in text
    assert "qualification must copy Deep Scan qualification verbatim" in text
