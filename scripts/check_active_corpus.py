#!/usr/bin/env python3
"""Validate Radar V2 sidecars and generated active snapshot."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.active_corpus import (
    RAW_COLLECTIONS, build_active_document, is_active_decision, load_admission, load_corrections,
    load_reader, record_key, validate_sidecars,
)



def main() -> int:
    raw = json.loads((ROOT / "radar.json").read_text(encoding="utf-8"))
    admission = load_admission(ROOT / "admission_state.json")
    corrections = load_corrections(ROOT / "record_corrections.json")
    reader = load_reader(ROOT / "reader_text.json")
    problems = validate_sidecars(raw, admission, corrections, reader)
    expected = build_active_document(raw, admission=admission, corrections=corrections, reader=reader)

    active_path = ROOT / "radar_active.json"
    if not active_path.exists():
        problems.append("radar_active.json is missing; run scripts/rebuild_active_radar.py")
        active = {}
    else:
        active = json.loads(active_path.read_text(encoding="utf-8"))
        if not active.get("active_corpus_snapshot"):
            problems.append("radar_active.json is not marked as an active-corpus snapshot")

    for collection in RAW_COLLECTIONS:
        exp_keys = [record_key(x) for x in expected.get(collection, []) if isinstance(x, dict)]
        got_keys = [record_key(x) for x in active.get(collection, []) if isinstance(x, dict)]
        if exp_keys != got_keys:
            problems.append(f"{collection} active snapshot does not match centralized admission state")

    inactive = {
        k for k, v in admission.get("records", {}).items()
        if isinstance(v, dict) and str(v.get("decision") or "").lower() in {"drop", "drop_unverifiable", "duplicate"}
    }
    active_keys = {
        record_key(x) for c in RAW_COLLECTIONS for x in (active.get(c, []) if isinstance(active.get(c), list) else [])
        if isinstance(x, dict) and record_key(x)
    }
    leaked = sorted(inactive & active_keys)
    if leaked:
        problems.append(f"inactive record leaked into radar_active.json: {leaked[0]}")

    # V2 active records must carry reader semantics; inactive V2 records may remain only
    # in the audit sidecars, never in the active snapshot.
    table = reader.get("records", {}) if isinstance(reader.get("records"), dict) else {}
    for key, state in admission.get("records", {}).items():
        if not isinstance(state, dict) or state.get("source") != "deep_scan_v2":
            continue
        if not is_active_decision(state.get("decision")):
            continue
        entry = table.get(key)
        if not isinstance(entry, dict) or entry.get("profile") != "deep-reader-v2-authoritative":
            problems.append(f"Deep Scan V2 admission lacks authoritative reader entry: {key}")

    summary = active.get("active_corpus", {}) if isinstance(active.get("active_corpus"), dict) else {}
    print("Active corpus:", summary.get("active_counts", {}))
    print("Decision counts:", summary.get("decision_counts", {}))
    print("Deep Scan V2:", summary.get("deep_scan_v2", {}))
    if problems:
        for p in problems:
            print("FAIL:", p)
        return 1
    print("Active-corpus validation passed; no inactive evidence is exposed by radar_active.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
