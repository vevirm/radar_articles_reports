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

- `scripts/scan_radar.py` — main scan
- `historical/scan_historical.py` — historical scan
- `.github/workflows/radar-scan.yml` — main automation
- `.github/workflows/historical-scan.yml` — historical automation

## Tests

The main maintained regression suite is bundled inside `tests/all_tests.zip` and loaded by `tests/test_all.py`. The release also remains compatible with obsolete standalone tests that may have been left in an older repository by GitHub browser uploads.

Version: **v23.0-calm-working-radar**
