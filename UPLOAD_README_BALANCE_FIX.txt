RADAR v24.7.4 BALANCE FIX — SIMPLE UPLOAD NOTES

The easiest option is to use the supplied full fixed repository ZIP and replace your repository contents with it.
The important point: radar.json is ALREADY CLEANED. You do not need to run Python or any cleanup command.

If you prefer to upload only changed files, use the separate patch ZIP and keep its folder structure.

Main changed files:
  radar_config.json
  radar.json
  scripts/scan_radar.py
  scripts/apply_c_source_policy_cleanup.py
  historical/scan_historical.py
  relevant regression tests
  V2474_BALANCED_C_SOURCE_POLICY.md

What this does:
  - keeps Historical A+B only
  - uses 8:1:3 as a relative discovery balance, not a cap
  - keeps baseline C scanning so C cannot be choked back to zero
  - removes the broad national-media C firehose
  - keeps elite news and authoritative international/EU institutions
  - collapses duplicate C coverage of the same event
  - cleans old disallowed/duplicate C rows from the visible site data

If you upload through GitHub's web interface, make one commit containing the changed files together so code and radar.json stay in sync.
