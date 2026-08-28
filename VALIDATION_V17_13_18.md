# Validation — V17.13.18 latest scan + source merit workbook

## Current radar data

- `radar.json` parses as valid JSON.
- It is byte-for-byte identical to the supplied `radar (37).json`.
- SHA-256: `c6d827d4f533d4efb8271b5d26f41ca570dc43f1271434625a438537f8111645`
- `last_updated`: 2026-08-28T20:50Z
- Counts: A=224, B=25, C=14, frontier_evidence=0.

## Scanner/security isolation

- `scripts/scan_radar.py` is unchanged from V17.13.17.
  - V17.13.17 SHA-256: `ca72f96e83f1851cec80f613f6261711ba4adb9b8eb3ef9b1d97ac567bb2c1c3`
  - V17.13.18 SHA-256: `ca72f96e83f1851cec80f613f6261711ba4adb9b8eb3ef9b1d97ac567bb2c1c3`
- The security-hardened scheduled workflow is unchanged from V17.13.17.
  - V17.13.17 SHA-256: `aca720bad6da2a77ab8f3e9e67520436305ae611c934cedc2fbbc6e542820d5e`
  - V17.13.18 SHA-256: `aca720bad6da2a77ab8f3e9e67520436305ae611c934cedc2fbbc6e542820d5e`
- The schedule remains `17 */6 * * *` (every 6 hours).
- Scanner configuration, dependencies, Matrix classification and reader logic were not changed.

## Source merit workbook

- File: `stuff/source_merit_ranking.xlsx`
- SHA-256: `5df1ffeb2535e19aac793a2c7e2455ada7df0526fca7be8a716c4903dc9f7bfa`
- 255 publication-level deduplicated records.
- Merit bands: A=16, B=61, C=145, D=23, E=10.
- Formula/error scan found no `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?` or `#N/A` errors.
- Workbook was re-imported and rendered successfully after export.
- The workbook is not read by the scanner and cannot change admission or Matrix results.

## Presentation checks

`scripts/presentation_smoke.js` passes with the refreshed corpus, including:
- radar JSON parse and A/B/C counts;
- reader JavaScript syntax;
- Matrix, evidence-browser and risks/opportunities builders;
- direct plain-language wording in the three fast-reader views;
- Stuff page JavaScript syntax.
