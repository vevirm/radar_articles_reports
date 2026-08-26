# R&I Geopolitics Radar V17.12.2

V17.12.2 keeps the presentation-first V17.12.1 build and adds bounded round-aware manual ingestion plus an exact-link reviewed recovery batch for rounds IV–VI. The bundled state is rendered immediately on first upload; repository pushes do not start a live scan. The live scanner is manual-only in this package so the pages can be checked before spending ~20 minutes on discovery. It also preserves the V17.12 reader-first presentation behavior: It keeps the evidence/matrix logic intact while changing what the user sees first: a complete plain-English proposition, then bibliography, with the abstract/evidence revealed on click. It also suppresses non-English display prose rather than promoting it as a headline.

## First upload: presentation first, scan later

This package intentionally treats the first GitHub upload as a presentation check, not a discovery run. `radar.json` is already bundled and is the data source for all pages. A push runs only the fast **Presentation smoke check** workflow. The expensive **R&I Radar Scan** workflow runs only when manually started from GitHub Actions.

Recommended order:

1. Upload the repository and let GitHub Pages publish the bundled state.
2. Open the main page, Insight Summary, Opportunities & Risks, and Radar Insights.
3. Confirm the presentation is correct.
4. Only then run **Actions → R&I Radar Scan → Run workflow** when a fresh scan is actually wanted.

No live scan was run while making this repair.

## Read-this-first subpage

`read/` is a deliberately simpler progressive-disclosure view of the same bundled corpus. It shows the main conclusion first, then three structural points. Reasoning opens on demand, and source evidence sits one level deeper. Four live shifts and three slower conditions remain collapsed until requested. The page is editorial synthesis; `radar.json` and the detailed reader pages remain the traceable record.

## Manual candidate ingest

```bash
python scripts/manual_ingest.py path/to/candidates.docx --state radar.json
```

Accepted inputs: DOCX, PDF, CSV, JSON, YAML/YML, TXT and Markdown. `--links-validated` records curator-tested reachability without treating reachability as substantive verification. `--no-fetch` is safe for comparison/registration; reviewed evidence can also be supplied with `--review-evidence PATH.json` when it is cryptographically/reproducibly tied to the exact supplied record URLs.

The lane extracts bibliography and URLs, deduplicates conservatively, retrieves the exact supplied source where possible, and evaluates the same substantive requirement as automated discovery: **genuine EU/European R&I in geopolitical context**. Metadata-only material defers. Secondary, uncertain, forthcoming and context-only records remain distinguishable.

A reviewed evidence cache is not a free-form manual override: each review must be URL-bound to the curator-supplied URL, source-verified, and explicit about its evidence mode/status. Primary-source resolution is permitted only when the supplied record itself needs it, while preserving the original supplied URL in provenance.

## Matrix-oriented manual lists

Curator cell mappings are stored as hypotheses, not answers. A reviewed source can be admitted when its underlying evidence passes the substantive gate; matrix placement then comes from reviewed source evidence (`matrix_dimension`, `quadrant_claimed`, `quadrant_implied`). The frontend honors that reviewed row/column instead of re-inferring the row from topic keywords.

Earlier reviewed supplements remain intact. V17.12.2 additionally ingests the declared **58-item rounds IV–VI block** from `EU_RI_Found_Items_Rounds_IV-VI.docx`: **10** new substantive items enter the radar and **7** receive independently reviewed matrix placements. The detailed batch decisions are in `MANUAL_INGEST_REPORT_ROUNDS_IV_VI.md`; earlier supplement decisions remain in `MANUAL_INGEST_REPORT.md`.

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

Manual ingestion is not a live scan. V17.12.2 starts from the user-supplied 26 August 2026 state and preserves its scanner timestamp (`last_updated`: **2026-08-26T08:57Z**) and scan cursors. The rounds IV–VI review is recorded separately under `manual_ingest.last_ingested_at` / batch history; no live scanner run was claimed or performed.

## Validate

```bash
PYTHONPATH=. python -m pytest -q
```

See `VALIDATION_V17_12_2.md` for the current manual-ingest/state validation. `VALIDATION_V17_12_1.md` and `VALIDATION_V17_12.md` remain the historical presentation/readability records.
