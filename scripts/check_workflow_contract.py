#!/usr/bin/env python3
"""Deployment/workflow sanity checks.

These checks are deliberately separate from scanner regression tests. A stale or
partially uploaded workflow file must never prevent the evidence engine from
running. GitHub Actions can call this checker with continue-on-error, so mismatches
produce a visible warning while the scanner itself remains safe.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
checks = []


def require(path, needle, label):
    text = path.read_text(encoding='utf-8')
    checks.append((needle in text, label, str(path.relative_to(ROOT)), needle))


def forbid(path, needle, label):
    text = path.read_text(encoding='utf-8')
    checks.append((needle not in text, label, str(path.relative_to(ROOT)), f'not {needle}'))


main = ROOT / '.github/workflows/radar-scan.yml'
hist = ROOT / '.github/workflows/historical-scan.yml'

require(main, "cron: '17 0,4,8,12,16,20 * * *'", 'Main scanner four-hour schedule')
require(hist, "cron: '53 6 * * *'", 'Historical scan separated from Main schedule')
for path, label in ((main, 'Main'), (hist, 'Historical')):
    require(path, 'group: ri-research-scanners', f'{label} shared scanner lock')
    require(path, 'queue: max', f'{label} queues instead of replacing pending scans')
    require(path, 'cancel-in-progress: false', f'{label} never cancels an active scanner')

require(main, 'rescue_needed: ${{ steps.rescue.outputs.dispatch }}', 'Main rescue remains inside the same workflow cycle')
require(main, "RADAR_RESCUE_MODE: 'true'", 'Main in-workflow rescue mode')
forbid(main, '/actions/workflows/radar-scan.yml/dispatches', 'Main does not release the lock between normal and rescue rounds')
require(hist, 'rescue_needed: ${{ steps.rescue.outputs.dispatch }}', 'Historical rescue remains inside the same workflow cycle')
require(hist, "HISTORICAL_RESCUE_MODE: 'true'", 'Historical in-workflow rescue mode')
forbid(hist, '/actions/workflows/historical-scan.yml/dispatches', 'Historical does not release the lock between normal and rescue rounds')

require(main, 'git add -- radar.json', 'Main persistence boundary')
require(main, 'radar.json is the ONLY persistent output', 'Main persistence-boundary explanation')
require(hist, "HISTORICAL_MIN_RUNTIME_SECONDS: '600'", 'Historical bounded runtime')
require(hist, 'git add -- historical/historical.json', 'Historical persistence boundary')
require(hist, "grep -vx 'historical/historical.json'", 'Historical persistence-boundary explanation')

failed = [x for x in checks if not x[0]]
for ok, label, rel, needle in checks:
    print(('OK  ' if ok else 'WARN') + f' {label}: {rel}')
if failed:
    print('\nWorkflow contract mismatch. The scanner itself is still safe to run; update the YAML files on the next repository upload.')
    for _, label, rel, needle in failed:
        print(f' - {label}: expected {needle!r} in {rel}')
    sys.exit(1)
print('Workflow contract looks correct.')
