# V17.7.1 validation

- 174 unit tests pass.
- The bundled `radar.json` remains byte-for-byte identical to the supplied current state.
- Existing A/B/C quality-profile versions are unchanged; no cleanup migration is triggered.
- Stage-budget warnings no longer count as source failures.
- Rotation has an explicit execution-aware cursor test: skipped queued work does not advance the persisted cursor.
- DOI landing metadata recovery has a bounded unit test.
- Historical Frontier gap lookback remains 0 months, preserving the existing temporal scope.
- Total hard scan budget remains 1200 seconds under the 30-minute GitHub Actions job cap.
