#!/usr/bin/env python3
"""Rebuild all active analytical products from the centralized active corpus.

The raw scanner collections in radar.json are preserved byte-for-byte in meaning:
this script never removes/reclassifies/corrects those stored rows.  It builds an
in-memory active view from sidecars, regenerates downstream reasoning from that
view, then writes only derived products and active-corpus diagnostics back into
radar.json.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.active_corpus import (
    RAW_COLLECTIONS, build_active_document, load_admission, load_corrections,
    load_reader, record_key, validate_sidecars,
)
from scripts import downstream_retrace

DERIVED_KEYS = (
    "strategic_pathways", "external_shock_watch", "shock_inference",
    "high_order_inference", "downstream_archive", "downstream_retrace",
    "reader_products_refresh",
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _counts(doc: dict[str, Any]) -> dict[str, int]:
    return {k: len(doc.get(k, [])) if isinstance(doc.get(k), list) else 0 for k in RAW_COLLECTIONS}


def _add_historical_context(doc: dict[str, Any]) -> None:
    path = ROOT / "historical" / "historical.json"
    try:
        hist = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return
    rows = hist.get("items", []) if isinstance(hist, dict) else []
    doc["historical_context"] = [
        copy.deepcopy(x) for x in rows
        if isinstance(x, dict) and str(x.get("strand") or "").strip().upper() == "A"
    ]


def _v2_coverage(raw: dict[str, Any], reader: dict[str, Any]) -> dict[str, int]:
    table = reader.get("records", {}) if isinstance(reader.get("records"), dict) else {}
    all_keys = {
        record_key(r) for c in ("strand_a", "strand_b", "strand_c", "frontier_evidence")
        for r in (raw.get(c, []) if isinstance(raw.get(c), list) else [])
        if isinstance(r, dict) and record_key(r)
    }
    verified = {k for k in all_keys if isinstance(table.get(k), dict) and table[k].get("profile") == "deep-reader-v2-authoritative"}
    return {"total_records": len(all_keys), "v2_verified": len(verified), "v2_pending": len(all_keys - verified)}


def rebuild(raw: dict[str, Any], *, admission: dict[str, Any], corrections: dict[str, Any], reader: dict[str, Any], now: str, allow_large_change: bool = False) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    problems = validate_sidecars(raw, admission, corrections, reader)
    if problems:
        raise RuntimeError("Active-corpus sidecar validation failed: " + " | ".join(problems[:10]))

    active = build_active_document(raw, admission=admission, corrections=corrections, reader=reader)
    _add_historical_context(active)
    raw_counts = _counts(raw)
    active_counts = _counts(active)
    raw_total = sum(raw_counts[k] for k in ("strand_a", "strand_b", "strand_c"))
    active_total = sum(active_counts[k] for k in ("strand_a", "strand_b", "strand_c"))

    if raw_total and active_total == 0:
        raise RuntimeError("Fail-safe: active corpus would be empty")
    if raw_total >= 50 and active_total < raw_total * 0.40 and not allow_large_change:
        raise RuntimeError(f"Fail-safe: active corpus would collapse from {raw_total} to {active_total}; inspect decisions or rerun with --allow-large-change")
    for k in ("strand_a", "strand_b", "strand_c"):
        if raw_counts[k] >= 10 and active_counts[k] == 0 and not allow_large_change:
            raise RuntimeError(f"Fail-safe: {k} would collapse from {raw_counts[k]} to zero")

    # Fresh replay from the active evidence only. Previous derived state is present
    # for audit comparison, but retrace_document rebuilds inference rather than
    # allowing unsupported objects to persist through hysteresis.
    rebuilt_active, retrace_report = downstream_retrace.retrace_document(active, now=now, revalidation_report=None)

    out = copy.deepcopy(raw)
    for key in DERIVED_KEYS:
        if key in rebuilt_active:
            out[key] = copy.deepcopy(rebuilt_active[key])

    coverage = _v2_coverage(raw, reader)
    state_counts = active.get("active_corpus", {}).get("decision_counts", {})
    out["active_corpus"] = {
        "profile": "radar-active-corpus-v1",
        "rebuilt_at": now,
        "raw_counts": raw_counts,
        "active_counts": active_counts,
        "raw_total": raw_total,
        "active_total": active_total,
        "decision_counts": state_counts,
        "review_is_active": True,
        "missing_state_is": "provisional_active",
        "deep_scan_v2": coverage,
        "derived_reasoning_uses_active_corpus": True,
        "metadata_corrections_applied_to_active_view": True,
        "deep_scan_v2_semantics_feed_reasoning": True,
    }
    stats = out.get("stats") if isinstance(out.get("stats"), dict) else {}
    stats.update({
        "active_corpus_total": active_total,
        "active_strand_a": active_counts.get("strand_a", 0),
        "active_strand_b": active_counts.get("strand_b", 0),
        "active_strand_c": active_counts.get("strand_c", 0),
        "deep_scan_v2_verified": coverage["v2_verified"],
        "deep_scan_v2_pending": coverage["v2_pending"],
        "inactive_drop": int(state_counts.get("drop", 0) or 0),
        "inactive_unverifiable": int(state_counts.get("drop_unverifiable", 0) or 0),
        "inactive_duplicates": int(state_counts.get("duplicate", 0) or 0),
        "active_review": int(state_counts.get("review", 0) or 0),
    })
    out["stats"] = stats

    rebuilt_active["active_corpus"]["rebuilt_at"] = now
    rebuilt_active["active_corpus"]["deep_scan_v2"] = coverage
    rebuilt_active["active_corpus_snapshot"] = True
    rebuilt_active["active_corpus_source"] = "radar.json + admission_state.json + record_corrections.json + reader_text.json"

    report = {
        "profile": "radar-active-corpus-rebuild-v1",
        "completed_at": now,
        "raw_counts": raw_counts,
        "active_counts": active_counts,
        "decision_counts": state_counts,
        "deep_scan_v2": coverage,
        "downstream_diagnostics": retrace_report.get("diagnostics", {}),
        "integrity_check": retrace_report.get("integrity_check", {}),
    }
    return out, rebuilt_active, report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--radar", type=Path, default=ROOT / "radar.json")
    ap.add_argument("--admission", type=Path, default=ROOT / "admission_state.json")
    ap.add_argument("--corrections", type=Path, default=ROOT / "record_corrections.json")
    ap.add_argument("--reader", type=Path, default=ROOT / "reader_text.json")
    ap.add_argument("--report", type=Path, default=None)
    ap.add_argument("--active-output", type=Path, default=ROOT / "radar_active.json")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--allow-large-change", action="store_true")
    ap.add_argument("--now", default="")
    args = ap.parse_args()

    raw = json.loads(args.radar.read_text(encoding="utf-8"))
    admission = load_admission(args.admission)
    corrections = load_corrections(args.corrections)
    reader = load_reader(args.reader)
    rebuilt, active_snapshot, report = rebuild(
        raw, admission=admission, corrections=corrections, reader=reader,
        now=args.now or utc_now(), allow_large_change=args.allow_large_change,
    )
    if not args.check_only:
        args.radar.write_text(json.dumps(rebuilt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.active_output.write_text(json.dumps(active_snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
