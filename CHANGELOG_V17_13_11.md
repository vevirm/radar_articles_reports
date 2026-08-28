# V17.13.11 — publication-specific reader cleanup

This round fixes reader presentation and export quality without loosening evidence admission or changing the recurring rotation contract.

## Reader changes

- All eight **Read at least this** issue charts are visible immediately; they are no longer collapsible.
- Matrix candidates are deduplicated by canonical publication title/URL before classification, removing repeated PDF/landing-page versions.
- Quick and full Matrix entries use source-specific publication points. Full Matrix entries add a distinct explanation of the mechanism by which the publication matters.
- **Why it matters** never falls back to an empty line or to the same sentence as the claim. Matrix-specific explanations distinguish mechanisms such as compute access, research security, scale-up capital, industrial conversion, researcher mobility and science diplomacy.
- **Risks & Opportunities** uses topic diversification and a shorter decision list. Detail views show the actual publication and why that source matters.

## Stuff / exports

- The main export is a real `radar_exports.xlsx`, not CSV text with an Excel-like presentation.
- The workbook is publication-first: one row per deduplicated publication with `What it says`, `Why it matters for EU R&I`, Matrix placement, bibliographic metadata and source URL.
- A second workbook sheet contains only current Matrix evidence with the same source-specific language.
- The Stuff page previews publications directly and labels TSV downloads as TSV.

## Rotation check

The recurring multifactor rotation remains active. Rotation tests cover query-family rotation, depth rotation, sparse-cell recovery and priority-person interleaving. State cursors in the current corpus are non-zero and per-cell recovery/depth cursors are populated. A stale test that expected the old `v17.8.2-balanced-frontier` profile was updated to the current `v17.13.7-recurring-multifactor-rotation` profile; the rotation behavior tests themselves pass.
