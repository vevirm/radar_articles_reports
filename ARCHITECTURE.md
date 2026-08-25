# Architecture — V17.10.2 manual candidate recovery

The radar now has two discovery entrances feeding one substantive evidence gate.

1. **Automated discovery** in `scripts/scan_radar.py` uses the existing scholarly/institutional source rotation and source-aware `gate_scope`.
2. **Manual candidate ingestion** in `scripts/manual_ingest.py` parses DOCX/PDF/CSV/JSON/YAML/TXT/Markdown, normalizes bibliography/URLs, deduplicates against state, retrieves the cited primary source where possible, then invokes the same `gate_scope`.

The manual document itself is never treated as source evidence. User-confirmed link reachability is stored separately from evidence verification, so a working URL cannot by itself admit a record. Records are tagged as verified primary, secondary reference, uncertain/metadata-only, forthcoming/unpublished, context-only, or existing-corpus. Only a verified primary source that passes the normal A/B substantive gate can be newly admitted.

## Recall repair

Missed current candidates produce diagnostics. Exact non-homepage URLs are placed in a bounded recovery queue (`manual_recovery_urls_per_scan`, default 10). A later real scanner run retries those URLs before broad institutional discovery, but all recovered text still passes the normal substantive gate. This narrows recall repair to known high-value candidates instead of broadening low-precision domains or weakening thresholds.

## Provenance

Public records use `discovery_provenance` = `automated`, `manual`, or `both`, plus a provenance array and manual ingest IDs. Matching an existing automated record changes provenance only; it does not duplicate the item.

## State integrity

`manual_ingest` is an additive state namespace containing batches, diagnostics and the recovery queue. Manual ingest deliberately preserves `last_updated`, scan cursors, completed cycles and scan-result history. A real scanner run preserves the namespace and records recovery attempts at that scan's real timestamp.

## Matrix

Core evidence classification continues to use source-backed evidence. `quadrant_claimed` (the outcome a source advocates/claims) remains distinct from `quadrant_implied` (the outcome implied by its evidence); implied evidence controls placement when supplied.
