#!/usr/bin/env python3
"""Verify protected Radar core files against the reasoning-reform baseline.

This is intentionally simple: it protects migration stages that promise not to touch
scanner/Deep-Scan/active-boundary code. Later stages may update the baseline only as
an explicit reviewed action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "reasoning-reform" / "baseline.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--group",
        action="append",
        choices=("scanner_hard_core", "deep_scan_hard_core", "active_boundary"),
        help="Check only selected group(s). Default: all protected groups.",
    )
    args = ap.parse_args()
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    groups = args.group or ["scanner_hard_core", "deep_scan_hard_core", "active_boundary"]
    failures: list[str] = []
    checked = 0
    for group in groups:
        for rel, expected in baseline["protected_code_hashes"][group].items():
            p = ROOT / rel
            if not p.exists():
                failures.append(f"MISSING {rel}")
                continue
            actual = sha256(p)
            checked += 1
            if actual != expected:
                failures.append(f"CHANGED {rel}\n  expected {expected}\n  actual   {actual}")
    if failures:
        print("Reasoning-reform core freeze: FAILED")
        for x in failures:
            print(x)
        return 1
    print(f"Reasoning-reform core freeze: OK ({checked} protected files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
