# Architecture — V17.11.1 exact-link reviewed manual evidence

The radar has two discovery entrances feeding the same substantive standard.

1. **Automated discovery** (`scripts/scan_radar.py`) uses scholarly/institutional source rotation and source-aware gating.
2. **Manual candidate ingestion** (`scripts/manual_ingest.py`) parses common office/data formats, normalizes bibliography/URLs, deduplicates against state, and targets the **exact URL supplied by the curator**.

Manual ingestion does not use a search engine. When direct runtime retrieval is unavailable, a reviewed-evidence cache may stand in for fetched text only when its review is explicitly bound to the same canonical supplied URL and records source verification/evidence mode. A primary URL may be resolved for records explicitly flagged as secondary/generic/wrong-reference, but the supplied URL remains provenance.

## Evidence and admission

The curator document is a candidate/recovery source, not primary evidence. The manual lane can nevertheless admit a record once underlying reviewed source evidence satisfies the core requirement: genuine EU/European R&I in geopolitical context. Metadata-only material defers rather than being called irrelevant. Forthcoming, context-only and unresolved secondary records remain separate.

The reviewed-source route records scanner diagnostics as well as the reviewed decision, so a lexical miss can be distinguished from a substantive failure instead of silently weakening the scanner gate.

## Matrix

Curator cells are stored only as `curator_primary_cell` / `curator_cells`. Reviewed source evidence stores `matrix_dimension`, `quadrant_claimed`, `quadrant_implied`, and `matrix_evidence_basis`. The frontend locks the matrix row to reviewed `matrix_dimension`; it does not re-infer that row from topic words. Evidence-implied quadrant controls placement when present, while claimed/advocated direction remains visible separately.

## Recall repair

Missed current candidates can feed bounded exact-URL recovery queues. A later real scanner run retries those URLs before broader institutional discovery, but every recovered source still must pass the substantive gate. This raises recall around known high-value misses without broadly lowering precision.

## Provenance and state integrity

Public records use `discovery_provenance` = `automated`, `manual`, or `both`. Manual diagnostics preserve manual IDs, supplied URLs, directly resolved primary/full-text URLs, and the direct-link chain used during review. Manual ingest has separate history under `manual_ingest` and deliberately preserves `last_updated`, scan cursors, completed cycles and scan-result history.
