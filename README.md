# R&I Geopolitics Radar V17.11.1

V17.11.1 extends the exact-link manual-evidence lane with Additions III review and fixes two diagnostic/parser edge cases without turning manual curation into an admission bypass. The supplied DOCX URL is the primary retrieval target; broad web/search-engine discovery is not part of manual ingestion.

## Manual candidate ingest

```bash
python scripts/manual_ingest.py path/to/candidates.docx --state radar.json
```

Accepted inputs: DOCX, PDF, CSV, JSON, YAML/YML, TXT and Markdown. `--links-validated` records curator-tested reachability without treating reachability as substantive verification. `--no-fetch` is safe for comparison/registration; reviewed evidence can also be supplied with `--review-evidence PATH.json` when it is cryptographically/reproducibly tied to the exact supplied record URLs.

The lane extracts bibliography and URLs, deduplicates conservatively, retrieves the exact supplied source where possible, and evaluates the same substantive requirement as automated discovery: **genuine EU/European R&I in geopolitical context**. Metadata-only material defers. Secondary, uncertain, forthcoming and context-only records remain distinguishable.

A reviewed evidence cache is not a free-form manual override: each review must be URL-bound to the curator-supplied URL, source-verified, and explicit about its evidence mode/status. Primary-source resolution is permitted only when the supplied record itself needs it, while preserving the original supplied URL in provenance.

## Matrix-oriented manual lists

Curator cell mappings are stored as hypotheses, not answers. A reviewed source can be admitted when its underlying evidence passes the substantive gate; matrix placement then comes from reviewed source evidence (`matrix_dimension`, `quadrant_claimed`, `quadrant_implied`). The frontend honors that reviewed row/column instead of re-inferring the row from topic keywords.

The prior reviewed supplement remains intact (17 substantive sources + 2 weak signals). For `EU_RI_Additions_III_May-Aug_2026.docx`, V17.11.1 admits **3 substantive sources and 2 weak signals**; all **5 enter the Sovereignty Frontier matrix** after independent evidence review. The detailed decisions are in `MANUAL_INGEST_REPORT.md`.

## Recall diagnostics and provenance

Manual candidates are compared against the admitted corpus and saved seen-URL ledger. Missed high-value exact URLs may enter bounded recovery queues; future automated scans can retry them without weakening pass-1 precision. Public records expose `automated`, `manual`, or `both` provenance. Manual diagnostics preserve both the curator-supplied URL and any directly resolved primary/full-text URL, including the direct-link chain used during review.

## Source-aware aboutness and claims

- Full text may use strict recurrence/section-spread checks.
- Abstract-only sources are judged substantively without nonexistent-section requirements.
- Metadata-only records defer and trigger retrieval.
- Bare `EU` is not assumed to mean European Union without context.
- Display claims state what the source finds, argues, reports or projects without boilerplate prefixes.
- Directional keywords support matrix classification but are not mandatory gates.
- `quadrant_claimed` and `quadrant_implied` stay distinct; evidence-implied placement controls when available.

## State integrity

Manual ingestion is not a live scan. The bundled `last_updated` remains the authoritative supplied value **2026-08-25T10:58Z**, with scan cursors/history preserved. Manual review/ingest timestamps are stored separately.

## Validate

```bash
PYTHONPATH=. python -m pytest -q
```

Current complete suite: **251 passed**.
