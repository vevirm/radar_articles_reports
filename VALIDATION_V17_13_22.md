# V17.13.22 validation

Validated locally without running a network discovery scan:

- `python -m py_compile scripts/scan_radar.py scripts/manual_ingest.py scripts/build_briefing.py` — PASS.
- `node scripts/presentation_smoke.js` — PASS, including all principal reader pages and inline JavaScript syntax.
- Workflow YAML parsed with a YAML 1.2 parser — PASS.
- Due-gate boundary simulation — PASS: 5.99h skips; 6.00h and later run.
- Preservation comparison against the prior bundled radar and supplied `radar (38).json` — PASS: 3 A + 1 B expected 2026-04-28 age-outs, zero still-in-window A/B losses.

No fresh discovery scan was run while packaging this repair.
