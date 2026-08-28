# Validation V17.13.20

This release carries the Stuff source-merit ranking into the reader and decision views without changing scanner admission or Matrix placement.

Validated contracts:
- `source_merit.js` parses and scores live radar records with the same score bands used by the Stuff workbook.
- Current top-scoring records reproduce the workbook logic: official EU sources score at the top, followed by major public bodies, strong journals and policy institutes, then ordinary peer-reviewed/specialist/current-event material.
- Main Radar, Read at least this, Evidence browser, Matrix short, Matrix full, Risks & opportunities, Literature used and Stuff all load the shared source-merit layer and visibly surface evidence weight.
- Matrix signals retain their existing row/column classification; source merit is attached only as evidence weight and as a display-order tie/secondary factor.
- Risks & opportunities still derive from the Matrix; source merit contributes to priority ordering but does not create a risk or opportunity by itself.
- Read at least this still requires issue relevance first; source merit only ranks relevant candidate evidence.
- Presentation smoke test passes for radar JSON parsing, shared modules, page JavaScript syntax, fast-reader wording and source-merit integration.
- `radar.json`, `stuff/source_merit_ranking.xlsx`, scanner code, scan configuration, requirements and GitHub security workflows are unchanged from V17.13.19.
