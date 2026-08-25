# V17.11.1 changelog

- Ingested `EU_RI_Additions_III_May-Aug_2026.docx` against the newer supplied `radar (22).json` state, preserving the live-scan timestamp and scanner state.
- Fixed DOCX matrix parsing when `(primary)` marks a later listed cell, and stopped numbered weak-signal subsection headings from leaking into the preceding curator note.
- Added `partial_text` handling to manual retrieval/review evidence.
- Fixed pre-ingest comparison so records admitted earlier in the same manual batch are not falsely reported as prior automated corpus hits.
- Added explicit `duplicate_in_batch` and `rejected_core_gate` diagnostics.
- A verified underlying source that fails the substantive EU/European R&I-in-geopolitics gate is now a real rejection, not a retrieval defer or exact-URL recovery target.
- Preserved reviewed evidence for context/outside-window records without admitting them to the primary corpus.
- Reviewed Additions III only from curator-supplied URLs and direct links exposed by those pages; no broad web/title search was used.
- Additions III result: 12 records parsed; 3 substantive sources admitted; 2 weak signals admitted; 4 deferred; 1 verified core-gate rejection; 1 context record; 1 in-batch duplicate; 0 forthcoming.
- Five Additions III admissions enter the Sovereignty Frontier matrix: C11 → C-C, C13 → I-C, R14 → R-D, W16 → K-B, W17 → C-A.
- Manual diagnostics now retain the curator-supplied URL, directly resolved primary/full-text URL, and direct-link chain used for verification.
- Complete automated test suite: 251 passed in 18.95s.
