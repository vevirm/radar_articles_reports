# Validation V17.13.21

This release removes the fixed issue taxonomy from the fast reader without changing scanner admission.

Validated contracts:
- `read/issues.js` parses and builds a non-empty live issue set from the bundled `radar.json`.
- On the bundled current state it produces nine leading issue maps; the count is not hard-coded and can vary within the reader's broad display bounds.
- `read/index.html` contains no fixed `ISSUE_MAP`; branches and subissues are built from current admitted evidence.
- The landing-page issue strip and minimum-read summary use the same live issue builder.
- Issue labels and source-backed findings pass through the shared plain-language reader boundary.
- Source merit only weights/orders already-admitted material.
- Scanner admission, Matrix placement, `radar.json`, source-merit Excel, security workflows and six-hour schedule are unchanged.
- Presentation smoke test passes without network discovery or a scanner run.
