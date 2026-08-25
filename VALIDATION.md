# V17.11.1 validation

Validated against the supplied repository, authoritative `radar (22).json`, and `EU_RI_Additions_III_May-Aug_2026.docx` using an exact-link reviewed-evidence pack.

- Manual parser covers DOCX/PDF/CSV/JSON/YAML/YML/TXT/Markdown.
- Exact supplied URL remains the manual retrieval key; no search-engine discovery is used in the manual path.
- Direct redirects and direct links exposed by a supplied page may resolve an underlying primary source while preserving the curator-supplied URL; diagnostics retain the resolved URL and direct-link chain.
- Parser regression coverage includes later-listed `(primary)` cells and numbered weak-signal subsections.
- Pre-ingest comparison is frozen so same-batch manual duplicates cannot become false automated hits.
- Verified source-based pass-1 failures are recorded as `rejected_core_gate` and are not left in exact-URL recovery queues.
- Full-text, partial-text, abstract-only, metadata-only, secondary, forthcoming and context records remain distinct.
- Curator cells remain hypotheses; reviewed source evidence supplies `matrix_dimension`, `quadrant_claimed`, and `quadrant_implied`.
- Manual ingestion preserves live-scan bookkeeping. `last_updated` remains **2026-08-25T10:58Z**.
- Final state: **141 Strand A**, **23 Strand B**, **14 weak signals**.
- Additions III contributes **5 new Frontier matrix signals**.
- Complete automated suite: **251 passed** (`PYTHONPATH=. pytest -q`).

No live scan occurred during this build. Manual review/ingest timestamps are stored separately from scanner timestamps/cursors.
