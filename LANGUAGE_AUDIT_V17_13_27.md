# Reader-language audit — V17.13.27

## Purpose

The radar now has an explicit language hierarchy. The aim is not to make every page equally simple. The same evidence should become easier or more technical according to the task of the page, while the underlying evidence and Matrix placement stay unchanged.

## Hierarchy

1. **Read at least this — simplest**
   - ordinary-language issue labels and findings;
   - short source-strength labels such as `Top source` rather than a score;
   - no placement confidence, screening score, claimed/implied quadrant, source-merit formula or admission diagnostics in the default reader view;
   - policy terms are translated when a common-language equivalent is available.

2. **Matrix and Risks & opportunities — simple analytical**
   - shorter language than the main Radar;
   - focuses on what Europe gains, loses, controls, pays for or relies on;
   - public rows: People & knowledge; Tools & facilities; Firms & growth; Rules & decisions;
   - public directions: More control, stronger; More control, some cost; Stronger, but reliant; Less control, weaker;
   - the full Matrix keeps technical placement diagnostics behind a secondary disclosure.

3. **Main Radar and Evidence browser — policy-technical**
   - standard EU R&I-policy language is allowed when it is the precise wording: research security, strategic dependency, technological sovereignty, scale-up finance, research infrastructure, talent circulation, etc.;
   - the Main Radar now prefers the validated stored core message before applying any plain-language fallback;
   - expandable record details preserve the source, summary, relevance/admission evidence and other context.

4. **Excel technical evidence workbook — most technical**
   - ranked source merit and its score components;
   - admission/review decision and technical radar claim;
   - EU/R&I/strategic evidence fields;
   - Matrix row, column, cell, evidence basis, placement confidence, screening score and questions;
   - discovery provenance, source review basis and source-text mode;
   - a separate 16-cell criteria sheet and method sheet.

## Boundary rule

Language transforms are downstream presentation only. They must not add a causal bridge, EU relevance, R&I mechanism, control/dependence direction or performance direction that is not already supported by the admitted record.

## Page checks performed

- `read/` uses `RadarInsights.readText` for generated findings and hand-authored simple issue labels for issue-tree headings.
- `frontier/quick/`, `frontier/` and `priorities/` use `RadarInsights.matrixText` for generated analytical findings.
- `index.html` uses `RadarInsights.radarText` and prefers the stored validated core message for main-Radar claims.
- `briefing/` is explicitly documented as the same policy-technical level as the main Radar.
- `stuff/` presents `source_merit_ranking.xlsx` as the technical evidence workbook, not a simplified reader view.

## Read-label cleanup

The live issue-tree labels were checked for double simplification. Labels such as `Rules, standards & rules`, `Chips & chips` and `Economic ability to compete` were replaced by authored simple labels: `Rules and standards`, `Chips`, and `Economic strength`. Acronyms such as AI and EU keep their normal capitalisation in generated issue summaries.

## Result

The hierarchy is now enforced by code and presentation smoke tests. Read is the simplest; Matrix/Priorities are deliberately simpler than the main Radar; the main Radar remains policy-technical; Excel carries the technical audit detail.
