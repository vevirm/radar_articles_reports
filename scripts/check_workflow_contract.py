#!/usr/bin/env python3
"""Static production workflow contract check. Not run as a pre-scan regression gate."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
main=(ROOT/'.github/workflows/radar-scan.yml').read_text(encoding='utf-8')
hist=(ROOT/'.github/workflows/historical-scan.yml').read_text(encoding='utf-8')
checks=[
 ("cron: '17 */4 * * *'" in main,'Main runs every four hours at :17 UTC'),
 ("cron: '57 */4 * * *'" in hist,'Historical runs every four hours at :57 UTC'),
 ('group: ri-radar-research-scanners' in main and 'group: ri-radar-research-scanners' in hist,'Shared scanner concurrency lock'),
 ('cancel-in-progress: true' in main,'Main can pre-empt Historical and therefore has priority'),
 ('cancel-in-progress: false' in hist,'Historical never cancels Main'),
 ('Run standard 24-minute Main scanner' in main,'Main production budget step'),
 ('Run standard 10-minute Historical scanner' in hist,'Historical production budget step'),
 ("HISTORICAL_SCAN_BUDGET_SECONDS: '600'" in hist,'Historical 10-minute budget'),
 ('Run scanner regression tests' not in main,'No legacy regression discovery before Main research'),
 ('Run historical scanner tests' not in hist,'No legacy regression discovery before Historical research'),
 ('Launch one fresh 20-minute rescue scan' not in main,'No second rescue workflow behind Main'),
 ('Launch one fresh historical rescue scan' not in hist,'No second rescue workflow behind Historical'),
 ('git add -- radar.json' in main,'Main persistence boundary'),
 ('git add -- historical/historical.json' in hist,'Historical persistence boundary'),
]
failed=False
for ok,label in checks:
 print(('OK  ' if ok else 'FAIL')+label)
 failed|=not ok
if failed: raise SystemExit(1)
