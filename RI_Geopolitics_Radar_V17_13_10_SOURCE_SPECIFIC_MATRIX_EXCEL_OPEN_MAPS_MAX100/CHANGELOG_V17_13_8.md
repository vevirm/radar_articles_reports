# V17.13.8 — Stuff workbench: exports + priority publications

- Adds a separate `Stuff` utility page without changing the main reader flow.
- Adds live Matrix CSV export for the whole Matrix, any row, any column or one exact cell.
- Adds a packaged Excel workbook with separate tabs for the full Matrix, four rows, four columns and all 16 cells.
- Adds bibliography export as CSV, BibTeX and RIS.
- Adds a “Most important publications” attention list. Primary/official EU acts and reports rank above secondary reporting when the primary source is present; strong peer-reviewed research and strategic policy research follow.
- Importance ranking combines source authority, evidence quality, R&I/geopolitical materiality and freshness. It is explicitly separate from admission.
- Keeps the permanent Matrix-balance rotation from V17.13.7 unchanged.
- Reader palette remains black, white and red.


## V17.13.9 — source-bound “why it matters”

- Replaced reusable topic-level “why it matters” templates with per-record extraction from source summaries, reviewed evidence and source-bound core messages.
- Generic phrases such as “EU research funding and international partnerships may change” and “European access to key technologies and innovation capacity may change” are no longer reader fallbacks.
- A “why it matters” line is omitted when no separate source-grounded consequence fits the 120-character reader contract.
- Full Matrix cards use the same source-bound consequence logic before any Matrix rationale fallback.
- Radar data, admission, rotation, Matrix placement and scan state are unchanged. No network scan was run.

## V17.13.10 — source-specific Quick Matrix + Excel-safe Stuff + open issue maps

- Replaced Quick Matrix quadrant boilerplate with publication-bound short points derived from each source.
- Quick Matrix groups exact duplicate source-version points while the full Matrix keeps every qualifying source record.
- Thin Matrix cells are visibly marked as rotation priorities; current evidence is not deleted, reassigned or padded to fake balance.
- `Read at least this` opens all eight issue maps on arrival; readers can still close or reopen all maps.
- Stuff live spreadsheet exports are tab-separated `.tsv` files with a UTF-8 BOM so Excel opens columns correctly under comma-decimal / semicolon-list locales.
- Stuff Matrix exports now include source quality, EU relevance, source finding, evidence status and a source-backed `Why this cell` field. Where no saved source-backed cell rationale exists, that field is blank rather than generic.
- Rebuilt the packaged XLSX workbook with the same source-specific Matrix points and source-backed rationale rule.
- No scan was run. Radar data, Matrix classification/admission logic and scan rotation logic are unchanged.
- Stuff priority-publication cards no longer repeat ranking boilerplate; each card shows a publication-specific point, with the Matrix cell kept as a separate tag where relevant.
