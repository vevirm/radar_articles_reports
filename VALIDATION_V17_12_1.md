# V17.12.1 presentation-first validation

This repair is deliberately **not a scan build**. It validates the already-bundled 26 August 2026 state and the reader pages before any new discovery run is started.

## First-upload behavior

- `R&I Radar Scan` is `workflow_dispatch` only: no push trigger and no schedule in this package.
- `Presentation smoke check` runs on push and performs only local repository validation; it never calls `scan_radar.py` or does network discovery.
- GitHub Pages can therefore render the bundled `radar.json` first. A live scan is started later only by **Actions → R&I Radar Scan → Run workflow**.

## State integrity

The packaged `radar.json` is byte-for-byte identical to the supplied `radar (23).json`.

- SHA-256: `721f97b4d476bd3744663dc4e22be0b582fc272a23fd6c74032bf97bcc0c36c0`
- `last_updated`: **2026-08-26T02:00Z**
- Strand A: **141**
- Strand B: **23**
- Strand C: **16**

## Insight Summary repair

The failure shown in the uploaded screenshot was a frontend exception after data had already loaded. The page-level `claimText()` called an undefined `clean()` function. V17.12.1 makes that function self-contained and separates data-loading failures from rendering failures, so a later JavaScript exception is no longer mislabeled as a missing `radar.json`.

## Runtime results against the bundled state

A DOM render harness executed the actual reader HTML/JavaScript with the bundled state:

- Insight Summary: **101 qualifying signals** = **28 openings**, **26 trade-offs**, **27 dependencies**, **20 double-loss alarms**.
- Insight Summary rendered **3** takeaway cards, **7** top signals and all **16** matrix cells with no console/page error.
- Opportunities & Risks rendered **8** risks and **8** opportunities with no error.
- Radar Insights rendered **106** papers, **26** reports and **15** displayable weak signals with no error.

## Automated checks

```bash
node scripts/presentation_smoke.js
PYTHONPATH=. pytest -q tests/test_insights_page.py tests/test_v17_3_sovereignty_frontier.py tests/test_v17_9_source_aware_matrix.py
```

Results: presentation smoke **PASS**; focused Python suite **19 passed**. No scanner was executed.
