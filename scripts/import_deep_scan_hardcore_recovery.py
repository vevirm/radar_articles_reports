#!/usr/bin/env python3
"""Import terminal PUSH HARDER Deep Scan recovery results.

Recovered evidence is validated with the existing protected Deep Scan V2 validator.
The only special terminal policy is that, after the much stronger recovery audit has
been exhausted, an identity-confirmed but substantively inaccessible work may be
closed as DROP_UNVERIFIABLE instead of returning to a human/manual queue.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import time
import zipfile
from pathlib import Path
from typing import Any

try:
    from scripts.active_corpus import (
        DEFAULT_ADMISSION, DEFAULT_CORRECTIONS, SAFE_CORRECTION_FIELDS, SAFE_UNSET_FIELDS,
        load_admission, load_corrections, validate_sidecars,
    )
    from scripts.claims_schema import validate_claims
    from scripts.deep_read_works import (
        CORPUS, SIDECAR, clean, identity_hash, iter_historical_records, iter_records,
        historical_pending, load_sidecar, pending, record_key, source_hash, validate,
    )
    from scripts.deep_scan_work_state import (
        DEFAULT_WORK_STATE, load_state, manual_verification_keys, mark_verified, save_state,
        sync_verified, update_record_metadata, write_status_markdown,
    )
    from scripts.import_deep_scan_results import (
        CLAIMS_FORMAT, V2_PROFILE, high_confidence_duplicate, normalize_v2_claims,
        validate_v2_result, _usable_sources,
    )
    from scripts.prepare_deep_scan_hardcore_recovery import HARDCORE_ROUTES
except ModuleNotFoundError:
    from active_corpus import (  # type: ignore
        DEFAULT_ADMISSION, DEFAULT_CORRECTIONS, SAFE_CORRECTION_FIELDS, SAFE_UNSET_FIELDS,
        load_admission, load_corrections, validate_sidecars,
    )
    from claims_schema import validate_claims  # type: ignore
    from deep_read_works import (  # type: ignore
        CORPUS, SIDECAR, clean, identity_hash, iter_historical_records, iter_records,
        historical_pending, load_sidecar, pending, record_key, source_hash, validate,
    )
    from deep_scan_work_state import (  # type: ignore
        DEFAULT_WORK_STATE, load_state, manual_verification_keys, mark_verified, save_state,
        sync_verified, update_record_metadata, write_status_markdown,
    )
    from import_deep_scan_results import (  # type: ignore
        CLAIMS_FORMAT, V2_PROFILE, high_confidence_duplicate, normalize_v2_claims,
        validate_v2_result, _usable_sources,
    )
    from prepare_deep_scan_hardcore_recovery import HARDCORE_ROUTES  # type: ignore

RESULT_FORMAT = "radar-deep-scan-results-v2"
RECOVERY_MODE = "hardcore-terminal-v1"
REQUIRED_NORMAL_STEPS = {
    "supplied_url", "doi", "exact_title", "title_author_year",
    "official_publisher_or_repository", "broader_identity_search",
}
ROUTE_OUTCOMES = {"completed", "success", "found", "recovered", "failed", "not_found", "blocked", "unavailable", "not_applicable", "no_match"}
EXHAUSTED_DEPTHS = {"identity_only_after_hardcore_recovery", "unverified_after_hardcore_recovery"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def docs_from_file(path: Path):
    if path.suffix.lower() == ".json":
        yield path.name, json.loads(path.read_text(encoding="utf-8"))
        return
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".json") and not n.endswith("/")]
            preferred = [n for n in names if Path(n).name in {"deep_scan_hardcore_results.json", "deep_scan_results.json"}]
            for name in preferred or names:
                try:
                    doc = json.loads(zf.read(name).decode("utf-8"))
                except Exception:
                    continue
                if isinstance(doc, dict) and doc.get("recovery_mode") == RECOVERY_MODE:
                    yield f"{path.name}:{name}", doc
                    return
        raise ValueError(f"{path.name}: no {RECOVERY_MODE} result JSON found")
    raise ValueError(f"Unsupported result file {path}")


def _route_map(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    hc = raw.get("hardcore_recovery") if isinstance(raw.get("hardcore_recovery"), dict) else {}
    rows = hc.get("routes") if isinstance(hc.get("routes"), list) else []
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        route = clean(row.get("route")).lower()
        if route and route not in out:
            out[route] = row
    return out


def _normal_attempt_steps(raw: dict[str, Any]) -> set[str]:
    verification = raw.get("verification") if isinstance(raw.get("verification"), dict) else {}
    rows = verification.get("retrieval_attempts") if isinstance(verification.get("retrieval_attempts"), list) else []
    return {clean(x.get("step")).lower() for x in rows if isinstance(x, dict) and clean(x.get("step"))}




def _scanner_validation_route_url(row: dict[str, Any] | None) -> str:
    row = row if isinstance(row, dict) else {}
    access = row.get("source_access") if isinstance(row.get("source_access"), dict) else {}
    url = clean(row.get("source_validation_url") or access.get("validation_url") or row.get("ep_document_pdf") or access.get("document_pdf"))
    if url:
        return url
    celex = clean(row.get("celex") or access.get("celex"))
    return ("https://publications.europa.eu/resource/celex/" + celex) if celex else ""


def validate_hardcore_audit(raw: dict[str, Any], *, exhausted: bool, current_row: dict[str, Any] | None = None) -> list[str]:
    problems: list[str] = []
    hc = raw.get("hardcore_recovery") if isinstance(raw.get("hardcore_recovery"), dict) else {}
    if not hc:
        return ["missing hardcore_recovery audit"]
    routes = _route_map(raw)
    if exhausted:
        missing = [r for r in HARDCORE_ROUTES if r not in routes]
        if missing:
            problems.append("hardcore recovery missing route categories: " + ",".join(missing))
        for route in HARDCORE_ROUTES:
            row = routes.get(route)
            if not row:
                continue
            outcome = clean(row.get("outcome")).lower().replace(" ", "_").replace("-", "_")
            if outcome not in ROUTE_OUTCOMES:
                problems.append(f"hardcore route {route} has invalid outcome")
            if len(clean(row.get("query_or_url"))) < 4:
                problems.append(f"hardcore route {route} missing concrete query/url/identifier")
            if len(clean(row.get("note"))) < 18:
                problems.append(f"hardcore route {route} audit note is too thin")
        if not bool(hc.get("all_routes_exhausted")):
            problems.append("drop_unverifiable requires hardcore_recovery.all_routes_exhausted=true")
        if len(clean(hc.get("terminal_reason"))) < 24:
            problems.append("drop_unverifiable requires a specific terminal_reason")
        passes = hc.get("try_harder_passes") if isinstance(hc.get("try_harder_passes"), list) else []
        by_num = {int(p.get("pass")): p for p in passes if isinstance(p, dict) and str(p.get("pass", "")).isdigit()}
        for n, minimum_new in ((1, 3), (2, 2)):
            p = by_num.get(n)
            if not p:
                problems.append(f"missing TRY HARDER pass {n}")
                continue
            new = p.get("new_routes_identified") if isinstance(p.get("new_routes_identified"), list) else []
            actions = p.get("actions_taken") if isinstance(p.get("actions_taken"), list) else []
            if len([x for x in new if len(clean(x)) >= 6]) < minimum_new:
                problems.append(f"TRY HARDER pass {n} needs at least {minimum_new} genuinely new retrieval ideas")
            if len([x for x in actions if len(clean(x)) >= 10]) < minimum_new:
                problems.append(f"TRY HARDER pass {n} did not execute enough concrete new actions")
            if len(clean(p.get("result"))) < 18:
                problems.append(f"TRY HARDER pass {n} result is too thin")
        required_normal_steps = set(REQUIRED_NORMAL_STEPS)
        if _scanner_validation_route_url(current_row):
            required_normal_steps.add("scanner_validation_route")
        missing_normal = required_normal_steps - _normal_attempt_steps(raw)
        if missing_normal:
            problems.append("terminal recovery missing original Deep Scan retrieval steps: " + ",".join(sorted(missing_normal)))
    else:
        # A recovered result may stop as soon as substantive matching evidence is found,
        # but it must show at least one meaningful recovery action beyond merely restating the old failure.
        if not routes:
            problems.append("recovered result missing hardcore recovery audit")
    return problems


def _empty_deep(qualification: str = "") -> dict[str, Any]:
    return {
        "work_kind": "",
        "research_question": "",
        "main_finding": "",
        "method_or_basis": "",
        "qualification": qualification,
        "radar_relevance": "",
        "confidence": "low",
        "why_supported": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Import terminal PUSH HARDER Deep Scan results")
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--historical", type=Path, default=None)
    ap.add_argument("--sidecar", type=Path, default=SIDECAR)
    ap.add_argument("--admission", type=Path, default=None)
    ap.add_argument("--corrections", type=Path, default=None)
    ap.add_argument("--work-state", type=Path, default=DEFAULT_WORK_STATE)
    ap.add_argument("--inbox", type=Path, default=Path("deep_scan_hardcore_inbox"))
    ap.add_argument("--status-file", type=Path, default=Path("DEEP_SCAN_STATUS.md"))
    args = ap.parse_args()
    if args.historical is None:
        args.historical = args.corpus.parent / "historical" / "historical.json"
    if args.admission is None:
        args.admission = args.corpus.parent / "admission_state.json"
    if args.corrections is None:
        args.corrections = args.corpus.parent / "record_corrections.json"

    doc = json.loads(args.corpus.read_text(encoding="utf-8"))
    historical: dict[str, Any] = {}
    if args.historical.exists():
        loaded = json.loads(args.historical.read_text(encoding="utf-8"))
        historical = loaded if isinstance(loaded, dict) else {}
    sidecar = load_sidecar(args.sidecar)
    admission_state = load_admission(args.admission)
    corrections = load_corrections(args.corrections)
    work_state = load_state(args.work_state)
    sync_verified(work_state, sidecar)

    current: dict[str, tuple[str, dict[str, Any], str, str]] = {}
    for strand, row in iter_records(doc):
        key = record_key(row)
        if key:
            current[key] = (strand, row, source_hash(row), identity_hash(row))
    for strand, row in iter_historical_records(historical):
        key = record_key(row)
        if key:
            current[key] = (strand, row, source_hash(row), identity_hash(row))
    for key, (_s, row, _h, _ih) in current.items():
        update_record_metadata(work_state, key, row)

    files = sorted(p for p in args.inbox.glob("*") if p.is_file() and p.name != ".gitkeep" and p.suffix.lower() in {".json", ".zip"})
    if not files:
        print("No terminal recovery result files found.")
        return

    table = sidecar.setdefault("records", {})
    admit_table = admission_state.setdefault("records", {})
    corr_table = corrections.setdefault("records", {})
    manual = manual_verification_keys(work_state)
    current_keys = set(current)
    avoid_whys = [clean(v.get("reader_why")) for v in table.values() if isinstance(v, dict) and clean(v.get("reader_why"))]
    accepted = exhausted_count = rejected = stale = 0
    imported_files: list[Path] = []

    for path in files:
        had_doc = False
        for label, result_doc in docs_from_file(path):
            had_doc = True
            if result_doc.get("format") != RESULT_FORMAT or result_doc.get("recovery_mode") != RECOVERY_MODE:
                print(f"REJECT {label}: wrong format/recovery_mode")
                rejected += 1
                continue
            for idx, raw in enumerate(result_doc.get("results", []), 1):
                if not isinstance(raw, dict):
                    print(f"REJECT {label} result {idx}: not an object")
                    rejected += 1
                    continue
                key = clean(raw.get("record_key"))
                if key not in current:
                    print(f"REJECT {label} result {idx}: record missing from current corpus")
                    rejected += 1
                    continue
                if key not in manual:
                    print(f"REJECT {label} result {idx}: record is not currently in terminal recovery state")
                    rejected += 1
                    continue
                strand, row, cur_hash, cur_ih = current[key]
                if clean(raw.get("source_hash")) != cur_hash or clean(raw.get("identity_hash")) != cur_ih:
                    print(f"STALE {label} result {idx}: source/identity hash changed")
                    stale += 1
                    continue
                admission = raw.get("admission") if isinstance(raw.get("admission"), dict) else {}
                decision = clean(admission.get("decision")).lower()
                if decision == "defer":
                    print(f"REJECT {label} result {idx}: DEFER is forbidden in terminal recovery")
                    rejected += 1
                    continue
                is_historical = strand.startswith("historical_")
                allowed = {"A", "B"} if is_historical else {"A", "B", "C"}

                if decision == "drop_unverifiable":
                    problems = validate_hardcore_audit(raw, exhausted=True, current_row=row)
                    verification = raw.get("verification") if isinstance(raw.get("verification"), dict) else {}
                    depth = clean(verification.get("evidence_depth")).lower()
                    if depth not in EXHAUSTED_DEPTHS:
                        problems.append("terminal drop_unverifiable requires hardcore evidence_depth")
                    if _usable_sources(verification):
                        problems.append("terminal drop_unverifiable cannot cite substantive evidence_used sources")
                    if any(clean(raw.get(x)) for x in ("reader_title", "reader_what", "reader_why", "reader_more")):
                        problems.append("terminal drop_unverifiable must not invent reader interpretation")
                    if raw.get("claims") not in (None, []):
                        problems.append("terminal drop_unverifiable requires claims: []")
                    corr = raw.get("metadata_correction") if isinstance(raw.get("metadata_correction"), dict) else {}
                    if (corr.get("fields") if isinstance(corr.get("fields"), dict) else {}) or (corr.get("unset") if isinstance(corr.get("unset"), list) else []):
                        problems.append("terminal drop_unverifiable must not apply metadata corrections")
                    if problems:
                        print(f"REJECT {label} result {idx}: " + "; ".join(problems))
                        rejected += 1
                        continue
                    now = utc_now()
                    stored_strand = strand.rsplit("_", 1)[-1].upper() if is_historical else ("A" if strand == "frontier_evidence" else strand.replace("strand_", "").upper())
                    reason = clean(admission.get("reason")) or clean((raw.get("hardcore_recovery") or {}).get("terminal_reason"))
                    verification_copy = copy.deepcopy(verification)
                    verification_copy["hardcore_recovery"] = copy.deepcopy(raw.get("hardcore_recovery"))
                    table[key] = {
                        "profile": V2_PROFILE,
                        "strand": stored_strand,
                        "corpus_scope": "historical" if is_historical else "main",
                        "source_hash": cur_hash,
                        "identity_hash": cur_ih,
                        "deep_analysis": _empty_deep("Substantive evidence could not be recovered after exhaustive terminal recovery."),
                        "verification": verification_copy,
                        "admission": {
                            "decision": "drop_unverifiable",
                            "target_strand": "",
                            "reason_code": "EVIDENCE_ACCESS_EXHAUSTED",
                            "reason": reason or "Substantive evidence remained inaccessible after the complete PUSH HARDER recovery protocol.",
                        },
                        "duplicate": {"status": "unique", "duplicate_of": "", "reason": ""},
                        "claims": [],
                        "claims_profile": CLAIMS_FORMAT,
                        "deep_read_mode": "offline_llm_hardcore_terminal_recovery",
                        "reader_text_model": clean(raw.get("processor")) or "user-provided-llm-subscription",
                        "reader_text_written_at": now,
                        "deep_scan_package_id": clean(result_doc.get("package_id")) or "hardcore-terminal",
                    }
                    admit_table[key] = {
                        "decision": "drop_unverifiable",
                        "target_strand": "",
                        "reason_code": "EVIDENCE_ACCESS_EXHAUSTED",
                        "reason": reason or "Substantive evidence remained inaccessible after the complete PUSH HARDER recovery protocol.",
                        "source": "deep_scan_hardcore_terminal",
                        "corpus_scope": "historical" if is_historical else "main",
                        "updated_at": now,
                        "deep_scan_package_id": clean(result_doc.get("package_id")) or "hardcore-terminal",
                        "verification_note": clean(verification.get("verification_note")),
                    }
                    mark_verified(work_state, key, clean(result_doc.get("package_id")) or "hardcore-terminal", when=now)
                    manual.discard(key)
                    accepted += 1
                    exhausted_count += 1
                    print(f"ACCEPT terminal DROP_UNVERIFIABLE {label} result {idx}: exhaustive recovery completed")
                    continue

                # Any recovered KEEP/REVIEW/DROP must satisfy the unchanged protected V2 validator.
                problems = validate_hardcore_audit(raw, exhausted=False)
                problems.extend(validate_v2_result(raw, key=key, current_keys=current_keys, allowed_target_strands=allowed))
                dup = raw.get("duplicate") if isinstance(raw.get("duplicate"), dict) else {}
                dup_of = clean(dup.get("duplicate_of"))
                if clean(dup.get("status")).lower() == "duplicate" and dup_of in current:
                    if not high_confidence_duplicate(row, current[dup_of][1]):
                        problems.append("duplicate relation is not independently high-confidence")
                if problems:
                    print(f"REJECT {label} result {idx}: " + "; ".join(problems))
                    rejected += 1
                    continue

                normalized, prose_problems = validate({
                    "reader_title": raw.get("reader_title"),
                    "reader_what": raw.get("reader_what"),
                    "reader_why": raw.get("reader_why"),
                    "reader_more": raw.get("reader_more"),
                    "deep_analysis": raw.get("deep_analysis"),
                }, avoid_whys)
                deep_ok = normalized.get("deep_analysis") if isinstance(normalized.get("deep_analysis"), dict) else {}
                if decision in {"keep", "review"}:
                    missing = []
                    if not normalized.get("reader_what"): missing.append("reader_what")
                    if not normalized.get("reader_more"): missing.append("reader_more")
                    if not clean(deep_ok.get("main_finding")): missing.append("deep_analysis.main_finding")
                    if not clean(deep_ok.get("method_or_basis")): missing.append("deep_analysis.method_or_basis")
                    if not clean(deep_ok.get("radar_relevance")): missing.append("deep_analysis.radar_relevance")
                    if missing:
                        print(f"REJECT {label} result {idx}: recovered active result not deep enough; missing {', '.join(missing)}")
                        rejected += 1
                        continue
                claims, claim_problems = normalize_v2_claims(
                    raw, key=key, row=row, is_historical=is_historical, strand=strand,
                    decision=decision, qualification=clean(deep_ok.get("qualification")), claims_required=True,
                )
                if claim_problems:
                    print(f"REJECT {label} result {idx}: claim validation failed: {'; '.join(claim_problems)}")
                    rejected += 1
                    continue

                now = utc_now()
                stored_strand = strand.rsplit("_", 1)[-1].upper() if is_historical else ("A" if strand == "frontier_evidence" else strand.replace("strand_", "").upper())
                verification_copy = copy.deepcopy(raw.get("verification") or {})
                verification_copy["hardcore_recovery"] = copy.deepcopy(raw.get("hardcore_recovery"))
                entry = {
                    "profile": V2_PROFILE,
                    "strand": stored_strand,
                    "corpus_scope": "historical" if is_historical else "main",
                    "source_hash": cur_hash,
                    "identity_hash": cur_ih,
                    **normalized,
                    "verification": verification_copy,
                    "admission": copy.deepcopy(raw.get("admission")),
                    "duplicate": copy.deepcopy(raw.get("duplicate")),
                    "deep_read_mode": "offline_llm_hardcore_terminal_recovery",
                    "reader_text_model": clean(raw.get("processor")) or "user-provided-llm-subscription",
                    "reader_text_written_at": now,
                    "deep_scan_package_id": clean(result_doc.get("package_id")) or "hardcore-terminal",
                    "claims": claims or [],
                    "claims_profile": CLAIMS_FORMAT,
                }
                table[key] = entry
                if entry.get("reader_why"):
                    avoid_whys.append(entry["reader_why"])
                sidecar_decision = "duplicate" if clean(dup.get("status")).lower() == "duplicate" else decision
                admit_table[key] = {
                    "decision": sidecar_decision,
                    "target_strand": clean(admission.get("target_strand")).upper(),
                    "reason_code": clean(admission.get("reason_code")).upper(),
                    "reason": clean(admission.get("reason")),
                    "source": "deep_scan_hardcore_terminal",
                    "corpus_scope": "historical" if is_historical else "main",
                    "updated_at": now,
                    "deep_scan_package_id": clean(result_doc.get("package_id")) or "hardcore-terminal",
                    "verification_note": clean((raw.get("verification") or {}).get("verification_note")),
                    "duplicate_of": dup_of if clean(dup.get("status")).lower() == "duplicate" else "",
                }
                correction = raw.get("metadata_correction") if isinstance(raw.get("metadata_correction"), dict) else {}
                fields = correction.get("fields") if isinstance(correction.get("fields"), dict) else {}
                unset = correction.get("unset") if isinstance(correction.get("unset"), list) else []
                if fields or unset:
                    safe_fields = {k: copy.deepcopy(v) for k, v in fields.items() if k in SAFE_CORRECTION_FIELDS}
                    safe_unset = [x for x in unset if x in SAFE_UNSET_FIELDS]
                    corr_table[key] = {
                        "fields": safe_fields,
                        "unset": safe_unset,
                        "reason_code": "DEEP_SCAN_V2_METADATA_CORRECTION",
                        "reason": clean(correction.get("reason")),
                        "source": "deep_scan_hardcore_terminal",
                        "corpus_scope": "historical" if is_historical else "main",
                        "evidence": [clean(x.get("url")) for x in _usable_sources(raw.get("verification") or {}) if clean(x.get("url"))],
                        "updated_at": now,
                        "deep_scan_package_id": clean(result_doc.get("package_id")) or "hardcore-terminal",
                    }
                mark_verified(work_state, key, clean(result_doc.get("package_id")) or "hardcore-terminal", when=now)
                manual.discard(key)
                accepted += 1
                print(f"ACCEPT recovered {decision.upper()} {label} result {idx}" + (f" with prose safeguards: {'; '.join(prose_problems)}" if prose_problems else ""))
        if had_doc:
            imported_files.append(path)

    if accepted:
        now = utc_now()
        sidecar["version"] = 3
        sidecar["profile"] = V2_PROFILE
        sidecar["generated_at"] = now
        sidecar["claims_profile"] = CLAIMS_FORMAT
        sidecar["claims_updated_at"] = now
        admission_state["version"] = 1
        admission_state["profile"] = "radar-admission-v1"
        admission_state["updated_at"] = now
        corrections["version"] = 1
        corrections["profile"] = "radar-record-corrections-v1"
        corrections["updated_at"] = now
        problems = validate_sidecars(doc, admission_state, corrections, sidecar)
        if problems:
            raise SystemExit("Refusing to write invalid sidecars: " + " | ".join(problems[:10]))
        args.sidecar.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.admission.write_text(json.dumps(admission_state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.corrections.write_text(json.dumps(corrections, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        save_state(work_state, args.work_state)
        pending_keys = [x[1] for x in pending(doc, sidecar)] + [x[1] for x in historical_pending(historical, sidecar)]
        write_status_markdown(work_state, sidecar, pending_keys, args.status_file)

    for path in imported_files:
        try:
            path.unlink()
        except OSError as exc:
            raise SystemExit(f"Imported results but could not remove inbox file {path}: {exc}") from exc

    print(f"Hardcore Deep Scan recovery import: accepted {accepted} (exhausted drops {exhausted_count}); stale {stale}; rejected {rejected}.")


if __name__ == "__main__":
    main()
