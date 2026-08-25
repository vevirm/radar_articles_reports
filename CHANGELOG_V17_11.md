# V17.11.0 changelog

- Fixed manual ingestion so a reviewed manual source can become admissible evidence instead of remaining permanently deferred when runtime HTTP retrieval is unavailable.
- Made the exact curator-supplied URL the binding key for reviewed evidence; manual ingestion does not use search-engine discovery.
- Preserved the supplied URL in provenance when an explicitly secondary/generic/wrong-reference record is resolved to a primary source.
- Added reviewed-source core-gate handling that preserves the scanner's lexical result for recall diagnostics instead of weakening automated pass-1 precision.
- Kept curator cell mappings as hypotheses only; admission and matrix placement use reviewed underlying-source evidence.
- Fixed the Frontier frontend to honor reviewed `matrix_dimension` for the row instead of re-inferring the row from topic keywords.
- Preserved `quadrant_claimed` separately from `quadrant_implied`; implied evidence controls matrix placement when present.
- Tightened title-only deduplication so distinct technology-sovereignty sources cannot collapse into one record.
- Added reviewed weak-signal matrix handling without making directional keywords mandatory gates.
- Re-reviewed `EU_RI_Additions_May-Aug_2026.docx`: 17 substantive sources and 2 weak signals admitted; 5 deferred; 7 retained as context/outside-window.
- Added/updated regression coverage for exact-URL binding, reviewed gate behavior, primary resolution provenance, deduplication, reviewed row control, and reviewed weak signals.
- Preserved authoritative `last_updated = 2026-08-25T07:34Z`; no live scan was claimed.
