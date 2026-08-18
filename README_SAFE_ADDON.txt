R&I RADAR BRIEFING — SAFE + IMMEDIATE
=======================================

EXISTING RADAR
--------------
Unchanged:
- existing radar results stay in place
- the existing R&I Radar Scan remains the scanner
- the existing regular scan schedule stays unchanged
- existing A/B/C logic stays unchanged

ADDED SUBPAGE
-------------
/briefing/

TIMING
------
1. FIRST RUN
   Immediately when this add-on is uploaded/updated, analyze the radar material
   that already exists.

2. NORMAL RHYTHM
   After every successful "R&I Radar Scan", wait 30 minutes and analyze the newest
   radar material.

3. MANUAL
   The briefing workflow can also be run manually at any time.

OUTPUT
------
The main visible output is a simple list of issues:
- one short bullet per issue
- about one sentence per issue
- focused on the R&I × EU × geopolitics intersection

Evidence is available below in expandable sections.

SAFETY
------
This package does NOT contain or replace:
- radar.json
- the main index.html
- scripts/scan_radar.py
- .github/workflows/radar-scan.yml
- radar_config.json
- radar_criteria.md

The briefing reads radar.json, verifies that it did not change it, and commits
ONLY briefing/index.html and briefing/briefing.json.

FILES
-----
.github/workflows/radar-briefing.yml
scripts/build_briefing.py
README_SAFE_ADDON.txt
