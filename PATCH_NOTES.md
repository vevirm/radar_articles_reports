# v17.19.34

- Restored the intended **Read at least this** section name everywhere. It is no longer a generic “Read” page.
- Rebuilt **Read at least this** as the chart-only minimum visual briefing. The four charts show the largest current issues, Matrix direction, affected R&I dimensions, and current risks/opportunities/external shocks. The issue-list replacement introduced in v17.19.33 has been removed from this page.
- Fixed strict scanner recognition of realised export-control shocks where an external actor is explicitly **barring exports with immediate effect**.
- The retained China event affecting 14 EU entities now files as a **Trade disruptions** external shock in scanner logic as well as in the reader interpretation.
- Updated the currently published `radar.json` so External shocks is **1 immediately**, without requiring another scan before the corrected release is useful.
- Kept the full-repository upload workflow: this package is intended to be uploaded over the previous repository in full.
- Validation: 186 main tests + 19 historical tests passed.

# v17.19.33

- Reframed the main current-affairs feed as **News** instead of a ten-item “Watchlist”. It combines recent journalism and relevant official developments, with major news sources prioritised in the ordering.
- Surfaced **External shocks** directly on the main Radar.
- Removed reader-facing scanner/process copy such as “new this scan”, scan-status explanations, admission/classification notes and point-length meta text.
- Expanded Matrix point text from 80 to **100 characters**, reduced initial bullet density, and opened up spacing.
- Added small line icons to Matrix row/column headers as visual cues.
