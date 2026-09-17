#!/usr/bin/env python3
"""Offline claim backfill for the Radar reasoning reform.

This tool deliberately sits *after* Deep Scan.  It never browses, never changes
scanner evidence, never changes Deep Scan admission, and never changes the public
reader.  It packages already-stored authoritative Deep Scan text for claim
extraction and imports only schema-valid claims back into ``reader_text.json``.

Usage:
  python scripts/backfill_claims.py prepare --output-dir claim_backfill_out
  python scripts/backfill_claims.py import --inbox claim_backfill_inbox
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.claims_schema import load_vocabulary, validate_claims
    from scripts.deep_read_works import iter_historical_records, iter_records, record_key
except ModuleNotFoundError:  # direct script execution from scripts/
    from claims_schema import load_vocabulary, validate_claims  # type: ignore
    from deep_read_works import iter_historical_records, iter_records, record_key  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
READER = ROOT / "reader_text.json"
ADMISSION = ROOT / "admission_state.json"
CORPUS = ROOT / "radar.json"
ACTIVE = ROOT / "radar_active.json"
HISTORICAL = ROOT / "historical" / "historical.json"
VOCAB = ROOT / "claims_vocabulary.json"

PACKAGE_FORMAT = "radar-claims-backfill-package-v1"
RESULT_FORMAT = "radar-claims-backfill-results-v1"
AUTHORITATIVE_PROFILE = "deep-reader-v2-authoritative"
ELIGIBLE_DECISIONS = {"keep", "review", "needs_manual_verification"}
DROP_DECISIONS = {"drop", "drop_unverifiable", "duplicate"}
DECISION_WEIGHT = {
    "keep": 1.0,
    "review": 0.6,
    "needs_manual_verification": 0.35,
    "provisional": 0.35,
    "awaiting": 0.35,
    "drop": 0.0,
    "drop_unverifiable": 0.0,
    "duplicate": 0.0,
}

INSTRUCTIONS = r"""# Radar claim backfill — START HERE

You are extracting structured claims from **stored Deep Scan text only**.
Do not browse the web. Do not add facts from memory. Do not reinterpret admission.

For each job in `claims_jobs.json`:

1. Read only the supplied reader/deep-analysis text and metadata.
2. Return **1–3 claims**. The first is the main finding. A second is allowed for a
   distinct object–mechanism pair. A third is allowed only when a factual
   qualification/limit itself forms a useful claim.
3. Copy `record_key`, `source_hash`, `identity_hash`, `job_hash`, `era`, and
   `merit` exactly from the job. Every claim for that job uses that exact merit.
4. Set `origin` to `backfill`; set `provisional` to false.
5. Use only objects/mechanisms/classes/statuses/etc. in the supplied
   `claims_vocabulary.json`. Never invent a vocabulary term. If the stored text
   cannot support a required field, put the whole job in `rejected` with a short
   reason instead of guessing.
6. `qualification` should preserve the Deep Scan qualification. The main claim
   should carry it verbatim when one exists. A secondary claim may use an empty
   qualification when the qualification does not apply to that sentence.
7. `text` is one factual sentence. Preserve proposal/negotiation/operating status;
   do not turn intentions into outcomes or diagnoses into effects.
8. Historical jobs keep `era: historical`; current jobs keep `era: current`.
9. Do not alter the top-level format or package_id.

Write one file named `claims_backfill_results.json` with this shape:

{
  "format": "radar-claims-backfill-results-v1",
  "package_id": "COPY EXACTLY",
  "results": [
    {
      "record_key": "COPY EXACTLY",
      "source_hash": "COPY EXACTLY",
      "identity_hash": "COPY EXACTLY",
      "job_hash": "COPY EXACTLY",
      "claims": [ ... 1 to 3 complete claim objects ... ]
    }
  ],
  "rejected": [
    {"record_key": "...", "reason": "Only when extraction cannot be done without guessing."}
  ]
}

