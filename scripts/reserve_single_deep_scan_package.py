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
    existing = state.get("lanes", {}).get("SINGLE", {})
    unresolved = [x for x in existing.get("assigned", []) if isinstance(x, str)] if isinstance(existing, dict) else []
    if unresolved:
        raise SystemExit(
            f"A prior single Deep Scan package still has {len(unresolved)} reserved record(s). "
            "Import/finish that package before preparing another single package."
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
    register_package(state, "SINGLE", package_id, keys)
    lane = state.setdefault("lanes", {}).setdefault("SINGLE", {})
    lane["target_size"] = len(keys)
    lane["assigned"] = list(keys)
    save_state(state, args.work_state)
    print(f"Reserved single Deep Scan package {package_id}: {len(keys)} records in fixed import order.")


if __name__ == "__main__":
    main()
