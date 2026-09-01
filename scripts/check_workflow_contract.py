#!/usr/bin/env python3
"""Deployment/workflow sanity checks.

These checks are deliberately separate from scanner regression tests. A stale or
partially uploaded workflow file must never prevent the evidence engine from
running. GitHub Actions calls this checker with continue-on-error, so mismatches
produce a visible warning while the scanner still runs safely.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

checks = []

def require(path, needle, label):
    text = path.read_text(encoding='utf-8')
    ok = needle in text
    checks.append((ok, label, str(path.relative_to(ROOT)), needle))

main = ROOT / '.github/workflows/radar-scan.yml'
hist = ROOT / '.github/workflows/historical-scan.yml'
require(main, "cron: '17 0,4,8,12,16,20 * * *'", 'Main scanner four-hour schedule')
require(main, 'git add -- radar.json', 'Main persistence boundary')
require(main, 'only radar.json can be committed', 'Main persistence-boundary explanation')
require(main, '/actions/workflows/radar-scan.yml/dispatches', 'Main low-yield rescue dispatch target')
require(hist, "cron: '41 3 * * *'", 'Historical daily schedule')
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
