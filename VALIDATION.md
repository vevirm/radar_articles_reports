# Current validation — V17.12.4

The user-supplied standalone `radar (26).json` was used as the authoritative cumulative state because it was newer than the V17.12.3 ZIP copy. The manual batch reviewed 63 bibliography entries, added 23 verified substantive Strand-A records, assigned 12 source-evidence-backed matrix placements, matched 7 existing records without duplication, kept 24 core-gate rejects and 8 context/reference/outside-window records outside the public radar, and left one record-level item deferred. One additional component of a compound citation also remains deferred.

The scanner `last_updated` timestamp remains `2026-08-26T19:37Z`; no scan cursor was advanced. The manual-ingest ledger records the separate batch timestamp and all 63 decisions.

A canonical URL + normalized-title integrity pass found two duplicate-source records already present in the newer standalone baseline. They were consolidated while preserving alternate-title/version metadata. Final public evidence arrays contain **0 duplicate normalized titles** and **0 duplicate canonical source URLs**.

Focused regression tests passed: **49 tests + 4 subtests** covering manual ingest, source-aware matrix logic, site architecture and insights rendering. Presentation smoke passed with `176 A / 24 B / 17 C`, **129 qualifying matrix signals**, and valid checked JavaScript syntax.
