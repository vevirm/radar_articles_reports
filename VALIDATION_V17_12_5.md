# Validation — V17.12.5 reader-first language

## Automated checks

- JavaScript syntax: `briefing/insights.js`, `frontier/frontier.js`, and `priorities/priorities.js` pass `node -c`.
- Python scanner/ingestion code passes `python -m compileall -q scripts`.
- Focused regression and ingestion suite: **59 tests passed**.
- The four requested before/after examples are asserted at both the browser/display layer and the scanner write boundary.
- Matrix evidence candidates are asserted to reuse the same simplified claim layer.

## Source-detail preservation

The bundled `radar.json` was compared field-by-field before and after the reader-claim migration. Across `strand_a`, `strand_b`, `strand_c`, and `frontier_evidence`:

- **20 reader-facing claim records changed**.
- **0 source-detail fields changed** among title/headline, summary, authors, source, date, link, type, relevance note, why-it-matters, and anchor fields.

This means the prominent claim can be simplified while the original bibliographic and evidence detail remains available underneath.

## Future insertion rule

New records are simplified twice defensively:

1. when their reader-facing `core_message` is created or reviewed; and
2. in a final `normalize_reader_claims()` pass immediately before published radar data is written.

The same shared browser layer is used by the main radar and downstream evidence/matrix views, so a record that bypasses one creation path still receives the reader-first treatment when displayed and when the published corpus is normalized.
