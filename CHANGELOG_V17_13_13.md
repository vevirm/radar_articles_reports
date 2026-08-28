# V17.13.13 — explicit “what it says” + simple bibliography workbook

## Radar cards

- The card heading is now the publication/source title rather than silently acting as the interpretation layer.
- Immediately before `Why it matters`, every Radar card now shows `What it says for EU R&I geopolitics`.
- The new line is validated across the current A/B/C corpus: non-blank, maximum 150 characters, complete sentence ending, and no ellipsis/hard cut.
- When extraction cannot yield a clean finding sentence, the fallback is an explicit grammatical description of what the source covers rather than a chopped title fragment.

## Stuff / Excel

- Replaced the old workbench-style Stuff page with a one-click bibliography page.
- Main action: `Download bibliography + summaries (.xlsx)`.
- The XLSX now opens directly on one sheet, `Bibliography`; there is no cover/read-me sheet.
- Removed Matrix row/outcome/cell codes, scores and setup instructions from the workbook.
- Workbook columns are: Publication, Authors, Date, Published in / by, Type, What it says for EU R&I geopolitics, Why you should care, Source link.
- The current workbook contains 234 deduplicated publications.
- The deployment bundle keeps only the simplified `bibliography_and_summaries.xlsx` workbook; the duplicate legacy workbook is omitted to keep the package small.
- Stuff retains BibTeX and RIS only as secondary reference-manager exports.

## Scope

No discovery scan was run. Admission, Matrix classification, priorities and scanner rotation are unchanged.
