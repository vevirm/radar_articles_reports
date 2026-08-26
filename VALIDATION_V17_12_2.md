# V17.12.2 validation

Date: 2026-08-26

## State integrity

- Base scanner timestamp preserved: `2026-08-26T08:57Z`.
- `scan_state` cursors preserved from the supplied state; manual ingest is recorded separately.
- Final corpus: **152 Strand A / 23 Strand B / 17 Strand C**.
- Latest manual batch: `0f1a8c55c834-9b0296a6` with **58** records and **10** new substantive admissions.

## Manual-ingest controls

- Exact supplied URL remains the binding key for reviewed evidence.
- No search-engine/general title discovery exists in the manual retrieval path.
- Secondary/incomplete and metadata-only records defer.
- Retrieval/environment failures are not converted into relevance rejection.
- Curator cell hints remain separate from evidence-derived matrix placement.
- Claimed and implied quadrants remain separately representable.

## Tests

- `python -m pytest -q` → **255 passed**.
- `node scripts/presentation_smoke.js` → **PASS**; radar parsed at 152 A / 23 B / 17 C and all reader JavaScript syntax/build checks passed.
- No live discovery scan was run.
