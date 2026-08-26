# Validation — V17.12.3

## Site architecture

All four primary pages expose the same four primary components in the same order:

1. Read at least this
2. Main radar
3. Matrix
4. Risks & opportunities

`briefing/` remains available as a secondary Evidence browser and is not included in the primary navigation. Latest weak signals remains a local jump inside Main Radar rather than a fifth component.

## Progressive disclosure

- Main Radar: minimum-useful-read callout → component guide → full corpus.
- Read at least this: editorial synthesis + live top risk/opening/matrix pressure → deeper levels → evidence.
- Matrix: minimum-useful dynamic interpretation → highlighted signals → full 4×4 matrix → methodology.
- Risks & opportunities: top risk/opening pair → full ranked lists → underlying evidence.

## Scanner presentation

The homepage now says **Scanner · manual run only**, matching `.github/workflows/radar-scan.yml`, which is `workflow_dispatch` only. Dynamic status is labeled **Last run health** rather than implying continuous automation.

## Tests

- Full Python suite: **198/198 PASS**.
- Presentation smoke: **PASS**.
- `radar.json` hash is unchanged from V17.12.2.
- No discovery scan was run for this release.
