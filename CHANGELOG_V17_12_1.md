# V17.12.1 — presentation-first repository repair

- Fixed the Insight Summary runtime failure: `frontier/index.html` no longer calls an undefined page-level `clean()` function.
- Separated `radar.json` loading errors from rendering errors so a JavaScript exception is not mislabeled as missing data.
- Made the first-upload repository presentation-first: pushes do **not** start the long scanner.
- `R&I Radar Scan` is manual-only in this package; run it later from GitHub Actions after the pages have been inspected.
- Added a fast push-time presentation smoke check that validates `radar.json`, JavaScript syntax and a real Insight Summary render against the bundled state without network discovery.
- Kept the supplied 26 Aug 2026 `radar.json` byte-for-byte unchanged.
