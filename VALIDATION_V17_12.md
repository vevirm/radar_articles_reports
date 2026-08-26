# V17.12.0 reader-first validation

This build uses the user-supplied `radar (23).json` as the bundled state.

## State used

- `last_updated`: **2026-08-26T02:00Z**
- Strand A: **141**
- Strand B: **23**
- Strand C / weak signals: **16**

## Reader-facing checks

- Main radar cards show the **message/idea first**, then bibliography.
- Clicking the message reveals the stored abstract/evidence and source link.
- Insight Summary uses the same complete reader-first claims rather than clipped `core_message` fragments.
- Risks & Opportunities uses specific evidence claims, not generic quadrant boilerplate, and displays the strongest eight items per side.
- The two requested rewrites resolve to exactly:
  - `The EU's first CRMA list includes no Bulgarian projects — outdated data, slow permits and low trust keep it out.`
  - `The EU says its new trade rules protect the climate. Trading partners say they protect EU industry.`
- Display claims are not published with trailing ellipses. If a complete short proposition cannot be formed, the item is omitted from the reader-facing insight layer rather than shown as a chopped sentence.
- A display-language guard suppresses clearly non-English prose as a headline; non-English bibliographic titles are not promoted in cards.

## Automated checks

- JavaScript syntax checks: **PASS** for `briefing/insights.js`, `frontier/frontier.js`, and `priorities/priorities.js`.
- Focused UI / priority / source-aware matrix tests: **14 passed**.
- Full repository suite against the newer supplied state: **248 passed, 3 failed**.

The three remaining failures are legacy state assertions, not presentation regressions: one test expects exactly 14 weak signals (the supplied state has 16), and two tests require the current gap plan to include an `-A` target even though the newer supplied matrix state no longer does so.
