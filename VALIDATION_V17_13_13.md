# Validation — V17.13.13

## Radar: “What it says for EU R&I geopolitics”

Validated against all 240 current public A/B/C records:

- 240/240 produce a non-blank `whatForEuRiGeo` line;
- 0 exceed 150 characters;
- 0 end as hard-cut fragments by punctuation contract;
- 0 contain ellipsis truncation;
- the line is rendered immediately before `Why it matters` on both ordinary evidence cards and weak-signal cards;
- publication/source title is used as the card heading, so the new explanatory line is not merely another unlabeled headline.

## Stuff / XLSX

- Main Stuff action is `Download bibliography + summaries (.xlsx)`.
- The Matrix filter/workbench controls have been removed from Stuff (`rowSelect`, `miniMatrix`, `downloadImportant` absent).
- `bibliography_and_summaries.xlsx` contains one worksheet only: `Bibliography`.
- The workbook opens at the publication table, with no cover/read-me sheet.
- 234 deduplicated publication rows are present.
- Columns are limited to bibliographic information, `What it says for EU R&I geopolitics`, `Why you should care`, and source link.
- The lean deployment bundle contains one Excel workbook only: `bibliography_and_summaries.xlsx`.
- Spreadsheet formula-error scan: no `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, or `#N/A` matches.

## Automated checks

- Targeted V17.13 feedback tests: **9 passed**.
- Presentation smoke: **PASS**, including Stuff inline JavaScript.
- Complete suite: **311 passed + 4 subtests**, 0 failures.

## Scope

No discovery scan was run. Radar corpus admission, Matrix placement, priority logic and scanner rotation were not changed.

## Lean deployment bundle

- Historical test source files and superseded changelog/validation files are intentionally excluded from the deployment ZIP.
- The deployed site, scanner, workflows, source data, and current bibliography workbook remain included.
- Bundle file count: 53 files, below the 100-file limit.
