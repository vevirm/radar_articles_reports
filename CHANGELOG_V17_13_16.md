# V17.13.16 — plain fast-reader wording + 6-hour scans

- Replaced contextual glossary help in `Read at least this` and `Risks & opportunities` with direct plain-language wording.
- Applied the same plain-language display boundary to `Matrix · short`, including bullets, row/column wording, cell labels and scan-status text.
- Source titles, links, evidence text, Matrix classification and underlying data remain intact; the simplification is a reader-layer transformation.
- Added a shared `fastReaderText()` helper for recurring specialist terms so new scan results are simplified on the three fast-reader pages without rewriting the source record.
- Changed the GitHub Actions scan schedule from every 12 hours to every 6 hours (`17 */6 * * *`).
- Copied the supplied `radar (36).json` byte-for-byte into `radar.json`.
