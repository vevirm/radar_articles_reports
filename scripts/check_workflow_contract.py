#!/usr/bin/env python3
"""Static production workflow contract check. Not run as a pre-scan regression gate."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
main=(ROOT/'.github/workflows/radar-scan.yml').read_text(encoding='utf-8')
hist=(ROOT/'.github/workflows/historical-scan.yml').read_text(encoding='utf-8')
checks=[
 ("cron: '17 0,4,8,12,16,20 * * *'" in main,'Main runs every four hours at :17 UTC'),
 ("cron: '17 2,6,10,14,18,22 * * *'" in hist,'Historical runs every four hours, exactly two hours after Main'),
 ('group: ri-radar-research-scanners' in main and 'group: ri-radar-research-scanners' in hist,'Shared scanner concurrency lock'),
 ('cancel-in-progress: false' in main and 'cancel-in-progress: false' in hist,'Neither scanner cancels the other; the later run waits'),
 ('Run scanner regression tests' in main,'Main regression gate retained'),
 ('Run historical scanner tests' in hist,'Historical regression gate retained'),
 ("HISTORICAL_MIN_RUNTIME_SECONDS: '600'" in hist,'Historical minimum research runtime remains ten minutes'),
 ('git add -- radar.json' in main,'Main persistence boundary'),
 ('git add -- historical/historical.json' in hist,'Historical persistence boundary'),
]
failed=False
for ok,label in checks:
 print(('OK  ' if ok else 'FAIL')+label)
 failed|=not ok
if failed: raise SystemExit(1)
