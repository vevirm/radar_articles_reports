# V17.12.1 — frontier page fix + scan pause

## Fix
- `frontier/index.html`: the V17.12.0 inline helper `claimText()` called `clean()`, which only
  existed privately inside `frontier.js` / `insights.js`. The page threw
  `ReferenceError: clean is not defined` inside `render()`, and the page-level catch-all
  reported it as "could not load radar.json" — the data file was never the problem.
  `clean` is now defined in the page's own script.
- Script cache-busting bumped to `?v=17.12.1` on all four pages so browsers fetch the fixed files.

## Scan pause
- New root file `SCAN_PAUSED`. While it exists, `.github/workflows/radar-scan.yml` skips
  dependency install, self-test, scan and commit on every trigger (push, schedule, dispatch).
  `radar.json` stays exactly as supplied. Delete the file and push to resume scanning.

## State
- `radar.json` is the supplied 26 Aug 2026 radar (23).json, unchanged. No scan was run.
- Build artefacts (`__pycache__`, `.pytest_cache`) removed from the bundle.
