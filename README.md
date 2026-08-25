# R&I Geopolitics Radar V17.10.2

V17.10.2 adds curated manual-candidate recovery without turning a hand-built list into an admission bypass. It preserves the V17.9 source-aware aboutness and evidence-led matrix rules and uses the supplied `radar (21).json` as the authoritative state.

## Manual candidate ingest

Use:

```bash
python scripts/manual_ingest.py path/to/candidates.docx --state radar.json
```

Accepted inputs: DOCX, PDF, CSV, JSON, YAML/YML, TXT and Markdown. `--no-fetch` performs comparison/registration only. `--refresh` reprocesses a previously ingested file hash. `--links-validated` records supplied URLs as user-tested/reachable without treating reachability as substantive evidence or bibliographic verification.

The ingest path extracts bibliographic fields and URLs, matches DOI/URL/title conservatively against the existing corpus, attempts the underlying primary source, and applies the same substantive `gate_scope` used by automated discovery. A manual citation alone is never evidence. Metadata-only candidates are deferred; secondary references, forthcoming/unpublished records and context-only records stay outside the matrix.

## Recall diagnostics and provenance

Manual candidates are compared with both the admitted corpus and the scanner's saved seen-URL ledger. High-value misses can enter a bounded exact-URL recovery queue which the normal scanner retries before broad institutional discovery; it does not lower the EU/European R&I + geopolitical pass-1 standard.

Items expose discovery provenance as `automated`, `manual`, or `both`. Existing matches are deduplicated and marked `both`. The UI shows that provenance on radar and matrix cards.

See `MANUAL_INGEST_REPORT.md` for both supplied May–August 2026 list comparisons, including the Sovereignty Frontier supplement and its weak-signal candidates.

## Source-aware aboutness and matrix semantics

- Full text may use strict recurrence/section-spread aboutness evidence.
- Abstract-only records are judged on substantive EU/European R&I + geopolitical content without requiring nonexistent sections.
- Metadata-only records defer and trigger retrieval rather than being called irrelevant.
- Bare `EU` is not treated as European Union unless context establishes it.
- Display claims state what the source finds, argues, reports or projects without boilerplate prefixes.
- Matrix classification uses substantive source evidence; directional vocabulary supports but does not gate classification.
- `quadrant_claimed` and `quadrant_implied` are preserved separately. Evidence-implied placement is not overwritten by an advocated/claimed outcome.

## State integrity

Manual ingestion is not a live scan. It does not change `last_updated`, scan cursors, completed cycles or scan-result bookkeeping. The bundled authoritative timestamp remains `2026-08-25T07:34Z` from the supplied state.

## Run and validate

Serve `index.html` with any local static server. The scanner is `scripts/scan_radar.py`; runtime JSON config is `radar_config.json`; the design/config specification is `eu_ri_radar_config_v2.yaml`.

Run the complete suite with:

```bash
python -m pytest -q
```