A returned file may contain a carefully completed prefix of the batch. Never fill
uncertain records just to finish the batch.
"""


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return data


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, suffix=".tmp") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
        temp = Path(fh.name)
    temp.replace(path)


def _decision_for(key: str, reader_entry: dict[str, Any], admission: dict[str, Any]) -> str:
    row = (admission.get("records") or {}).get(key)
    if isinstance(row, dict) and clean(row.get("decision")):
        return clean(row.get("decision")).lower()
    embedded = reader_entry.get("admission") if isinstance(reader_entry.get("admission"), dict) else {}
    return clean(embedded.get("decision")).lower() or "provisional"


def _raw_maps() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    current: dict[str, dict[str, Any]] = {}
    historical: dict[str, dict[str, Any]] = {}
    raw = _read_json(CORPUS)
    for _strand, row in iter_records(raw):
        key = record_key(row)
        if key and key not in current:
            current[key] = row
    hist_doc = _read_json(HISTORICAL)
    for _strand, row in iter_historical_records(hist_doc):
        key = record_key(row)
        if key and key not in historical:
            historical[key] = row
    return current, historical


def _active_map() -> dict[str, dict[str, Any]]:
    if not ACTIVE.exists():
        return {}
    doc = _read_json(ACTIVE)
    out: dict[str, dict[str, Any]] = {}
    for _strand, row in iter_records(doc):
        key = record_key(row)
        if key and key not in out:
            out[key] = row
    return out


def _source_merit_current(rows: dict[str, dict[str, Any]]) -> dict[str, int]:
    """Use the repository's existing Stuff score without re-implementing it.

    One Node invocation scores all current rows with ``source_merit.js``.  This is
    read-only and keeps the claim merit exactly tied to the repository's existing
    0–100 audit score rather than creating a second Python scoring system.
    """
    if not rows:
        return {}
    js = r"""
