#!/usr/bin/env python3
"""Deployment/workflow sanity checks.

These checks stay separate from scanner regression tests. A stale or partially uploaded
hidden workflow must never prevent the evidence engine from running, but the shipped
workflows should serialize Main and Historical scans at repository level.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
checks = []


def require(path, needle, label):
    text = path.read_text(encoding="utf-8")
    checks.append((needle in text, label, str(path.relative_to(ROOT)), needle))


def forbid(path, needle, label):
    text = path.read_text(encoding="utf-8")
    checks.append((needle not in text, label, str(path.relative_to(ROOT)), f"not {needle}"))


main = ROOT / ".github/workflows/radar-scan.yml"
hist = ROOT / ".github/workflows/historical-scan.yml"

require(main, "cron: '17 0,4,8,12,16,20 * * *'", "Main scanner fixed four-hour schedule")
require(hist, "cron: '53 6 * * *'", "Historical scan separated from Main schedule")
for path, label in ((main, "Main"), (hist, "Historical")):
    require(path, "group: ri-research-scanners", f"{label} shared scanner lock")
    require(path, "cancel-in-progress: false", f"{label} never cancels an active scanner")
    # GitHub Actions concurrency has no `queue: max` key. A shared group already queues
    # one pending run and prevents simultaneous execution.
    forbid(path, "queue: max", f"{label} uses valid GitHub concurrency syntax")

require(main, "git add -- radar.json", "Main persistence boundary")
require(main, "radar.json is the ONLY persistent output", "Main persistence-boundary explanation")
require(hist, "HISTORICAL_MIN_RUNTIME_SECONDS: '0'", "Historical target-driven runtime")
require(hist, "git add -- historical/historical.json", "Historical persistence boundary")
require(hist, "grep -vx 'historical/historical.json'", "Historical persistence-boundary explanation")

# Visible-code fallback for the recurring case where a browser upload leaves hidden
# workflow YAML stale. Main/Historical scanners still refuse to overlap; Historical also
# refreshes only the expected date-window metadata so the legacy safety step does not turn
# a deliberate defer into a false red failure.
guard = ROOT / "scripts/scanner_run_guard.py"
hist_scan = ROOT / "historical/scan_historical.py"
require(guard, "def defer_if_peer_scanner_active", "Legacy workflow runtime collision guard")
require(hist_scan, "refresh_window_metadata_after_peer_defer", "Historical legacy-defer compatibility")

failed = [x for x in checks if not x[0]]
for ok, label, rel, needle in checks:
    print(("OK  " if ok else "WARN") + f" {label}: {rel}")
if failed:
    print("\nWorkflow contract mismatch. Scanner code remains protected by its runtime guard, but the shipped YAML should be corrected.")
    for _, label, rel, needle in failed:
        print(f" - {label}: expected {needle!r} in {rel}")
    sys.exit(1)
print("Workflow contract looks correct.")
