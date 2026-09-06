#!/usr/bin/env python3
"""Runtime start-state check for the Main Radar scanner.

This is deliberately not a regression-test suite.  It validates only the repository state
needed to run safely: either the explicit one-use 200-item fresh baseline, or a normal live
scanner state created by an earlier successful run in this repository.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RADAR = ROOT / "radar.json"
DECLARATION = ROOT / "FRESH_START"
TOKEN = "RADAR_FRESH_START_V1"


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Cannot read {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{path.name} must contain a JSON object")
    return value


def rows(doc: dict, key: str) -> list:
    value = doc.get(key, [])
    return value if isinstance(value, list) else []


def fresh_contract(doc: dict) -> tuple[bool, str]:
    marker = doc.get("fresh_repository_seed")
    if not isinstance(marker, dict) or str(marker.get("version") or "").strip() != "v1":
        return False, "radar.json does not carry fresh_repository_seed=v1"
    try:
        declaration = DECLARATION.read_text(encoding="utf-8")
    except Exception:
        return False, "FRESH_START declaration is missing"
    if TOKEN not in declaration:
        return False, "FRESH_START declaration has the wrong token"
    a, b = rows(doc, "strand_a"), rows(doc, "strand_b")
    if (len(a), len(b)) != (190, 10):
        return False, f"fresh baseline must be 190 A + 10 B, found {len(a)} A + {len(b)} B"
    if rows(doc, "ab_archive"):
        return False, "fresh baseline must not contain inherited ab_archive rows"
    if rows(doc, "strand_c"):
        return False, "fresh baseline must not contain inherited Strand C rows"
    if doc.get("scan_state") or doc.get("scan_history"):
        return False, "fresh baseline must not contain inherited scan state/history"
    if doc.get("last_updated") or doc.get("run_completed_at") or doc.get("first_scan_complete"):
        return False, "fresh baseline must not contain a prior scanner completion timestamp"
    return True, ""


def main() -> int:
    doc = load_json(RADAR)
    if DECLARATION.exists():
        ok, why = fresh_contract(doc)
        if not ok:
            raise SystemExit(f"FRESH_START is present but the clean baseline contract is invalid: {why}")
        print("Fresh start accepted: 190 A + 10 B baseline; no archive, C, scan_state or scan_history.")
        print("The first successful scan will create this repository's own cursors/state/history.")
        return 0

    if doc.get("fresh_repository_seed"):
        raise SystemExit("radar.json still requests a fresh seed but FRESH_START is absent")
    if not doc.get("first_scan_complete"):
        raise SystemExit("Neither a valid FRESH_START baseline nor a completed live scanner state is present")
    if not isinstance(doc.get("scan_state"), dict):
        raise SystemExit("Live radar is missing scan_state")
    if not isinstance(doc.get("scan_history"), list) or not doc.get("scan_history"):
        raise SystemExit("Live radar is missing its own scan_history")
    print(f"Live incremental state accepted: {len(doc['scan_history'])} completed run(s) recorded by this repository.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
