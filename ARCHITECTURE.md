# Architecture — V17.5.6

The radar has three logically separate stages:

1. **Corpus admission** — decides whether A/B/C material belongs in the radar at all.
2. **Frontier classification** — decides whether an admitted/current signal is strong enough to occupy one of the 16 Sovereignty-Frontier cells.
3. **Scarcity-balanced discovery** — measures the 16 cell counts and gives additional discovery budget to under-covered cells without replacing normal source rotation.

## Frontier semantic contract

`frontier/frontier.js` is the canonical classifier. `scripts/frontier_coverage.js` invokes that exact module from the scanner, so browser display and scan prioritisation share the same occupancy logic.

Short acronyms are boundary-aware. Row scoring alone cannot fill a cell: after row/direction scoring, `cellEvidencePass()` requires a supported row mechanism plus evidence for the selected independence/competitiveness direction. Evidence-derived signals may use the underlying title/summary; weak signals must carry the mechanism themselves.

## Scarcity plan

`scripts/scan_radar.py::frontier_gap_plan()`:

- loads exact 4×4 counts;
- computes `deficit = max(0, target_count - count)` for every cell;
- sorts by deficit, rotating ties with `frontier_gap_cursor`;
- creates `weighted_targets`, where a deficit-3 cell gets three extra allocation turns, deficit-2 gets two, deficit-1 gets one;
- allocates bounded news, OpenAlex/Crossref and institutional overlay capacity;
- leaves the ordinary OpenAlex/Crossref/institution rotations intact.

The target count is configured in `radar_config.json` (`frontier_gap_target_count`, currently 3). No cell is permanently listed as a priority.

## State continuity

The V17.5.5 change does not expand the base source universe, so the existing source-expansion compatibility marker is retained. Current OpenAlex/Crossref/institution cursors and the Frontier gap cursor continue from the user's latest `radar.json`.


## V17.5.6 discovery-depth state

`scan_state` is extended without changing its v17.2 version marker. Three additive state families are initialized with `setdefault`, so an existing live checkpoint is not reset:

- `frontier_gap_query_cursors`: per-cell formulation position;
- `frontier_gap_source_cursors`: per-cell specialist-source position;
- `result_depth`: per-query/page state for OpenAlex, Crossref broad, and Crossref priority tasks.

Each scholarly query keeps a newest-results lane and a rotating depth lane. This preserves freshness while preventing recurring queries from repeatedly inspecting only the same top results.
