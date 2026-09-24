#!/usr/bin/env python3
"""Persist the exact order of a manually prepared single Deep Scan package.

Without this reservation, a newly discovered high-priority Strand-A item could move to the
front of the live queue while an offline 60-record package is being processed, causing the
strict importer to reject the returned package as out-of-order.  Reservation makes the
package order authoritative without changing Deep Scan judgement.
"""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

try:
    from scripts.deep_scan_work_state import load_state, register_package, save_state
except ModuleNotFoundError:
    from deep_scan_work_state import load_state, register_package, save_state  # type: ignore


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", type=Path, required=True)
    ap.add_argument("--work-state", type=Path, default=Path("deep_scan_work_state.json"))
    args = ap.parse_args()

    if not args.package.exists():
        raise SystemExit(f"Package not found: {args.package}")
    state = load_state(args.work_state)
    lanes = state.get("lanes", {}) if isinstance(state.get("lanes"), dict) else {}
    existing = lanes.get("SINGLE", {})
    unresolved = [x for x in existing.get("assigned", []) if isinstance(x, str)] if isinstance(existing, dict) else []
    if unresolved:
        # Repair the precise legacy jam caused by older prepare-single runs: if every
        # unresolved SINGLE key is also reserved by another lane, SINGLE owns no unique
        # work and can be released safely.  Never auto-release a genuine standalone
        # SINGLE reservation.
        reserved_elsewhere: set[str] = set()
        for lane_name, lane_row in lanes.items():
            if str(lane_name).upper() == "SINGLE" or not isinstance(lane_row, dict):
                continue
            reserved_elsewhere.update(
                key for key in lane_row.get("assigned", [])
                if isinstance(key, str) and key
            )
        duplicate_only = bool(unresolved) and all(key in reserved_elsewhere for key in unresolved)
        if duplicate_only:
            existing["assigned"] = []
            existing["target_size"] = 0
            existing["current_package_id"] = ""
            print(
                f"Released stale SINGLE reservation: {len(unresolved)} record(s) are already "
                "reserved by persistent worker lanes."
            )
        else:
            unique_count = len([key for key in unresolved if key not in reserved_elsewhere])
            raise SystemExit(
                f"A prior single Deep Scan package still has {len(unresolved)} reserved record(s) "
                f"({unique_count} unique to SINGLE). Import/finish that package before preparing "
                "another single package."
            )

    with zipfile.ZipFile(args.package) as zf:
        manifests = [n for n in zf.namelist() if n.endswith("/manifest.json") or n == "manifest.json"]
        if not manifests:
            raise SystemExit("Deep Scan package contains no manifest.json")
        manifest = json.loads(zf.read(manifests[0]).decode("utf-8"))
        package_id = str(manifest.get("package_id") or "").strip()
        if not package_id:
            raise SystemExit("Deep Scan package manifest has no package_id")
        keys: list[str] = []
        for entry in manifest.get("batches", []) if isinstance(manifest.get("batches"), list) else []:
            if not isinstance(entry, dict):
                continue
            rel = str(entry.get("file") or "").strip()
            if not rel:
                continue
            # Batch files live below the same package root as the manifest.
            root = manifests[0].rsplit("/", 1)[0] if "/" in manifests[0] else ""
            name = f"{root}/{rel}" if root else rel
            payload = json.loads(zf.read(name).decode("utf-8"))
            for job in payload.get("jobs", []) if isinstance(payload.get("jobs"), list) else []:
                if isinstance(job, dict) and str(job.get("record_key") or "").strip():
                    keys.append(str(job["record_key"]).strip())
    if not keys:
        raise SystemExit("Deep Scan package has no record keys to reserve")

    # Defense in depth: even if package preparation regresses, never commit a SINGLE
    # reservation that overlaps another active lane.
    conflicts: dict[str, list[str]] = {}
    key_set = set(keys)
    for lane_name, lane_row in state.get("lanes", {}).items():
        if str(lane_name).upper() == "SINGLE" or not isinstance(lane_row, dict):
            continue
        overlap = [
            key for key in lane_row.get("assigned", [])
            if isinstance(key, str) and key in key_set
        ]
        if overlap:
            conflicts[str(lane_name)] = overlap
    if conflicts:
        detail = ", ".join(f"{lane}: {len(items)}" for lane, items in sorted(conflicts.items()))
        raise SystemExit(
            "Refusing overlapping SINGLE reservation; package contains records already "
            f"reserved elsewhere ({detail}). Re-run prepare-single with the fixed preparer."
        )

    register_package(state, "SINGLE", package_id, keys)
    lane = state.setdefault("lanes", {}).setdefault("SINGLE", {})
    lane["target_size"] = len(keys)
    lane["assigned"] = list(keys)
    save_state(state, args.work_state)
    print(f"Reserved single Deep Scan package {package_id}: {len(keys)} records in fixed import order.")


if __name__ == "__main__":
    main()
