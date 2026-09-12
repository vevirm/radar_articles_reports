v24.7.5 RELATIVE 8:1:3 FIX

What this fixes
- Main mixed scans no longer publish a C flood when A/B yield is small.
- 8:1:3 is a relative running ratio, not fixed ceilings.
- Surplus valid B/C is deferred for later release rather than rejected.
- Historical remains A+B only and follows 8:1; no Historical C.
- The latest 1 A / 1 B / 26 C run is repaired in the included radar.json to 1 A / 1 B / 1 C, with the other 25 C retained as pending candidates.
- Downstream reasoning was retraced and has zero orphan evidence references.

GitHub browser upload
1. Extract the patch ZIP on your computer.
2. Open the ROOT of the GitHub repository (where radar.json and radar_config.json are visible).
3. Add file -> Upload files.
4. Drag the CONTENTS of the extracted patch folder, not the outer folder itself.
5. Check that GitHub shows paths such as scripts/scan_radar.py, historical/scan_historical.py, tests/all_tests.zip, radar.json and radar_config.json.
6. Commit directly to main. Suggested message: Enforce relative 8-1-3 publication balance

Do not run any cleanup script manually. The corrected radar.json is already included.