const fs=require('fs');
const Merit=require('./source_merit.js');
const rows=JSON.parse(fs.readFileSync(0,'utf8'));
const out={};
for(const [k,v] of Object.entries(rows)) out[k]=Merit.scoreFor(v);
process.stdout.write(JSON.stringify(out));
"""
    try:
        p = subprocess.run(
            ["node", "-e", js],
            input=json.dumps(rows, ensure_ascii=False),
            text=True,
            cwd=ROOT,
            capture_output=True,
            check=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("Node is required to calculate the existing Stuff merit score") from exc
    raw = json.loads(p.stdout)
    return {str(k): max(0, min(100, int(round(float(v))))) for k, v in raw.items()}


def _merit_map() -> dict[str, int]:
    current, historical = _raw_maps()
    active = _active_map()
    # Active rows include authoritative Deep Scan/corrections. Fall back to raw only
    # if an active copy is unavailable.
    current_for_score = {k: active.get(k, row) for k, row in current.items()}
    out = _source_merit_current(current_for_score)
    for key, row in historical.items():
        value = row.get("source_merit_score")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            # Historical scanner rows predate the current Stuff helper in some
            # edge cases. Score them with the same helper rather than guessing.
            continue
        out[key] = max(0, min(100, int(round(float(value)))))
    missing_hist = {k: v for k, v in historical.items() if k not in out}
    if missing_hist:
        out.update(_source_merit_current(missing_hist))
    return out


def _deep_text(reader_entry: dict[str, Any]) -> dict[str, Any]:
    deep = reader_entry.get("deep_analysis") if isinstance(reader_entry.get("deep_analysis"), dict) else {}
    return {
        "reader_title": clean(reader_entry.get("reader_title")),
        "reader_what": clean(reader_entry.get("reader_what")),
        "reader_why": clean(reader_entry.get("reader_why")),
        "reader_more": clean(reader_entry.get("reader_more")),
        "deep_analysis": {
            "work_kind": clean(deep.get("work_kind")),
            "research_question": clean(deep.get("research_question")),
            "main_finding": clean(deep.get("main_finding")),
            "method_or_basis": clean(deep.get("method_or_basis")),
            "qualification": clean(deep.get("qualification")),
            "radar_relevance": clean(deep.get("radar_relevance")),
            "confidence": clean(deep.get("confidence")),
            "why_supported": deep.get("why_supported"),
        },
    }


def _job_hash(job: dict[str, Any]) -> str:
    material = {
        "record_key": job["record_key"],
        "source_hash": job["source_hash"],
        "identity_hash": job["identity_hash"],
        "era": job["era"],
        "decision": job["decision"],
        "merit": job["merit"],
        "stored_text": job["stored_text"],
    }
    raw = json.dumps(material, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def build_jobs(
    reader: dict[str, Any] | None = None,
    admission: dict[str, Any] | None = None,
    *,
    include_existing: bool = False,
    merit_by_key: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    reader = reader or _read_json(READER)
    admission = admission or _read_json(ADMISSION)
    merit_by_key = merit_by_key or _merit_map()
    table = reader.get("records") if isinstance(reader.get("records"), dict) else {}
    # "Current" means present in the authoritative active corpus now. Deep Scan
    # sidecars deliberately retain older verified records after rolling-window
    # retention; those stale sidecar entries must not be revived into reasoning.
    active_current_keys = set(_active_map())
    jobs: list[dict[str, Any]] = []
    for key, entry in table.items():
        if not isinstance(entry, dict) or entry.get("profile") != AUTHORITATIVE_PROFILE:
            continue
        deep = entry.get("deep_analysis") if isinstance(entry.get("deep_analysis"), dict) else {}
        if not clean(deep.get("main_finding")):
            continue
        decision = _decision_for(key, entry, admission)
        if decision in DROP_DECISIONS or decision not in ELIGIBLE_DECISIONS:
            continue
        if not include_existing and isinstance(entry.get("claims"), list) and entry.get("claims"):
            continue
        era = "historical" if key.startswith("historical:") else "current"
        if era == "current" and key not in active_current_keys:
            continue
        if key not in merit_by_key:
            raise ValueError(f"No 0–100 merit score available for {key}")
        job = {
            "record_key": key,
            "source_hash": clean(entry.get("source_hash")),
            "identity_hash": clean(entry.get("identity_hash")),
            "era": era,
            "strand": clean(entry.get("strand")),
            "decision": decision,
            "decision_weight": DECISION_WEIGHT.get(decision, 0.35),
            "merit": merit_by_key[key],
            "stored_text": _deep_text(entry),
        }
        job["job_hash"] = _job_hash(job)
        jobs.append(job)
    # Stable order: current first, then historical, preserving insertion order within era.
    jobs.sort(key=lambda j: (j["era"] == "historical", j["record_key"]))
    return jobs


def _package_id(index: int, jobs: list[dict[str, Any]]) -> str:
    seed = "|".join(j["job_hash"] for j in jobs)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10]
    return f"claims-backfill-{index:03d}-{digest}"


def prepare(output_dir: Path, *, batch_size: int = 20, max_records: int = 120, include_existing: bool = False) -> dict[str, Any]:
    if batch_size < 1 or batch_size > 40:
        raise ValueError("batch_size must be from 1 to 40")
    if max_records < 1:
        raise ValueError("max_records must be positive")
    all_jobs = build_jobs(include_existing=include_existing)
    jobs = all_jobs[:max_records]
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    vocabulary = _read_json(VOCAB)
    packages: list[str] = []
    for index, start in enumerate(range(0, len(jobs), batch_size), start=1):
        chunk = jobs[start:start + batch_size]
        package_id = _package_id(index, chunk)
        doc = {
            "format": PACKAGE_FORMAT,
            "package_id": package_id,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "jobs": chunk,
        }
        template = {"format": RESULT_FORMAT, "package_id": package_id, "results": [], "rejected": []}
        zip_path = output_dir / f"{package_id}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("START_HERE.txt", INSTRUCTIONS)
            zf.writestr("claims_jobs.json", json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
            zf.writestr("claims_vocabulary.json", json.dumps(vocabulary, ensure_ascii=False, indent=2) + "\n")
            zf.writestr("claims_backfill_results.json", json.dumps(template, ensure_ascii=False, indent=2) + "\n")
        packages.append(zip_path.name)
    summary = {
        "format": PACKAGE_FORMAT,
        "eligible_unbackfilled": len(all_jobs),
        "packaged_records": len(jobs),
        "batch_size": batch_size,
        "packages": packages,
    }
    _write_json_atomic(output_dir / "manifest.json", summary)
    return summary


def _expected_jobs_by_key() -> dict[str, dict[str, Any]]:
    return {j["record_key"]: j for j in build_jobs(include_existing=True)}


def _validate_result_doc(doc: Any, expected: dict[str, dict[str, Any]], vocabulary: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    errors: list[str] = []
    accepted: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(doc, dict) or doc.get("format") != RESULT_FORMAT:
        return accepted, [f"result format must be {RESULT_FORMAT}"]
    if not clean(doc.get("package_id")):
        errors.append("missing package_id")
    rows = doc.get("results")
    if not isinstance(rows, list):
        errors.append("results must be a list")
        return accepted, errors
    seen: set[str] = set()
    for idx, raw in enumerate(rows):
        label = f"results[{idx}]"
        if not isinstance(raw, dict):
            errors.append(f"{label}: must be an object")
            continue
        key = clean(raw.get("record_key"))
        if not key or key in seen:
            errors.append(f"{label}: missing or duplicate record_key")
            continue
        seen.add(key)
        job = expected.get(key)
        if not job:
            errors.append(f"{label}: record is not currently eligible for backfill: {key}")
            continue
        for field in ("source_hash", "identity_hash", "job_hash"):
            if clean(raw.get(field)) != clean(job.get(field)):
                errors.append(f"{label}: stale or altered {field} for {key}")
        claims = raw.get("claims")
        if not isinstance(claims, list) or not 1 <= len(claims) <= 3:
            errors.append(f"{label}: claims must contain 1 to 3 claims")
            continue
        for cidx, claim in enumerate(claims):
            if not isinstance(claim, dict):
                errors.append(f"{label}.claims[{cidx}]: must be an object")
                continue
            if clean(claim.get("record_key")) != key:
                errors.append(f"{label}.claims[{cidx}]: record_key mismatch")
            if clean(claim.get("origin")) != "backfill" or claim.get("provisional") is not False:
                errors.append(f"{label}.claims[{cidx}]: backfill claims require origin=backfill and provisional=false")
            if clean(claim.get("era")) != job["era"]:
                errors.append(f"{label}.claims[{cidx}]: era mismatch")
            if claim.get("merit") != job["merit"]:
                errors.append(f"{label}.claims[{cidx}]: merit must exactly equal packaged merit {job['merit']}")
        for problem in validate_claims(claims, vocabulary):
            errors.append(f"{label}: {problem}")
        qualification = clean(job["stored_text"]["deep_analysis"].get("qualification"))
        if qualification and clean(claims[0].get("qualification")) != qualification:
            errors.append(f"{label}.claims[0]: qualification must copy Deep Scan qualification verbatim")
        if not any(e.startswith(label) for e in errors):
            accepted[key] = copy.deepcopy(claims)
    return accepted, errors


def import_results(
    inbox: Path,
    *,
    reader_path: Path = READER,
    admission_path: Path = ADMISSION,
    delete_imported: bool = True,
    expected_jobs: dict[str, dict[str, Any]] | None = None,
    vocabulary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    files = sorted(p for p in inbox.glob("*.json") if p.is_file())
    if not files:
        return {"files": 0, "records_imported": 0, "claims_imported": 0, "claims_removed_for_drop": 0}
    reader = _read_json(reader_path)
    admission = _read_json(admission_path)
    table = reader.get("records") if isinstance(reader.get("records"), dict) else {}
    expected = expected_jobs if expected_jobs is not None else _expected_jobs_by_key()
    vocabulary = vocabulary or load_vocabulary(VOCAB)
    all_accepted: dict[str, list[dict[str, Any]]] = {}
    errors: list[str] = []
    for path in files:
        try:
            doc = _read_json(path)
        except Exception as exc:
            errors.append(f"{path.name}: unreadable JSON: {exc}")
            continue
        accepted, probs = _validate_result_doc(doc, expected, vocabulary)
        errors.extend(f"{path.name}: {p}" for p in probs)
        for key, claims in accepted.items():
            if key in all_accepted:
                errors.append(f"{path.name}: duplicate record returned across inbox files: {key}")
            else:
                all_accepted[key] = claims
    if errors:
        raise ValueError("Claim backfill import rejected:\n- " + "\n- ".join(errors))

    # Re-check decisions immediately before writing. Deep Scan remains authoritative.
    removed = 0
    for key, entry in table.items():
        if not isinstance(entry, dict):
            continue
        decision = _decision_for(key, entry, admission)
        if decision in DROP_DECISIONS and "claims" in entry:
            entry.pop("claims", None)
            removed += 1

    claim_count = 0
    for key, claims in all_accepted.items():
        entry = table.get(key)
        if not isinstance(entry, dict):
            raise ValueError(f"reader_text record disappeared during import: {key}")
        decision = _decision_for(key, entry, admission)
        if decision in DROP_DECISIONS or decision not in ELIGIBLE_DECISIONS:
            raise ValueError(f"Deep Scan decision no longer allows claims for {key}: {decision}")
        entry["claims"] = claims
        claim_count += len(claims)
    reader["records"] = table
    reader["claims_profile"] = "radar-claims-v1"
    reader["claims_updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    _write_json_atomic(reader_path, reader)
    if delete_imported:
        for path in files:
            path.unlink()
    return {
        "files": len(files),
        "records_imported": len(all_accepted),
        "claims_imported": claim_count,
        "claims_removed_for_drop": removed,
    }


def coverage(reader_path: Path = READER, admission_path: Path = ADMISSION) -> dict[str, int]:
    reader = _read_json(reader_path)
    admission = _read_json(admission_path)
    table = reader.get("records") if isinstance(reader.get("records"), dict) else {}
    active_current_keys = set(_active_map())
    out = {
        "eligible_current": 0,
        "backfilled_current": 0,
        "eligible_historical": 0,
        "backfilled_historical": 0,
        "dropped_with_claims": 0,
    }
    for key, entry in table.items():
        if not isinstance(entry, dict) or entry.get("profile") != AUTHORITATIVE_PROFILE:
            continue
        decision = _decision_for(key, entry, admission)
        has_claims = isinstance(entry.get("claims"), list) and bool(entry.get("claims"))
        if decision in DROP_DECISIONS:
            if has_claims:
                out["dropped_with_claims"] += 1
            continue
        if decision not in ELIGIBLE_DECISIONS or not clean((entry.get("deep_analysis") or {}).get("main_finding")):
            continue
        era = "historical" if key.startswith("historical:") else "current"
        if era == "current" and key not in active_current_keys:
            continue
        out[f"eligible_{era}"] += 1
        if has_claims:
            out[f"backfilled_{era}"] += 1
    return out


def audit(reader_path: Path = READER, admission_path: Path = ADMISSION) -> dict[str, int]:
    reader = _read_json(reader_path)
    admission = _read_json(admission_path)
    table = reader.get("records") if isinstance(reader.get("records"), dict) else {}
    vocabulary = load_vocabulary(VOCAB)
    active_current_keys = set(_active_map())
    all_claims: list[dict[str, Any]] = []
    problems: list[str] = []
    records_with_claims = 0
    for key, entry in table.items():
        if not isinstance(entry, dict):
            continue
        claims = entry.get("claims")
        if claims in (None, []):
            continue
        if not isinstance(claims, list):
            problems.append(f"{key}: claims must be a list")
            continue
        decision = _decision_for(key, entry, admission)
        if decision in DROP_DECISIONS:
            problems.append(f"{key}: dropped/duplicate record must not carry claims")
        era = "historical" if key.startswith("historical:") else "current"
        if era == "current" and key not in active_current_keys:
            problems.append(f"{key}: stale current sidecar record must not carry claims")
        for idx, claim in enumerate(claims):
            if not isinstance(claim, dict):
                problems.append(f"{key}.claims[{idx}]: must be an object")
                continue
            if clean(claim.get("record_key")) != key:
                problems.append(f"{key}.claims[{idx}]: record_key mismatch")
            if clean(claim.get("era")) != era:
                problems.append(f"{key}.claims[{idx}]: era mismatch")
            all_claims.append(claim)
        records_with_claims += 1
    problems.extend(validate_claims(all_claims, vocabulary))
    if problems:
        raise ValueError("Claim store audit failed:\n- " + "\n- ".join(problems))
    return {"records_with_claims": records_with_claims, "claims": len(all_claims)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepare/import the offline Radar claim backfill")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prepare")
    p.add_argument("--output-dir", type=Path, default=ROOT / "claim_backfill_out")
    p.add_argument("--batch-size", type=int, default=20)
    p.add_argument("--max-records", type=int, default=120)
    p.add_argument("--include-existing", action="store_true")

    i = sub.add_parser("import")
    i.add_argument("--inbox", type=Path, default=ROOT / "claim_backfill_inbox")
    i.add_argument("--keep-files", action="store_true")

    sub.add_parser("coverage")
    sub.add_parser("audit")
    args = ap.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.output_dir, batch_size=args.batch_size, max_records=args.max_records, include_existing=args.include_existing)
        elif args.command == "import":
            result = import_results(args.inbox, delete_imported=not args.keep_files)
        elif args.command == "coverage":
            result = coverage()
        else:
            result = audit()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
