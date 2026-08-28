# V17.13.18 — latest scan + source merit workbook in Stuff

- Replaced bundled `radar.json` byte-for-byte with the user-supplied `radar (37).json` scan state (`last_updated` 2026-08-28T20:50Z).
- Kept the V17.13.17 security-hardened workflows and 6-hour schedule unchanged.
- Kept scanner admission, scoring, Matrix classification, source rotation, evidence and reader logic unchanged.
- Replaced Stuff's downloadable bibliography workbook with `stuff/source_merit_ranking.xlsx`.
- The workbook opens directly on `Ranked sources` and contains 255 publication-level deduplicated records from the current radar.
- Ranking is deliberately practical for this radar: official EU primary sources first, then major public/multilateral bodies, strong journals and policy institutes, broader peer-reviewed sources, specialist/current-event sources and preprints.
- Each row shows the journal/outlet or institution behind the report, author(s), quality/reputation assessment, plain-English relevance, evidence type, scanner source tier, source URL and selected reputation-reference URL.
- Merit score is transparent: source authority + EU R&I relevance + evidence strength + author transparency. The workbook is an export/reference aid and is not read by the scanner.
