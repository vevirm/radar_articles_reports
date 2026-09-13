# Research & Innovation × Geopolitics Radar

Static GitHub Pages reader plus automated research scanners.

## Reader paths

- `/` — simple start page: briefing, Radar, or deeper analysis
- `/read/` — shortest useful briefing
- `/radar/` — searchable current evidence
- `/explore/` — question-led route into Matrix, Trends, phenomena, risks, shocks, history, sources and methods

## Data

- `radar.json` — live/current corpus
- `historical/historical.json` — older evidence kept separate from current signals

## Scanners

- `scripts/scan_radar.py` — main automatic scan
- `historical/scan_historical.py` — historical scan
- `.github/workflows/radar-scan.yml` — main automation
- `.github/workflows/historical-scan.yml` — historical automation
- `scripts/prepare_deep_scan_package.py` — builds one self-contained backlog-aware Deep Scan ZIP; no model API is called
- `scripts/import_deep_scan_results.py` — validates returned Deep Scan JSON/ZIP files and safely merges the reader sidecar
- `scripts/deep_read_works.py` — shared record/source/validation helpers; no model API calls
- `.github/workflows/reader-language.yml` — **Deep Scan — Prepare Package** manual file-export workflow
- `.github/workflows/deep-scan-import.yml` — automatically validates/imports files uploaded to `deep_scan_inbox`

The automatic scanner remains the fast path. Deep Scan is an offline file rotation: GitHub prepares a ZIP, a user-provided LLM subscription reads it, and GitHub validates the returned file into the optional `reader_text.json` semantic sidecar. No paid model API key is required. See [`DEEP_SCAN_SETUP.md`](DEEP_SCAN_SETUP.md).

## Tests

The main maintained regression suite is bundled inside `tests/all_tests.zip` and loaded by `tests/test_all.py`. The release also remains compatible with obsolete standalone tests that may have been left in an older repository by GitHub browser uploads.

Version: **v23.0-calm-working-radar**
