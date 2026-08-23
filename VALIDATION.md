# V17.7.2 validation

- 186 unit tests pass.
- All prior precision/false-positive tests pass after updating the persisted-state fixture to the supplied 2026-08-23T17:42Z radar state.
- New tests cover the bounded Strand-A external-position route, generic-EU rejection, facility-page rejection, method-first B contribution, source-first journal configuration, and rejection of non-futures “scenario construction” false positives.
- The bundled `radar.json` is byte-for-byte identical to the supplied `radar (13).json`: 51 Strand A, 12 Strand B, 5 Strand C.
- No A/B/C quality cleanup migration is triggered. Existing accepted items are preserved.
- A recall-profile migration resets discovery/rejection progress only so the widened source-first/contextual rules can reconsider previously unseen/rejected material; it does not delete corpus entries.
- Previously rejected institutional fingerprints are cleared once so wider rules can actually reconsider those reports.
- Crossref source-first journal rotation is execution-aware and bounded to eight journals / 60 recent records per journal per scan.
- Crossref query-based priority tasks are reduced to 32 per scan to offset source-first requests.
- Anonymous request pacing is deliberately slower after the observed degraded run: OpenAlex 1 worker / 1.0 s minimum interval; Crossref 1.2 s minimum interval. Crossref 429 responses get bounded cooldown retries; OpenAlex still fails fast after a 429 to preserve its established safety behavior.
- Scan budget remains 1200 seconds; OpenAlex/Crossref/institution stage slices remain 390/540/390 seconds.
