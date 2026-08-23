# Validation — V17.6.3

- Core-message acceptance repairs/rejects letter-spaced PDF/OCR text; spaced-letter artefacts cannot render as the 120-character message.

Validated against the supplied `radar (9).json`.

- Supplied state: A=41, B=35, C=5.
- Revalidated B under the futures-method-as-such gate: B=1; 34 method-use/domain-prediction records removed.
- Retained B item: *Forest pests on the move: Adapting horizon scanning methodology to assess climate-driven range expansion in forest pests*.
- A and C were not altered by this migration.
- Complete persisted `scan_state` preserved.
- Main-card headline generator enforces a 120-character maximum and keeps paper titles in bibliography rather than as the headline.
- Risks & Opportunities contains a Go back control and plain-language direction statements.
- Test suite: 151/151 pytest tests passing before packaging.
