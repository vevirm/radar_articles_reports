import copy
import json
from pathlib import Path

import pytest

from scripts.active_corpus import apply_deep_semantics
from scripts.deep_read_works import SourceRead
from scripts.import_deep_scan_results import (
    CLAIMS_FORMAT,
    normalize_v2_claims,
    parse_result_doc,
)
from scripts.prepare_deep_scan_package import build_job

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "reasoning-reform" / "claim_fixtures.json"


def _draft():
    claim = copy.deepcopy(json.loads(FIXTURE.read_text(encoding="utf-8"))["claims"][0])
    for field in ("record_key", "claim_id", "merit", "origin", "era", "provisional"):
        claim.pop(field, None)
    return claim


def _row():
    return {
        "title": "Example verified EU programme action",
        "authors": "European Commission",
        "source": "European Commission",
        "date": "2026-07-30",
        "link": "https://commission.europa.eu/example",
        "type": "Institutional report",
        "strand": "A",
        "eu_relevance": "direct",
    }


def test_new_deep_scan_claim_draft_gets_system_owned_fields_and_validates():
    draft = _draft()
    qualification = draft["qualification"]
    raw = {"claims": [draft], "metadata_correction": {"fields": {}, "unset": []}}
    claims, problems = normalize_v2_claims(
        raw,
        key="link:https://commission.europa.eu/example",
        row=_row(),
        is_historical=False,
        strand="strand_a",
        decision="keep",
        qualification=qualification,
        claims_required=True,
    )
    assert problems == []
    assert claims and len(claims) == 1
    claim = claims[0]
    assert claim["record_key"] == "link:https://commission.europa.eu/example"
    assert claim["claim_id"].startswith("c:")
    assert claim["origin"] == "deep_scan"
    assert claim["era"] == "current"
    assert claim["provisional"] is False
    assert isinstance(claim["merit"], int) and 0 <= claim["merit"] <= 100


def test_new_deep_scan_claim_unknown_vocabulary_fails_closed():
    draft = _draft()
    draft["object"] = "invented.object"
    raw = {"claims": [draft], "metadata_correction": {"fields": {}, "unset": []}}
    _, problems = normalize_v2_claims(
        raw,
        key="link:https://commission.europa.eu/example",
        row=_row(),
        is_historical=False,
        strand="strand_a",
        decision="keep",
        qualification=draft["qualification"],
        claims_required=True,
    )
    assert any("unknown object" in p for p in problems)


def test_drop_from_new_package_must_not_carry_claims():
    draft = _draft()
    claims, problems = normalize_v2_claims(
        {"claims": [draft]},
        key="link:https://commission.europa.eu/example",
        row=_row(),
        is_historical=False,
        strand="strand_a",
        decision="drop",
        qualification="",
        claims_required=True,
    )
    assert claims == []
    assert any("must return claims: []" in p for p in problems)


def test_strand_b_claims_are_forced_out_of_world_reasoning():
    draft = _draft()
    draft["attributes"] = {}
    raw = {"claims": [draft], "metadata_correction": {"fields": {}, "unset": []}}
    claims, problems = normalize_v2_claims(
        raw,
        key="link:https://commission.europa.eu/method",
        row={**_row(), "strand": "B"},
        is_historical=False,
        strand="strand_b",
        decision="review",
        qualification=draft["qualification"],
        claims_required=True,
    )
    assert problems == []
    assert claims[0]["attributes"]["world_reasoning"] is False


def test_old_in_flight_deep_scan_package_remains_importable_without_claim_marker():
    raw = json.dumps({"format": "radar-deep-scan-results-v2", "package_id": "old", "results": []}).encode()
    doc = parse_result_doc(raw, "old.json")
    assert "claims_format" not in doc
    claims, problems = normalize_v2_claims(
        {}, key="link:https://example.org/x", row=_row(), is_historical=False,
        strand="strand_a", decision="keep", qualification="", claims_required=False,
    )
    assert claims is None and problems == []


def test_unknown_claims_format_is_rejected():
    raw = json.dumps({
        "format": "radar-deep-scan-results-v2",
        "claims_format": "future-unknown",
        "package_id": "x",
        "results": [],
    }).encode()
    with pytest.raises(ValueError, match="unsupported claims_format"):
        parse_result_doc(raw, "bad.json")


def test_deep_scan_jobs_request_claims_and_active_view_carries_them():
    row = _row()
    packed = ("strand_a", "link:https://commission.europa.eu/example", "hash", row, "pending", SourceRead("stored_only", row["link"], "", ""))
    job = build_job(packed, 1, {"records": {}}, {}, {})
    assert job["required_output"]["claims"] == []

    draft = _draft()
    claims, problems = normalize_v2_claims(
        {"claims": [draft]}, key=job["record_key"], row=row, is_historical=False,
        strand="strand_a", decision="keep", qualification=draft["qualification"], claims_required=True,
    )
    assert problems == []
    reader_entry = {
        "profile": "deep-reader-v2-authoritative",
        "reader_what": "Verified finding",
        "deep_analysis": {"main_finding": "Verified finding", "radar_relevance": "Relevant"},
        "claims": claims,
        "claims_profile": CLAIMS_FORMAT,
    }
    active = apply_deep_semantics(row, reader_entry)
    assert active["claims"] == claims
    assert active["claims"] is not claims
    assert active["claims_profile"] == CLAIMS_FORMAT
