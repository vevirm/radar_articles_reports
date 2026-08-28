# V17.13.21 — live Read-at-least-this issues

- Removed the fixed public eight-issue structure from `Read at least this`.
- Added `read/issues.js`, a downstream reader-layer issue builder that recomputes the visible issue set from the current admitted radar material.
- The visible issue count, selection, order, branches and current subissues can change after each successful scan.
- Branch subissues are current source-backed findings rather than fixed explanatory text.
- The landing-page issue strip and minimum-read summary now use the same live issue builder.
- Source merit remains a weighting/tie-break layer only; it does not change scanner admission, corpus membership or Matrix placement.
- Scanner code, scan configuration, source-merit workbook, security limits, credential separation and six-hour schedule are unchanged from V17.13.20.
