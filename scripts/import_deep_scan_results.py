#!/usr/bin/env python3
"""Validate returned Deep Scan files and update the Radar's authoritative sidecars.

V1 result files remain importable for backwards compatibility, but only V2 results
can change admission/provenance or become authoritative for downstream reasoning.
Raw scanner evidence in radar.json is never deleted or rewritten here.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import time
import zipfile
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.active_corpus import (
        DEFAULT_ADMISSION, DEFAULT_CORRECTIONS, SAFE_CORRECTION_FIELDS, SAFE_UNSET_FIELDS,
        load_admission, load_corrections, validate_sidecars,
    )
    from scripts.deep_read_works import (
        CORPUS, SIDECAR, clean, identity_hash, iter_records, load_sidecar, pending, record_key, source_hash, validate,
    )
except ModuleNotFoundError:
    from active_corpus import (  # type: ignore
        DEFAULT_ADMISSION, DEFAULT_CORRECTIONS, SAFE_CORRECTION_FIELDS, SAFE_UNSET_FIELDS,
        load_admission, load_corrections, validate_sidecars,
    )
    from deep_read_works import (  # type: ignore
        CORPUS, SIDECAR, clean, identity_hash, iter_records, load_sidecar, pending, record_key, source_hash, validate,
    )

V1_FORMAT = "radar-deep-scan-results-v1"
V2_FORMAT = "radar-deep-scan-results-v2"
V1_PROFILE = "deep-reader-offline-v1"
V2_PROFILE = "deep-reader-v2-authoritative"
DECISIONS = {"keep", "drop", "review", "drop_unverifiable"}
DUPLICATE_STATUSES = {"unique", "duplicate", "review"}
TARGET_STRANDS = {"A", "B", "C"}
REQUIRED_UNVERIFIABLE_STEPS = {
    "supplied_url", "doi", "exact_title", "title_author_year",
    "official_publisher_or_repository", "broader_identity_search",
}
FORBIDDEN_EVIDENCE_DEPTHS = {"", "title_only", "search_snippet", "snippet_only", "scanner_only", "abstract_only"}
SUCCESS_OUTCOMES = {"success", "found", "matched", "recovered", "resolved"}
FAILURE_OUTCOMES = {"failed", "not_found", "no_match", "blocked", "unavailable", "not_applicable"}
ALLOWED_RECOVERED_DEPTHS = {
    "full_text_primary", "full_text_repository_copy", "official_full_document",
    "full_text_or_substantive_primary", "substantive_primary_after_recovery",
}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def parse_result_doc(raw: bytes, label: str) -> dict[str, Any]:
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"{label}: not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError(f"{label}: top level must be a JSON object")
    if obj.get("format") not in {V1_FORMAT, V2_FORMAT}:
        raise ValueError(f"{label}: format must be {V1_FORMAT!r} or {V2_FORMAT!r}")
    if not isinstance(obj.get("results"), list):
        raise ValueError(f"{label}: results must be a JSON list")
    return obj


def docs_from_file(path: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    if path.suffix.lower() == ".json":
        yield path.name, parse_result_doc(path.read_bytes(), path.name)
        return
    if path.suffix.lower() != ".zip":
        return
    with zipfile.ZipFile(path) as zf:
        candidates = [n for n in zf.namelist() if n.lower().endswith(".json") and not n.endswith("/")]
        preferred = [n for n in candidates if Path(n).name == "deep_scan_results.json"]
        names = preferred or candidates
        if not names:
            raise ValueError(f"{path.name}: ZIP contains no JSON result file")
        found = False
        errors = []
        for name in names:
            try:
                doc = parse_result_doc(zf.read(name), f"{path.name}:{name}")
            except ValueError as exc:
                errors.append(str(exc))
                continue
            found = True
            yield f"{path.name}:{name}", doc
        if not found:
            raise ValueError(f"{path.name}: no valid Deep Scan result document found. " + " | ".join(errors[:3]))


def _attempt_steps(verification: dict[str, Any]) -> set[str]:
    rows = verification.get("retrieval_attempts") if isinstance(verification.get("retrieval_attempts"), list) else []
    return {clean(x.get("step")).lower() for x in rows if isinstance(x, dict) and clean(x.get("step")) and clean(x.get("outcome"))}


def _attempt_map(verification: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = verification.get("retrieval_attempts") if isinstance(verification.get("retrieval_attempts"), list) else []
    out: dict[str, dict[str, Any]] = {}
    for x in rows:
        if not isinstance(x, dict):
            continue
        step = clean(x.get("step")).lower()
        if step and step not in out:
            out[step] = x
    return out


def _outcome(value: Any) -> str:
    return clean(value).lower().replace(" ", "_").replace("-", "_")


def _usable_sources(verification: dict[str, Any]) -> list[dict[str, Any]]:
    rows = verification.get("recovered_sources") if isinstance(verification.get("recovered_sources"), list) else []
    out = []
    for x in rows:
        if not isinstance(x, dict) or not x.get("evidence_used"):
            continue
        url = clean(x.get("url"))
        kind = clean(x.get("kind")).lower()
        if not url.startswith(("http://", "https://")):
            continue
        if kind in {"search_snippet", "snippet", "search_result"}:
            continue
        out.append(x)
    return out


def validate_v2_result(raw: dict[str, Any], *, key: str, current_keys: set[str]) -> list[str]:
    problems: list[str] = []
    verification = raw.get("verification") if isinstance(raw.get("verification"), dict) else {}
    admission = raw.get("admission") if isinstance(raw.get("admission"), dict) else {}
    duplicate = raw.get("duplicate") if isinstance(raw.get("duplicate"), dict) else {}
    correction = raw.get("metadata_correction") if isinstance(raw.get("metadata_correction"), dict) else {}

    decision = clean(admission.get("decision")).lower()
    target = clean(admission.get("target_strand")).upper()
    if decision not in DECISIONS:
        problems.append("invalid admission decision")
    if decision in {"keep", "review"} and target not in TARGET_STRANDS:
        problems.append("KEEP/REVIEW requires target_strand A/B/C")
    if not re.fullmatch(r"[A-Z0-9_\-]{3,80}", clean(admission.get("reason_code")).upper()):
        problems.append("missing/invalid admission reason_code")
    if len(clean(admission.get("reason"))) < 12:
        problems.append("admission reason is too thin")

    identity_verified = bool(verification.get("identity_verified"))
    depth = clean(verification.get("evidence_depth")).lower()
    usable = _usable_sources(verification)
    attempts = verification.get("retrieval_attempts") if isinstance(verification.get("retrieval_attempts"), list) else []
    attempt_steps = _attempt_steps(verification)
    audit_by_step = _attempt_map(verification)
    if "supplied_url" not in attempt_steps:
        problems.append("verification must report the supplied_url retrieval attempt")
    if len(clean(verification.get("verification_note"))) < 12:
        problems.append("verification_note is too thin")
    if decision == "drop_unverifiable":
        if identity_verified:
            problems.append("drop_unverifiable requires identity_verified=false")
        missing = REQUIRED_UNVERIFIABLE_STEPS - attempt_steps
        if missing:
            problems.append("drop_unverifiable missing retrieval steps: " + ",".join(sorted(missing)))
        thin = [step for step in REQUIRED_UNVERIFIABLE_STEPS if step in audit_by_step and len(clean(audit_by_step[step].get("note"))) < 12]
        if thin:
            problems.append("drop_unverifiable retrieval steps need specific audit notes (12+ chars): " + ",".join(sorted(thin)))
        success_steps = [step for step in REQUIRED_UNVERIFIABLE_STEPS if step in audit_by_step and _outcome(audit_by_step[step].get("outcome")) in SUCCESS_OUTCOMES]
        if success_steps:
            problems.append("drop_unverifiable cannot report a successful recovery step: " + ",".join(sorted(success_steps)))
        distinct_notes = {clean(audit_by_step[s].get("note")).lower() for s in REQUIRED_UNVERIFIABLE_STEPS if s in audit_by_step}
        if len(distinct_notes) < 4:
            problems.append("drop_unverifiable retrieval audit is too repetitive; record what was actually tried at each step")
        if usable:
            problems.append("drop_unverifiable cannot simultaneously cite substantive recovered evidence")
    else:
        if not identity_verified:
            problems.append("recovered-work decision requires identity_verified=true")
        if depth in FORBIDDEN_EVIDENCE_DEPTHS or depth not in ALLOWED_RECOVERED_DEPTHS:
            problems.append("evidence depth must be one of the authoritative recovered-source levels")
        if depth == "substantive_primary_after_recovery":
            missing = REQUIRED_UNVERIFIABLE_STEPS - attempt_steps
            if missing:
                problems.append("substantive_primary_after_recovery requires the full retrieval ladder: " + ",".join(sorted(missing)))
        if not usable:
            problems.append("recovered-work decision requires at least one substantive recovered source")
        supplied = audit_by_step.get("supplied_url", {})
        supplied_outcome = _outcome(supplied.get("outcome"))
        if supplied_outcome and supplied_outcome not in SUCCESS_OUTCOMES:
            recovery_steps = {"doi", "exact_title", "title_author_year", "official_publisher_or_repository", "broader_identity_search"}
            successful_recovery = [s for s in recovery_steps if s in audit_by_step and _outcome(audit_by_step[s].get("outcome")) in SUCCESS_OUTCOMES]
            if not successful_recovery:
                problems.append("supplied URL did not recover the work; recovered-work decision must report which recovery-ladder step actually found it")

    dup_status = clean(duplicate.get("status")).lower() or "unique"
    if dup_status not in DUPLICATE_STATUSES:
        problems.append("invalid duplicate status")
    dup_of = clean(duplicate.get("duplicate_of"))
    if dup_status == "duplicate":
        if decision != "drop":
            problems.append("confirmed duplicate must use admission decision drop")
        if not dup_of or dup_of == key or dup_of not in current_keys:
            problems.append("confirmed duplicate requires an existing canonical duplicate_of key")
    elif dup_of:
        problems.append("duplicate_of must be blank unless duplicate.status=duplicate")

    fields = correction.get("fields") if isinstance(correction.get("fields"), dict) else {}
    bad_fields = sorted(set(fields) - SAFE_CORRECTION_FIELDS)
    if bad_fields:
        problems.append("unsafe metadata correction fields: " + ",".join(bad_fields))
    unset = correction.get("unset") if isinstance(correction.get("unset"), list) else []
    bad_unset = sorted(set(map(str, unset)) - SAFE_UNSET_FIELDS)
    if bad_unset:
        problems.append("unsafe metadata unset fields: " + ",".join(bad_unset))
    if fields or unset:
        if len(clean(correction.get("reason"))) < 12:
            problems.append("metadata correction requires an evidence-grounded reason")
        if not usable:
            problems.append("metadata correction requires a substantive recovered source")
    return problems




def _doi(row: dict[str, Any]) -> str:
    value = clean(row.get("doi"))
    if not value:
        link = clean(row.get("link") or row.get("url"))
        m = re.search(r"doi\.org/(10\.\d{4,9}/[^?#\s]+)", link, re.I)
        value = m.group(1) if m else ""
    return re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I).lower().rstrip("/")


def _norm_title(row: dict[str, Any]) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(row.get("title") or row.get("headline")).lower()).strip()


def high_confidence_duplicate(a: dict[str, Any], b: dict[str, Any]) -> bool:
    ad, bd = _doi(a), _doi(b)
    if ad and bd and ad == bd:
        return True
    at, bt = _norm_title(a), _norm_title(b)
    return bool(at and bt and len(at) >= 24 and at == bt)

def _legacy_snapshot(entry: dict[str, Any]) -> dict[str, Any]:
    snap = copy.deepcopy(entry)
    snap.pop("legacy_versions", None)
    return snap


def main() -> None:
    ap = argparse.ArgumentParser(description="Import returned offline Deep Scan results")
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--sidecar", type=Path, default=SIDECAR)
    ap.add_argument("--admission", type=Path, default=None)
    ap.add_argument("--corrections", type=Path, default=None)
    ap.add_argument("--inbox", type=Path, default=Path("deep_scan_inbox"))
    ap.add_argument("--files", nargs="*", type=Path, default=None)
    args = ap.parse_args()

    if args.admission is None:
        args.admission = args.corpus.parent / "admission_state.json"
    if args.corrections is None:
        args.corrections = args.corpus.parent / "record_corrections.json"
    doc = json.loads(args.corpus.read_text(encoding="utf-8"))
    sidecar = load_sidecar(args.sidecar)
    admission_state = load_admission(args.admission)
    corrections = load_corrections(args.corrections)
    current: dict[str, tuple[str, dict[str, Any], str, str]] = {}
    for strand, row in iter_records(doc):
        key = record_key(row)
        if key:
            current[key] = (strand, row, source_hash(row), identity_hash(row))
    current_keys = set(current)

    files = [p for p in args.files if p.exists()] if args.files else sorted(
        p for p in args.inbox.glob("*") if p.is_file() and p.name != ".gitkeep" and p.suffix.lower() in {".json", ".zip"}
    )
    if not files:
        print("No Deep Scan result files found in inbox.")
        return

    table = sidecar.setdefault("records", {})
    # Deep Scan V2 is deliberately FIFO. The package builder exposes the head of
    # this same queue; enforce a consecutive prefix at import time so an LLM cannot
    # skip a difficult earlier record and return only easier later records. Partial
    # completion remains safe: a result file may stop after any valid prefix.
    expected_v2_queue = [item[1] for item in pending(doc, sidecar)]
    expected_v2_pos = 0
    admit_table = admission_state.setdefault("records", {})
    corr_table = corrections.setdefault("records", {})
    avoid_whys = [clean(v.get("reader_why")) for v in table.values() if isinstance(v, dict) and clean(v.get("reader_why"))]
    accepted_v1 = accepted_v2 = rejected_count = duplicate_count = stale_count = 0
    seen_pairs: set[tuple[str, str, str]] = set()
    imported_files: list[Path] = []
    file_failures: list[str] = []

    for path in files:
        file_had_valid_doc = False
        try:
            docs = list(docs_from_file(path))
        except Exception as exc:
            file_failures.append(f"{path.name}: {clean(exc)}")
            continue
        for label, result_doc in docs:
            file_had_valid_doc = True
            fmt = result_doc.get("format")
            package_id = clean(result_doc.get("package_id")) or "unknown-package"
            for idx, raw in enumerate(result_doc.get("results", []), 1):
                if not isinstance(raw, dict):
                    print(f"REJECT {label} result {idx}: result is not an object")
                    rejected_count += 1
                    continue
                key = clean(raw.get("record_key"))
                h = clean(raw.get("source_hash"))
                ih = clean(raw.get("identity_hash"))
                if not key or not h:
                    print(f"REJECT {label} result {idx}: missing record_key/source_hash")
                    rejected_count += 1
                    continue
                cur = current.get(key)
                if not cur:
                    print(f"REJECT {label} result {idx}: record no longer exists: {key[:100]}")
                    rejected_count += 1
                    continue
                strand, _row, current_hash, current_identity_hash = cur
                pair = (key, h, fmt)
                if pair in seen_pairs:
                    duplicate_count += 1
                    continue
                seen_pairs.add(pair)

                existing = table.get(key)
                if isinstance(existing, dict) and existing.get("profile") == V2_PROFILE:
                    duplicate_count += 1
                    continue

                if fmt == V2_FORMAT:
                    expected_key = expected_v2_queue[expected_v2_pos] if expected_v2_pos < len(expected_v2_queue) else ""
                    if key != expected_key:
                        print(
                            f"REJECT {label} result {idx}: out of FIFO order. Next required record is "
                            f"{expected_key[:120] if expected_key else '[none pending]'}"
                        )
                        rejected_count += 1
                        # Stop this result document here. A carefully completed prefix
                        # above remains imported; later/easier records must wait until
                        # the skipped record has been dealt with.
                        break

                if fmt == V1_FORMAT:
                    if h != current_hash:
                        print(f"STALE {label} result {idx}: scanner material changed since V1 package creation")
                        stale_count += 1
                        continue
                    normalized = {
                        "reader_title": raw.get("reader_title"), "reader_what": raw.get("reader_what"),
                        "reader_why": raw.get("reader_why"), "reader_more": raw.get("reader_more"),
                        "deep_analysis": raw.get("deep_analysis"),
                    }
                    accepted, problems = validate(normalized, avoid_whys)
                    if not accepted.get("reader_what"):
                        print(f"REJECT {label} result {idx}: no valid reader_what ({'; '.join(problems)})")
                        rejected_count += 1
                        continue
                    now = utc_now()
                    table[key] = {
                        "profile": V1_PROFILE, "strand": strand, "source_hash": h, **accepted,
                        "deep_read_mode": "offline_llm_package", "reader_text_model": clean(raw.get("processor")) or "user-provided-llm-subscription",
                        "reader_text_written_at": now, "deep_scan_package_id": package_id,
                    }
                    if table[key].get("reader_why"):
                        avoid_whys.append(table[key]["reader_why"])
                    accepted_v1 += 1
                    continue

                # V2 uses a stable identity hash. Automatic scanner wording may change while
                # a careful package is being worked, but the record identity may not.
                if not ih or ih != current_identity_hash:
                    print(f"STALE {label} result {idx}: record identity no longer matches exported V2 job")
                    stale_count += 1
                    continue
                v2_problems = validate_v2_result(raw, key=key, current_keys=current_keys)
                dup = raw.get("duplicate") if isinstance(raw.get("duplicate"), dict) else {}
                dup_of = clean(dup.get("duplicate_of"))
                if clean(dup.get("status")).lower() == "duplicate" and dup_of in current:
                    if not high_confidence_duplicate(_row, current[dup_of][1]):
                        v2_problems.append("duplicate relation is not independently high-confidence (same DOI or exact normalized title)")
                if v2_problems:
                    print(f"REJECT {label} result {idx}: {'; '.join(v2_problems)}")
                    rejected_count += 1
                    continue

                normalized = {
                    "reader_title": raw.get("reader_title"), "reader_what": raw.get("reader_what"),
                    "reader_why": raw.get("reader_why"), "reader_more": raw.get("reader_more"),
                    "deep_analysis": raw.get("deep_analysis"),
                }
                accepted, prose_problems = validate(normalized, avoid_whys)
                decision = clean((raw.get("admission") or {}).get("decision")).lower()
                if decision in {"keep", "review"}:
                    deep_ok = accepted.get("deep_analysis") if isinstance(accepted.get("deep_analysis"), dict) else {}
                    missing_active = []
                    if not accepted.get("reader_what"): missing_active.append("reader_what")
                    if not accepted.get("reader_more"): missing_active.append("reader_more")
                    if not clean(deep_ok.get("main_finding")): missing_active.append("deep_analysis.main_finding")
                    if not clean(deep_ok.get("method_or_basis")): missing_active.append("deep_analysis.method_or_basis")
                    if not clean(deep_ok.get("radar_relevance")): missing_active.append("deep_analysis.radar_relevance")
                    if missing_active:
                        print(f"REJECT {label} result {idx}: active V2 result is not deep enough; missing {', '.join(missing_active)} ({'; '.join(prose_problems)})")
                        rejected_count += 1
                        continue

                now = utc_now()
                previous = table.get(key) if isinstance(table.get(key), dict) else None
                legacy_versions = []
                if previous:
                    legacy_versions = list(previous.get("legacy_versions", [])) if isinstance(previous.get("legacy_versions"), list) else []
                    legacy_versions.append(_legacy_snapshot(previous))
                    legacy_versions = legacy_versions[-3:]
                entry = {
                    "profile": V2_PROFILE, "strand": strand, "source_hash": h, "identity_hash": ih,
                    **accepted, "verification": copy.deepcopy(raw.get("verification")),
                    "admission": copy.deepcopy(raw.get("admission")), "duplicate": copy.deepcopy(raw.get("duplicate")),
                    "deep_read_mode": "offline_llm_package_v2", "reader_text_model": clean(raw.get("processor")) or "user-provided-llm-subscription",
                    "reader_text_written_at": now, "deep_scan_package_id": package_id,
                }
                if legacy_versions:
                    entry["legacy_versions"] = legacy_versions
                table[key] = entry
                if entry.get("reader_why"):
                    avoid_whys.append(entry["reader_why"])

                adm = raw.get("admission") or {}
                dup = raw.get("duplicate") or {}
                sidecar_decision = "duplicate" if clean(dup.get("status")).lower() == "duplicate" else decision
                admit_table[key] = {
                    "decision": sidecar_decision,
                    "target_strand": clean(adm.get("target_strand")).upper(),
                    "reason_code": clean(adm.get("reason_code")).upper(),
                    "reason": clean(adm.get("reason")),
                    "source": "deep_scan_v2",
                    "updated_at": now,
                    "deep_scan_package_id": package_id,
                    "verification_note": clean((raw.get("verification") or {}).get("verification_note")),
                    "duplicate_of": clean(dup.get("duplicate_of")) if clean(dup.get("status")).lower() == "duplicate" else "",
                }
                correction = raw.get("metadata_correction") if isinstance(raw.get("metadata_correction"), dict) else {}
                fields = correction.get("fields") if isinstance(correction.get("fields"), dict) else {}
                unset = correction.get("unset") if isinstance(correction.get("unset"), list) else []
                if fields or unset:
                    corr_table[key] = {
                        "fields": copy.deepcopy(fields), "unset": list(unset),
                        "reason_code": "DEEP_SCAN_V2_METADATA_CORRECTION",
                        "reason": clean(correction.get("reason")), "source": "deep_scan_v2",
                        "evidence": [clean(x.get("url")) for x in _usable_sources(raw.get("verification") or {}) if clean(x.get("url"))],
                        "updated_at": now, "deep_scan_package_id": package_id,
                    }
                accepted_v2 += 1
                expected_v2_pos += 1
                if prose_problems:
                    print(f"ACCEPT {label} result {idx} with prose safeguards: {'; '.join(prose_problems)}")
        if file_had_valid_doc:
            imported_files.append(path)

    if file_failures:
        print("Invalid result files:")
        for x in file_failures:
            print(" -", x)
        raise SystemExit(2)

    total_accepted = accepted_v1 + accepted_v2
    if total_accepted:
        now = utc_now()
        sidecar["version"] = 3
        sidecar["profile"] = V2_PROFILE if accepted_v2 else sidecar.get("profile", V1_PROFILE)
        sidecar["generated_at"] = now
        admission_state["version"] = 1
        admission_state["profile"] = "radar-admission-v1"
        admission_state["updated_at"] = now
        corrections["version"] = 1
        corrections["profile"] = "radar-record-corrections-v1"
        corrections["updated_at"] = now
        sidecar_problems = validate_sidecars(doc, admission_state, corrections, sidecar)
        if sidecar_problems:
            raise SystemExit("Refusing to write invalid active-corpus sidecars: " + " | ".join(sidecar_problems[:8]))
        args.sidecar.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.admission.write_text(json.dumps(admission_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.corrections.write_text(json.dumps(corrections, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for path in imported_files:
        try:
            path.unlink()
        except OSError as exc:
            raise SystemExit(f"Imported results but could not remove inbox file {path}: {exc}") from exc

    print(
        f"Deep Scan import: V2 accepted {accepted_v2}; legacy V1 accepted {accepted_v1}; "
        f"stale {stale_count}; rejected {rejected_count}; duplicates {duplicate_count}."
    )
    print("Raw radar.json evidence was not deleted. V2 admission/corrections are stored in sidecars for active-corpus rebuild.")


if __name__ == "__main__":
    main()
