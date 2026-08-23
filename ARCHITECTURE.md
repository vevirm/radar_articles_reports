# Architecture — V17.5.11

The radar has four logically separate stages:

1. **Rotating discovery** — queries/sources/pages are sampled with persistent independent cursors.
2. **Corpus admission** — decides whether A/B/C material belongs in the radar.
3. **Frontier classification** — decides whether admitted/current evidence supports one of the 16 Sovereignty-Frontier cells.
4. **Scarcity-balanced discovery** — measures the 16 cell counts and gives additional discovery budget to under-covered cells without replacing normal rotation.

## Persistent rotation contract

`scripts/scan_radar.py` stores rotation state in `radar.json::scan_state`. The V17.5.11 quality repair does **not** reset this state. Independent cursor families include:

- `openalex_cursor`;
- `crossref_broad_cursor`;
- `crossref_priority_cursor`;
- `strand_b_method_cursor` for the dedicated methodology-first lane;
- `institution_cursor`;
- `frontier_gap_cursor`;
- `frontier_gap_query_cursors` per cell;
- `frontier_gap_source_cursors` per cell;
- `result_depth` per scholarly query/task so fresh-result and deeper-page lanes both rotate.

The source-expansion compatibility marker remains unchanged, so a quality-profile migration cleans/reclassifies evidence without restarting source traversal.

## Strand B lane

The dedicated B lane rotates method-first queries (Delphi, horizon scanning, weak signals, scenario-method construction, backcasting, morphological analysis, foresight evaluation, etc.). Discovery terms are only candidate generators; final admission still requires the methodology-first B gate. This prevents query terms such as `scenario`, `framework`, `assessment` or `R&D` from becoming admission shortcuts.

## Frontier semantic contract

`frontier/frontier.js` is the canonical classifier. `scripts/frontier_coverage.js` invokes that exact module from the scanner, so browser display and scan prioritisation share the same occupancy logic.

Short acronyms are boundary-aware. Row scoring alone cannot fill a cell: after row/direction scoring, `cellEvidencePass()` requires a supported row mechanism plus evidence for the selected independence/competitiveness direction. The Knowledge row includes explicit A/B/C/D semantics for talent attraction/retention, security-cost tradeoffs, productive reliance on foreign expertise and research-talent loss.

## Scarcity plan

`scripts/scan_radar.py::frontier_gap_plan()`:

- loads exact 4×4 counts;
- computes `deficit = max(0, target_count - count)` for every cell;
- sorts by deficit, rotating ties with `frontier_gap_cursor`;
- creates weighted targets so larger deficits receive more allocation turns;
- rotates per-cell query formulations and specialist sources with their own saved cursors;
- allocates bounded news, OpenAlex/Crossref and institutional overlay capacity;
- leaves the ordinary OpenAlex/Crossref/priority/institution and B-method rotations intact.

The target count is configured in `radar_config.json` (`frontier_gap_target_count`, currently 3). No cell is permanently listed as a priority.

## Quality-profile migration

A change in `quality_profile_version` triggers a one-time inherited A/B audit under the current gate. Thin saved evidence is refreshed where possible; records that cannot pass the repaired gate fail closed. This migration is a corpus-quality operation only: persistent scan cursors continue from the supplied state.
