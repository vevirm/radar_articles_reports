# Validation — V17.13.27

## State

- `radar.json`: 186 Strand A / 24 Strand B / 14 Strand C.
- Matrix production classifier: 38 qualifying findings.
- No discovery scan was run while producing V17.13.27.

## Matrix semantic contract

`node scripts/test_matrix_semantic_contract.js`

Result: **31/31 fixtures passed**. The fixtures cover all 16 cells, widened legitimate mechanisms (including external talent/research networks, shared/diversified infrastructure, outside scaling inputs and foreign-rule-dependent access) and false positives that must remain unclassified.

## Presentation/runtime smoke

`node scripts/presentation_smoke.js`

Result: passed. Checks include:

- all shared JS modules and inline page scripts parse;
- live Read issue builder produces a current issue set;
- Evidence browser, Matrix and Risks & opportunities build from current data;
- source merit is available across reader views;
- Read uses the simplest-language boundary;
- Matrix/Priorities use the simple-analytical boundary;
- full-Matrix technical diagnostics are secondary;
- main Radar uses the policy-technical boundary;
- Stuff identifies Excel as the technical evidence layer;
- scanner output persists `presentation_profile_version` and `reader_language_profile_version`.

## Excel workbook

`stuff/source_merit_ranking.xlsx` was regenerated with `artifact_tool` and contains four sheets:

- `Ranked sources` — 216 deduplicated sources with merit components and window class;
- `Technical evidence` — full technical/admission/Matrix fields;
- `Matrix criteria` — the 16-cell contract plus false-positive exclusions;
- `Method` — reader-language hierarchy, time window, English/external-relevance rules and source-merit method.

Targeted workbook inspection found no formula-error markers. Key ranges were rendered for visual inspection after formatting.

## Data integrity

This release changes presentation, documentation, Matrix criteria/classification code already audited in V17.13.26, and the technical workbook. It does not intentionally delete or add radar evidence. The 4-month normal / Highest-to-6-month rule is unchanged.
