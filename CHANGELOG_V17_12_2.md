# V17.12.2 — bounded manual-ingest and rounds IV–VI state update

- Uses the supplied 26 August 2026 radar state as the base and preserves scanner `last_updated` (`2026-08-26T08:57Z`) and scan cursors.
- Fixes DOCX batch-boundary parsing so the declared rounds IV–VI block yields 58 records and appended rounds VII–X are not silently mixed into the batch.
- Preserves curator source type and verification caveats; `[window: check date]` now requires verification.
- Keeps manual review exact-link-only and URL-bound; direct redirects/linked underlying sources are allowed, broad search discovery is not.
- Adds unique batch counts for substantive and matrix admissions and saved-state recall-failure categories.
- Adds targeted source coverage for HCSS, IAI, Institut Montaigne, GMF and eeNews Europe without weakening the substantive gate.
- Ingests the actual rounds IV–VI batch: 10 new substantive radar items, 7 new matrix items, 4 existing matches, 4 reviewed core-gate rejects and 40 deferred items.
- Updates bundled state to 152 Strand A / 23 Strand B / 17 Strand C.
- Updates regression tests for the presentation-first manual-only workflow and current supplied state.
