#!/usr/bin/env python3
"""Central active-corpus policy for the Radar.

Raw scanner evidence stays in ``radar.json``.  This module creates the view that
is allowed to feed readers, rankings, exports and derived reasoning by applying:

1. validated metadata corrections;
2. authoritative Deep Scan V2 semantic interpretation;
3. admission decisions (keep/drop/review/drop_unverifiable/duplicate);
4. optional strand reclassification.

Missing admission state means ``provisional`` and remains active so the automatic
scanner can continue operating while the historical corpus is re-Deep-Scanned.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ADMISSION = ROOT / "admission_state.json"
DEFAULT_CORRECTIONS = ROOT / "record_corrections.json"
DEFAULT_READER = ROOT / "reader_text.json"

RAW_COLLECTIONS = ("strand_a", "strand_b", "strand_c", "frontier_evidence")
STRAND_KEYS = {"A": "strand_a", "B": "strand_b", "C": "strand_c"}
ACTIVE_DECISIONS = {"provisional", "keep", "review"}
INACTIVE_DECISIONS = {"drop", "drop_unverifiable", "duplicate", "needs_manual_verification"}
AUTHORITATIVE_DEEP_PROFILES = {"deep-reader-v2-authoritative"}
SAFE_CORRECTION_FIELDS = {
    "title", "authors", "source", "date", "type",
    "eu_relevance", "text_mode", "source_text_mode", "event_status",
}
SAFE_UNSET_FIELDS = (SAFE_CORRECTION_FIELDS - {"title"}) | {"source_tier"}


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def record_key(row: dict[str, Any]) -> str:
    link = clean(row.get("link") or row.get("url"))
    if link:
        return f"link:{link}"
    doi = clean(row.get("doi")).lower()
    if doi:
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
        return f"doi:{doi}"
    rid = clean(row.get("id") or row.get("record_id") or row.get("fingerprint"))
    return f"id:{rid}" if rid else ""


def _load(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return copy.deepcopy(default)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Unreadable active-corpus sidecar {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("records", {}), dict):
        raise ValueError(f"Invalid active-corpus sidecar structure: {path}")
    data.setdefault("records", {})
    return data


def load_admission(path: Path = DEFAULT_ADMISSION) -> dict[str, Any]:
    return _load(path, {"version": 1, "profile": "radar-admission-v1", "updated_at": None, "records": {}})


def load_corrections(path: Path = DEFAULT_CORRECTIONS) -> dict[str, Any]:
    return _load(path, {"version": 1, "profile": "radar-record-corrections-v1", "updated_at": None, "records": {}})


def load_reader(path: Path = DEFAULT_READER) -> dict[str, Any]:
    return _load(path, {"version": 2, "profile": "deep-reader-offline-v1", "generated_at": None, "records": {}})


def decision_for(key: str, admission: dict[str, Any]) -> dict[str, Any]:
    raw = admission.get("records", {}).get(key)
    if not isinstance(raw, dict):
        return {"decision": "provisional", "reason_code": "AWAITING_DEEP_SCAN_V2", "reason": "Not yet verified by Deep Scan V2."}
    decision = clean(raw.get("decision")).lower() or "provisional"
    if decision not in ACTIVE_DECISIONS | INACTIVE_DECISIONS:
        decision = "review"
    return {**raw, "decision": decision}


def is_active_decision(decision: str) -> bool:
    return clean(decision).lower() in ACTIVE_DECISIONS


def apply_correction(row: dict[str, Any], correction: dict[str, Any] | None) -> dict[str, Any]:
    out = copy.deepcopy(row)
    if not isinstance(correction, dict):
        return out
    fields = correction.get("fields") if isinstance(correction.get("fields"), dict) else {}
    for field, value in fields.items():
        if field in SAFE_CORRECTION_FIELDS and value not in (None, ""):
            out[field] = value
    # A corrected bibliographic source invalidates scanner-assigned source quality.
    # Do not let a former OECD/Tier-1 attribution survive behind a corrected journal
    # label and continue influencing rankings or inference. The active ranking code
    # will score the corrected provenance afresh.
    if "source" in fields:
        out.pop("source_tier", None)
        out.pop("source_merit_score", None)
    unset = correction.get("unset") if isinstance(correction.get("unset"), list) else []
    for field in unset:
        if field in SAFE_UNSET_FIELDS:
            out.pop(field, None)
    if fields or unset:
        out["metadata_corrected"] = True
        out["metadata_corrected_fields"] = sorted(k for k in fields if k in SAFE_CORRECTION_FIELDS)
        out["metadata_correction_reason"] = clean(correction.get("reason"))
        out["metadata_correction_source"] = clean(correction.get("source"))
    return out


def apply_deep_semantics(row: dict[str, Any], reader_entry: dict[str, Any] | None) -> dict[str, Any]:
    """Overlay reader text and make V2 interpretation authoritative in the active copy.

    V1 Deep Scan remains useful reader language during migration, but it does not
    replace the semantic fields used by analytical engines.  V2 does.
    """
    out = copy.deepcopy(row)
    if not isinstance(reader_entry, dict):
        return out
    for field in ("reader_title", "reader_what", "reader_why", "reader_more", "deep_read_mode", "reader_text_model", "reader_text_written_at"):
        value = reader_entry.get(field)
        if value not in (None, ""):
            out[field] = copy.deepcopy(value)
    if isinstance(reader_entry.get("deep_analysis"), dict):
        out["deep_analysis"] = copy.deepcopy(reader_entry["deep_analysis"])

    profile = clean(reader_entry.get("profile"))
    if profile not in AUTHORITATIVE_DEEP_PROFILES:
        return out

    claims = reader_entry.get("claims")
    if isinstance(claims, list) and claims:
        out["claims"] = copy.deepcopy(claims)
        out["claims_profile"] = clean(reader_entry.get("claims_profile")) or "radar-claims-v1"
    else:
        out.pop("claims", None)
        out.pop("claims_profile", None)

    # V2 is authoritative for semantics. Remove scanner-hypothesis fields that can
    # otherwise keep feeding downstream reasoning even after the prose has been
    # replaced. Derived engines may reconstruct structured lenses from the verified
    # V2 title/summary/relevance, but may not reuse the old scanner evidence arrays.
    for field in (
        "eu_evidence", "ri_evidence", "geo_evidence", "a_context_evidence",
        "a_route", "bridge_sentence", "external_eu_bridge",
        "external_eu_bridge_is_inference", "strategic_classification",
        "strategic_classification_source",
    ):
        out.pop(field, None)
    # eu_relevance is also an automatic semantic judgement. Retain it only when
    # V2 explicitly verified/corrected that field in the metadata sidecar.
    verified_metadata = set(out.get("metadata_corrected_fields") or [])
    if "eu_relevance" not in verified_metadata:
        out.pop("eu_relevance", None)

    what = clean(reader_entry.get("reader_what"))
    why = clean(reader_entry.get("reader_why"))
    more = clean(reader_entry.get("reader_more"))
    deep = reader_entry.get("deep_analysis") if isinstance(reader_entry.get("deep_analysis"), dict) else {}
    main = clean(deep.get("main_finding")) or what
    relevance = clean(deep.get("radar_relevance")) or why

    if what:
        out["what"] = what
    if main:
        out["core_message"] = main
    if more or main:
        out["summary"] = more or main
    if relevance:
        out["relevance_note"] = relevance
    else:
        out.pop("relevance_note", None)
    if why:
        out["why_it_matters"] = why
    else:
        # An unsupported WHY must not fall back to an older automatic WHY.
        out.pop("why_it_matters", None)
    out["deep_scan_authoritative"] = True
    out["semantic_source"] = "deep_scan_v2"
    return out


def build_active_document(
    raw_doc: dict[str, Any],
    *,
    admission: dict[str, Any] | None = None,
    corrections: dict[str, Any] | None = None,
    reader: dict[str, Any] | None = None,
    include_status: bool = True,
) -> dict[str, Any]:
    """Return a deep-copied active view without destructively changing raw evidence."""
    admission = admission or {"records": {}}
    corrections = corrections or {"records": {}}
    reader = reader or {"records": {}}
    out = copy.deepcopy(raw_doc)
    for key in RAW_COLLECTIONS:
        out[key] = []

    seen_target: set[tuple[str, str]] = set()
    counts = {"provisional": 0, "keep": 0, "review": 0, "drop": 0, "drop_unverifiable": 0, "duplicate": 0, "needs_manual_verification": 0}
    raw_counts: dict[str, int] = {}
    active_counts: dict[str, int] = {}
    current_keys = {
        record_key(r) for c in RAW_COLLECTIONS
        for r in (raw_doc.get(c, []) if isinstance(raw_doc.get(c), list) else [])
        if isinstance(r, dict) and record_key(r)
    }

    for source_collection in RAW_COLLECTIONS:
        rows = raw_doc.get(source_collection, []) if isinstance(raw_doc.get(source_collection), list) else []
        raw_counts[source_collection] = len(rows)
        for raw in rows:
            if not isinstance(raw, dict):
                continue
            key = record_key(raw)
            state = decision_for(key, admission)
            decision = state["decision"]
            # A duplicate suppression is safe only while its canonical record still
            # exists in the raw corpus. If retention/rotation later removes the
            # canonical row, fail open to REVIEW rather than silently losing both.
            if decision == "duplicate" and clean(state.get("duplicate_of")) not in current_keys:
                state = {**state, "decision": "review", "reason_code": "DUPLICATE_CANONICAL_MISSING", "reason": "The previously selected canonical duplicate is no longer in the current raw corpus; manual review is required."}
                decision = "review"
            counts[decision] = counts.get(decision, 0) + 1
            if not is_active_decision(decision):
                continue

            row = apply_correction(raw, corrections.get("records", {}).get(key) if key else None)
            row = apply_deep_semantics(row, reader.get("records", {}).get(key) if key else None)
            target = clean(state.get("target_strand")).upper()
            target_collection = STRAND_KEYS.get(target, source_collection)
            if source_collection == "frontier_evidence":
                target_collection = "frontier_evidence"
            dedupe_key = (target_collection, key or clean(row.get("title")))
            # Do not silently collapse legacy/provisional collisions. Existing raw
            # records can share a URL across strands or represent different sections
            # of one report. Once V2 has verified the underlying identity and target
            # strand, coalesce same-key variants into one active canonical record.
            verified_identity = clean(state.get("source")).lower() == "deep_scan_v2"
            if verified_identity and dedupe_key in seen_target:
                continue
            if verified_identity:
                seen_target.add(dedupe_key)
            if target in STRAND_KEYS and target_collection != "frontier_evidence":
                row["strand"] = target
            if include_status:
                row["admission_status"] = decision
                row["admission_reason_code"] = clean(state.get("reason_code"))
                if clean(state.get("reason")):
                    row["admission_reason"] = clean(state.get("reason"))
                if clean(state.get("duplicate_of")):
                    row["duplicate_of"] = clean(state.get("duplicate_of"))
            out.setdefault(target_collection, []).append(row)

    for key in RAW_COLLECTIONS:
        active_counts[key] = len(out.get(key, [])) if isinstance(out.get(key), list) else 0

    out["active_corpus"] = {
        "profile": "radar-active-corpus-v1",
        "raw_counts": raw_counts,
        "active_counts": active_counts,
        "decision_counts": counts,
        "review_is_active": True,
        "missing_state_is": "provisional_active",
    }
    return out


def validate_sidecars(raw_doc: dict[str, Any], admission: dict[str, Any], corrections: dict[str, Any], reader: dict[str, Any] | None = None) -> list[str]:
    problems: list[str] = []
    keys = {record_key(r) for c in RAW_COLLECTIONS for r in (raw_doc.get(c, []) if isinstance(raw_doc.get(c), list) else []) if isinstance(r, dict) and record_key(r)}
    # Admission/correction/reader sidecars are audit history as well as active state.
    # Current-signal retention may legitimately remove a raw row after it was verified,
    # so historical sidecar entries may outlive the current raw corpus. They are simply
    # ignored until/unless that exact record identity returns.
    for key, state in admission.get("records", {}).items():
        if not isinstance(state, dict):
            problems.append(f"admission entry is not an object: {key}")
            continue
        d = clean(state.get("decision")).lower()
        if d not in ACTIVE_DECISIONS | INACTIVE_DECISIONS:
            problems.append(f"invalid admission decision {d!r}: {key}")
        dup = clean(state.get("duplicate_of"))
        if dup == key:
            problems.append(f"record cannot duplicate itself: {key}")
    for key, corr in corrections.get("records", {}).items():
        if not isinstance(corr, dict):
            problems.append(f"correction entry is not an object: {key}")
            continue
        fields = corr.get("fields") if isinstance(corr.get("fields"), dict) else {}
        bad = sorted(set(fields) - SAFE_CORRECTION_FIELDS)
        if bad:
            problems.append(f"unsafe correction fields for {key}: {', '.join(bad)}")
        unset = corr.get("unset") if isinstance(corr.get("unset"), list) else []
        bad_unset = sorted(set(map(str, unset)) - SAFE_UNSET_FIELDS)
        if bad_unset:
            problems.append(f"unsafe unset fields for {key}: {', '.join(bad_unset)}")
    return problems
