# V17.11.0 validation

Validated against the supplied repository, authoritative `radar (21).json`, both supplied DOCX files, and the exact-link reviewed-evidence pack for the matrix-oriented supplement.

- Manual parser: DOCX/PDF/CSV/JSON/YAML/YML/TXT/Markdown.
- Exact supplied URL is the default manual retrieval key; manual ingestion performs no search-engine discovery.
- Reviewed evidence is accepted only when URL-bound to the exact supplied record and explicitly source-verified.
- Conservative URL/DOI/title deduplication; title-only threshold prevents distinct tech-sovereignty sources from collapsing.
- `EU_RI_Additions_May-Aug_2026.docx`: 31 records re-reviewed; **17 substantive admissions + 2 weak-signal admissions**, **5 deferred**, **7 context-only**.
- The 19 reviewed admissions appear in the matrix with source-derived row/column fields; curator cells remain comparison hints only.
- `quadrant_claimed` and `quadrant_implied` remain separate; reviewed implied evidence controls placement.
- Existing source-aware full-text/abstract/metadata behavior and contextual bare-`EU` handling remain covered.
- Manual ingestion preserves `last_updated`, scan results, cursors and completed-cycle history. Preserved timestamp: **2026-08-25T07:34Z**.
- Current state: **138 Strand A**, **23 Strand B**, **12 weak signals**.
- Complete automated suite: **245 passed** (`PYTHONPATH=. python -m pytest -q`).

No live scan occurred during this repair. Reviewed manual evidence is recorded at its own manual-review/ingest timestamp and does not alter live-scan bookkeeping.
