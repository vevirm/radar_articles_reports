Radar v26.1 quick fix

Changes:
- Radar display strips source-site "Download" wrappers from titles/WHAT lines at render time only.
- Radar action labels simplified to Evidence / Source / Details.
- Earlier Findings suppresses generic repeated WHY boilerplate when it adds no item-specific information.
- Matrix WHY copy is row-specific rather than repeating the same generic phrases.
- Risks/Opportunities unmatched titles fall back to the actual evidence message rather than repeated generic templates.
- Strand C high-trust source anchoring has modestly higher recall while a substantive Strand-A anchor remains mandatory.

Not changed:
- Strand A admission or protected discovery priority.
- Strand B evidence role or method admission rules.
- C analytical weight (0.30), 60-day retention, or A-anchor requirement.
- Workflows, tests, radar.json, scan state, historical data.

Validation:
- pytest: 68 passed, 33 skipped, 0 failed.
- unittest discovery: 168 run, 66 skipped, 0 failed.
