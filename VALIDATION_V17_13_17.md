# Validation — V17.13.17 security hardening

Validation was performed against the supplied V17.13.16 package.

## Logic/data integrity

The following files are byte-for-byte unchanged from V17.13.16:

- `scripts/scan_radar.py`
- `scripts/build_briefing.py`
- `scripts/frontier_coverage.js`
- `scripts/presentation_smoke.js`
- `briefing/insights.js`
- `radar.json`
- `radar_config.json`
- `eu_ri_radar_config_v2.yaml`
- `requirements.txt`

The V17.13.16 and V17.13.17 `radar.json` SHA-256 is:

`687fecf91f33253e6a654f712e39f57aafc55657066637a6d4bc74966c2acae6`

## Changed files only

- `.github/workflows/radar-scan.yml`
- `.github/workflows/person-backfill.yml`
- `README.md` (12-hour text corrected to 6-hour)
- `VERSION.txt`
- `CHANGELOG_V17_13_17.md` (new)
- `SECURITY_HARDENING.md` (new)
- `VALIDATION_V17_13_17.md` (new)

## Checks passed

- Both workflow YAML files parse successfully.
- Scanner/support Python files compile successfully.
- Existing presentation smoke suite passes completely.
- The safety gate accepts the unchanged current `radar.json`.
- The unexpected-file guard accepts the unchanged working tree.
- No network discovery/full scanner run was performed during packaging, so the evidence corpus was not refreshed or altered.
