# R&I Radar v17.18.0

## Workflow jam removed without weakening the persistence boundary

- Main and historical scanners still have a strict persistence allowlist: the main job stages/commits only `radar.json`; the historical job stages/commits only `historical/historical.json`.
- A test runner, parser, cache or other runtime process changing another working-tree file can no longer throw away an otherwise completed scan. Such changes are logged as warnings and are never staged.
- The substantive corpus-integrity checks on `radar.json` remain in place. This change removes the fragile *working-tree cleanliness* kill switch, not the evidence/corpus safety checks.
- Main scanner is a true four-hour rotation at 00:17/04:17/08:17/12:17/16:17/20:17 UTC with no hidden 6-hour age gate.
- Historical scanner is a true four-hour rotation, offset at 02:41/06:41/10:41/14:41/18:41/22:41 UTC, with `HISTORICAL_MIN_RUNTIME_SECONDS=0`.

## Reader pages are live views of the Main Radar

- Every evidence-bearing reader page now reads the current root `radar.json` with cache-busting/no-store behaviour: Main Radar, Read at least this, topic briefing, Matrix (full and quick), Risks & opportunities, Sources and Stuff.
- The old static topic briefing was replaced. It no longer carries a generated-at snapshot that can drift from the Main Radar; it rebuilds from the current A/B/C corpus whenever the page loads.
- GitHub Pages is still explicitly rebuilt after a successful Main or Historical scan.
- Glossary remains intentionally static because it is definitions, not evidence. Historical remains intentionally based on `historical/historical.json` because it is a separate archive.

## Evidence quality controls height, not admission

- Source quality remains the shared `source_merit.js` rubric documented in Stuff: authority + EU/R&I relevance + evidence strength + author transparency.
- Read at least this, Matrix and Risks & opportunities already use that rubric after substantive qualification; those paths are retained.
- Topic briefing and Sources now also put stronger admitted evidence first.
- Stuff continues to show the technical quality ranking/export from the same current Main Radar corpus.
- No page can admit evidence because a source is prestigious. The scanner's substantive A/B/C gates still decide what enters the corpus; quality only ranks already-admitted material.

## Release completeness

- `scripts/build_release.py` now includes the machine-readable phrase ontology and its workbook, plus the reader/workflow regression tests, so a future lean release cannot silently omit files the scanner actually uses.

