#!/usr/bin/env python3
"""Strict offline Deep Scan worker-result preflight shipped in each worker ZIP.

Uses a GENERATED COPY of the *production* importer's validation function and the
production claims vocabulary/schema. This validates everything deterministically
checkable from the issued package. Live corpus state may still change after ZIP
issuance; the live importer remains final authority for identity/queue freshness.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

from claims_schema import load_vocabulary, validate_claims
from IMPORTER_RULES import validate_v2_result

ROOT = pathlib.Path(__file__).resolve().parent
DECISIONS = {"keep", "review", "drop", "defer", "drop_unverifiable"}


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def check_result(row: dict[str, Any], job: dict[str, Any], vocabulary: dict[str, Any]) -> list[str]:
    errors = []
    expected = job.get("required_output") or {}
    key = expected.get("record_key")
    for field in ("record_key", "source_hash", "identity_hash"):
        if row.get(field) != (expected if field == "record_key" else job).get(field):
            # Jobs with older required_output blocks still carry all 3 identifiers at top level.
            if row.get(field) != job.get(field):
                errors.append(f"{field} differs from assigned job")

    admission = row.get("admission") if isinstance(row.get("admission"), dict) else {}
    decision = clean(admission.get("decision")).lower()
    strand = clean(admission.get("target_strand")).upper()
    historical = job.get("corpus_scope") == "historical" or clean(key).startswith("historical:")
    # Includes the production admission + evidence-depth + retrieval-audit +
    # metadata-whitelist + duplicate-status checks, byte-for-byte at ZIP build time.
    try:
        errors.extend(validate_v2_result(
            row, key=key, current_keys={key} | {
                x.get("record_key") for x in job.get("possible_duplicates", [])
                if isinstance(x, dict) and x.get("record_key")
            },
            allowed_target_strands={"A", "B"} if historical else {"A", "B", "C"},
            current_row=job.get("automatic_scanner"),
        ))
    except Exception as exc:
        errors.append(f"importer validator raised {type(exc).__name__}: {exc}")

    du = row.get("duplicate") if isinstance(row.get("duplicate"), dict) else {}
    if clean(du.get("status")).lower() == "duplicate":
        canonical = clean(du.get("duplicate_of"))
        matches = [x for x in job.get("possible_duplicates", []) if isinstance(x, dict) and x.get("record_key") == canonical]
        if not matches or not any(x.get("reason") in ("same_doi", "exact_normalized_title") for x in matches):
            errors.append("duplicate_of is not a verified matching-DOI/exact-title canonical candidate in the package")

    # Importer's reader-text normalization rejects overlong fields. For KEEP/REVIEW,
    # the required fields would then disappear and the entire record be rejected.
    limits = {"reader_title": 18, "reader_what": 20, "reader_why": 20, "reader_more": 135}
    deep = row.get("deep_analysis") if isinstance(row.get("deep_analysis"), dict) else {}
    for field, cap in limits.items():
        value = clean(row.get(field))
        if value and len(value.split()) > cap:
            errors.append(f"{field} has {len(value.split())} words (maximum {cap})")
        if field != "reader_more" and value.endswith(("...", "…")):
            errors.append(f"{field} must not end with ellipsis")
    if row.get("reader_why") and not deep.get("why_supported"):
        errors.append("reader_why is present but deep_analysis.why_supported is false")
    if decision in ("keep", "review"):
        for field in ("reader_what", "reader_more"):
            if not clean(row.get(field)):
                errors.append(f"{field} is required for KEEP/REVIEW")
        for field in ("main_finding", "method_or_basis", "radar_relevance"):
            if not clean(deep.get(field)):
                errors.append(f"deep_analysis.{field} is required for KEEP/REVIEW")

    drafts = row.get("claims")
    if not isinstance(drafts, list):
        errors.append("claims must be a JSON array")
        return errors
    if decision in ("keep", "review") and not 1 <= len(drafts) <= 3:
        errors.append("KEEP/REVIEW requires 1–3 structured claims")
    if decision in ("drop", "defer", "drop_unverifiable") and drafts:
        errors.append(f"{decision} requires claims: []")
    if decision in ("keep", "review"):
        normalized = []
        for i, draft in enumerate(drafts, 1):
            if not isinstance(draft, dict):
                errors.append(f"claims[{i-1}] must be an object")
                continue
            item = copy.deepcopy(draft)
            system_owned = {"record_key", "claim_id", "merit", "origin", "era", "provisional"}
            provided = sorted(system_owned & set(item))
            if provided:
                errors.append(f"claims[{i-1}] includes system-managed fields (must omit): {', '.join(provided)}")
            item.update({
                "record_key": key,
                "claim_id": f"c:{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}:{i}",
                "merit": 50, # placeholder, real merit is determined by importer
                "origin": "deep_scan", "era": "historical" if historical else "current", "provisional": False,
            })
            if i == 1:
                qualifier = clean(deep.get("qualification"))
                if item.get("qualification") is not None and clean(item.get("qualification")) != qualifier:
                    errors.append("claims[0].qualification must match deep_analysis.qualification")
                item["qualification"] = qualifier
            else:
                item.setdefault("qualification", "")
            item.setdefault("secondary_objects", [])
            item.setdefault("attributes", {})
            if job.get("strand") == "B" or strand == "B":
                attrs = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
                if attrs.get("world_reasoning") is True:
                    errors.append(f"claims[{i-1}] Strand B cannot set attributes.world_reasoning=true")
                attrs["world_reasoning"] = False
                item["attributes"] = attrs
            normalized.append(item)
        if normalized:
            errors.extend(validate_claims(normalized, vocabulary))
    return errors


def validate_document(doc: Any, manifest: dict[str, Any], jobs: list[dict[str, Any]], vocabulary: dict[str, Any]) -> list[str]:
    errors = []
    if not isinstance(doc, dict):
        return ["top-level JSON must be an object"]
    if doc.get("format") != "radar-deep-scan-results-v2":
        errors.append("incorrect format")
    if doc.get("claims_format") != "radar-claims-v1":
        errors.append("incorrect claims_format")
    if doc.get("package_id") != manifest.get("package_id"):
        errors.append("package_id does not match this ZIP")
    rows = doc.get("results")
    if not isinstance(rows, list):
        return errors + ["results must be an array"]
    if not 1 <= len(rows) <= len(jobs):
        errors.append(f"expected 1..{len(jobs)} consecutive results, got {len(rows)}")
    for i, row in enumerate(rows):
        if i >= len(jobs):
            break
        if not isinstance(row, dict):
            errors.append(f"results[{i}]: not a JSON object")
            continue
        for msg in check_result(row, jobs[i], vocabulary):
            errors.append(f"results[{i}] {clean(row.get('record_key'))[:90]}: {msg}")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python CHECK_RESULTS.py deep_scan_results.json", file=sys.stderr)
        return 2
    try:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        jobs: list[dict[str, Any]] = []
        for batch in manifest["batches"]:
            jobs.extend(json.loads((ROOT / batch["file"]).read_text(encoding="utf-8"))["jobs"])
        doc = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
        vocabulary = load_vocabulary(ROOT / "claims_vocabulary.json")
        errors = validate_document(doc, manifest, jobs, vocabulary)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"FAIL: could not validate output: {exc}", file=sys.stderr)
        return 1
    if errors:
        print(f"FAIL: {len(errors)} importer-compatibility error(s). THIS JSON MUST NOT BE UPLOADED.")
        for error in errors:
            print(f" - {error}")
        return 1
    print(f"PASS: {len(doc['results'])}/{len(jobs)} consecutive results meet packaged importer and claim rules.")
    print("All worker ZIP validation passed; GitHub still checks current identities, reservations, and corpus updates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
