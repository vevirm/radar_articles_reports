# R&I Geopolitics Radar V17.12.0

V17.12.0 is a reader-first presentation update built on the supplied 26 August 2026 radar state. It keeps the evidence/matrix logic intact while changing what the user sees first: a complete plain-English proposition, then bibliography, with the abstract/evidence revealed on click. It also suppresses non-English display prose rather than promoting it as a headline.

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

Manual ingestion is not a live scan. The bundled `radar.json` is the user-supplied 26 August 2026 state (`last_updated`: **2026-08-26T02:00Z**). This presentation build does not run a new scan or alter scanner bookkeeping beyond replacing the bundled state with that supplied file.

## Validate

```bash
PYTHONPATH=. python -m pytest -q
```

See `VALIDATION_V17_12.md` for the presentation-build validation against the newer supplied state.

## Current scan mode: paused

This repository is intentionally packaged in **no-auto-scan hold mode**. Committing or uploading files does not invoke the scanner: `.github/workflows/radar-scan.yml` contains only `workflow_dispatch` and has no `push` or `schedule` trigger. The current `radar.json` therefore remains unchanged until a scan is deliberately started later.
