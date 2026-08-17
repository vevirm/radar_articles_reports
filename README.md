# R&I × Geopolitics + Foresight Methodology Radar

A GitHub Pages radar that scans for EU-relevant R&I/geopolitics publications, foresight-methodology work, and anchored weak-signal news.

## What this version changes

The scanner is **not a keyword classifier**. Final discovery and acceptance/rejection are handled by the OpenAI Responses API with its built-in `web_search` tool, using `gpt-5.6` and the full `radar_criteria.md` instructions.

This is designed to prevent false positives such as research calls, facilities, technical pages, or generic EU documents that merely mention third-country participation. Strand A requires substantive R&I-policy **and** geopolitical content. Strand B must be genuinely methodology-first. Strand C is searched only after A/B anchors exist.

## Scan order

1. Web-research pass for Strand A, date floor 2026-04-01.
2. Web-research pass for Strand B, date floor 2026-04-01.
3. Mechanical validation and requested ranking.
4. Maintain a bounded A/B history and recurring-theme anchors.
5. Web-research pass for current-window Strand C against those anchors only.
6. Write `radar.json`; GitHub Pages is rebuilt automatically.

## Automation

- **Immediate first scan:** any upload/commit to `main` triggers the workflow.
- **Scheduled:** 00:17 and 12:17 UTC every day (12 hours apart).
- **Manual:** Actions → R&I Radar Scan → Run workflow.

## One required secret

The repository is public, so an API key must **never** be stored in a file. Before the first upload/commit, add a GitHub Actions repository secret named:

`OPENAI_API_KEY`

Path in GitHub: **Settings → Secrets and variables → Actions → New repository secret**.

The workflow passes that secret only to the scanner process. The webpage never receives it.

## Files

- `index.html` — password-gated public page.
- `radar.json` — live results read by the page.
- `radar_criteria.md` — the full selection criteria.
- `scripts/scan_radar.py` — three-pass semantic web-research scanner.
- `.github/workflows/radar-scan.yml` — immediate + 12-hour automation.
- `WORKFLOW_BACKUP/radar-scan.yml` — visible backup if a file uploader omits `.github`.

## Important limitations

The password screen is a lightweight deterrent for casual visitors, not true access control: GitHub Pages and this public repository remain technically accessible. Web search and model output can still make mistakes, so the scanner includes additional mechanical checks and is instructed to prefer false negatives over false positives. It never pads a strand.
