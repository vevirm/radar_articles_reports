#!/usr/bin/env python3
"""Promote private Deep-A candidates only after authoritative Deep Scan V2 KEEP.

REVIEW and negative/terminal decisions remain invisible.  Negative/terminal records move
into a small audit archive; DEFER/recovery-retry candidates stay staged so the normal Deep
Scan recovery policy can continue.  The script never changes Deep Scan's judgement.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V2_PROFILE = "deep-reader-v2-authoritative"
VISIBLE_KEEP_TARGETS = {"A": "strand_a", "B": "strand_b"}
TERMINAL = {"drop", "drop_unverifiable", "duplicate", "needs_manual_verification", "review"}


def clean(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def record_key(row: dict[str, Any]) -> str:
    link = clean(row.get("link") or row.get("url"))
    if link:
        return f"link:{link}"
    doi = clean(row.get("doi") or row.get("_doi")).lower()
    if doi:
        doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi).removeprefix("doi:")
        return f"doi:{doi}"
    rid = clean(row.get("id") or row.get("record_id") or row.get("fingerprint"))
    return f"id:{rid}" if rid else ""


def load(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8"))


def public_key_locations(radar: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for collection in ("strand_a", "strand_b", "strand_c", "frontier_evidence"):
        for row in radar.get(collection, []) if isinstance(radar.get(collection), list) else []:
            if isinstance(row, dict):
                key = record_key(row)
                if key:
                    out[key] = collection
    return out


def strip_private_fields(row: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(row)
    for key in list(out):
        if key.startswith("deep_a_private_") or key in {"ordinary_a_pass"}:
            out.pop(key, None)
    out["new_this_scan"] = False
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, default=ROOT / "radar.json")
    ap.add_argument("--pool", type=Path, default=ROOT / "deep_a_candidates.json")
    ap.add_argument("--archive", type=Path, default=ROOT / "deep_a_candidate_archive.json")
    ap.add_argument("--admission", type=Path, default=ROOT / "admission_state.json")
    ap.add_argument("--reader", type=Path, default=ROOT / "reader_text.json")
    ap.add_argument("--report", type=Path, default=ROOT / "migration-reports" / "latest-deep-a-promotion.json")
    args = ap.parse_args()

    radar = load(args.corpus, {})
    pool = load(args.pool, {"version": 1, "profile": "deep-a-private-candidate-pool-v1", "candidates": []})
    admission = load(args.admission, {"records": {}})
    reader = load(args.reader, {"records": {}})
    archive = load(args.archive, {"version": 1, "profile": "deep-a-private-candidate-archive-v1", "records": []})
    if not isinstance(radar, dict) or not isinstance(pool, dict):
        raise SystemExit("Invalid radar/private candidate state")

    admissions = admission.get("records", {}) if isinstance(admission, dict) else {}
    readers = reader.get("records", {}) if isinstance(reader, dict) else {}
    public = public_key_locations(radar)
    remaining: list[dict[str, Any]] = []
    archived = list(archive.get("records", [])) if isinstance(archive.get("records"), list) else []
    archived_keys = {clean(x.get("record_key")) for x in archived if isinstance(x, dict)}
    promoted: list[dict[str, str]] = []
    hidden: list[dict[str, str]] = []
    already_public: list[str] = []
    now = utc_now()

    for candidate in pool.get("candidates", []) if isinstance(pool.get("candidates"), list) else []:
        if not isinstance(candidate, dict):
            continue
        key = record_key(candidate)
        if not key:
            continue
        adm = admissions.get(key) if isinstance(admissions, dict) and isinstance(admissions.get(key), dict) else {}
        rd = readers.get(key) if isinstance(readers, dict) and isinstance(readers.get(key), dict) else {}
        decision = clean(adm.get("decision")).lower()
        target = clean(adm.get("target_strand")).upper()
        authoritative = clean(rd.get("profile")) == V2_PROFILE and clean(adm.get("source")).lower() == "deep_scan_v2"

        if key in public:
            # The main scanner may independently discover the same work while an offline
            # Deep Scan package is being processed. In that case keep only one public row.
            if authoritative:
                already_public.append(key)
                continue
            remaining.append(candidate)
            continue

        if authoritative and decision == "keep" and target in VISIBLE_KEEP_TARGETS:
            collection = VISIBLE_KEEP_TARGETS[target]
            row = strip_private_fields(candidate)
            row["strand"] = target
            row["deep_scan_promoted_from_private_a"] = True
            row["deep_scan_promoted_at"] = now
            radar.setdefault(collection, []).append(row)
            public[key] = collection
            promoted.append({"record_key": key, "target_strand": target, "title": clean(row.get("title"))})
            continue

        # REVIEW is intentionally not public for the wider private harvester. Deep Scan's
        # normal rules are unchanged; this is simply a stricter publication boundary for
        # records that never entered the public corpus in the first place.
        if (authoritative and (decision in TERMINAL or (decision == "keep" and target not in VISIBLE_KEEP_TARGETS))) or decision == "needs_manual_verification":
            status = (f"keep_reclassified_{target}_hidden" if decision == "keep" and target not in VISIBLE_KEEP_TARGETS else (decision or "needs_manual_verification"))
            hidden.append({"record_key": key, "decision": status, "title": clean(candidate.get("title"))})
            if key not in archived_keys:
                archived.append({
                    "record_key": key,
                    "title": clean(candidate.get("title")),
                    "link": clean(candidate.get("link") or candidate.get("url")),
                    "deep_a_private_gate": clean(candidate.get("deep_a_private_gate")),
                    "decision": status,
                    "target_strand": target,
                    "reason_code": clean(adm.get("reason_code")),
                    "reason": clean(adm.get("reason")),
                    "deep_scan_package_id": clean(adm.get("deep_scan_package_id")),
                    "archived_at": now,
                })
                archived_keys.add(key)
            continue

        # No authoritative result yet, or DEFER/recovery retry: keep it in the private pool.
        remaining.append(candidate)

    pool_out = {
        "version": 1,
        "profile": "deep-a-private-candidate-pool-v1",
        "updated_at": now,
        "publication_policy": "private_until_authoritative_deep_scan_keep",
        "candidates": remaining,
    }
    archive_out = {
        "version": 1,
        "profile": "deep-a-private-candidate-archive-v1",
        "updated_at": now,
        "records": archived[-2000:],
    }
    args.corpus.write_text(json.dumps(radar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.pool.write_text(json.dumps(pool_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.archive.write_text(json.dumps(archive_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "profile": "deep-a-private-promotion-v1",
        "generated_at": now,
        "promoted": promoted,
        "hidden_after_deep_scan": hidden,
        "already_public": already_public,
        "remaining_private": len(remaining),
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Deep-A promotion: {len(promoted)} KEEP candidate(s) promoted; "
        f"{len(hidden)} verified non-KEEP candidate(s) kept off-page; "
        f"{len(remaining)} private candidate(s) remain queued/recovering."
    )


if __name__ == "__main__":
    main()
