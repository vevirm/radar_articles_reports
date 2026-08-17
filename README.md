# R&I × Geopolitics + Foresight Methodology Radar

EU-first, automatically updated GitHub Pages radar.

## What this repository does

- Runs a first scan immediately when the repository files/workflow are committed to `main`.
- Runs again every 12 hours via GitHub Actions.
- Requires no OpenAI key and no paid API.
- Discovers candidates through OpenAlex, Crossref, whitelisted institutional websites/sitemaps, and a whitelist-only current-news layer.
- Applies strict admission gates before anything is shown publicly.
- Writes accepted results to `radar.json`.
- Requests a GitHub Pages rebuild after each scan so fresh results become visible on the site.
- Keeps accepted A/B publications as a cumulative corpus; Strand C is a current-window signal layer.

## Important classification design

The scanner does **not** use a simple keyword score as the admission rule.

### Strand A

All must pass:

1. substantive R&I/science/technology **policy** content
2. substantive geopolitics/economic-security content
3. an explicit textual bridge between 1 and 2
4. direct or explicit derived EU relevance

Calls, funding notices, project pages, facility/laboratory pages, ordinary institutional news, events, jobs, blogs and opinion/commentary are hard-rejected.

### Strand B

Foresight must be methodology-first. The publication must discuss how foresight/scenarios/horizon scanning/anticipatory governance is designed, evaluated, institutionalised or integrated with other methods. A trend report or scenario output alone does not qualify.

### Strand C

Factual current-window news from the whitelist only. Every item must anchor to an accepted A/B publication or recurring A/B theme. No anchor means no inclusion.

The full human-readable standard is in `radar_criteria.md`.

## Password gate

The page uses the simple casual-visitor password gate requested for this radar. Password: `TutuRadar2026?`

This is not server-side security; the repository and `radar.json` remain public because the site is hosted as a public GitHub Pages project.

## Expected GitHub Pages address

`https://vevirm.github.io/radar_articles_reports/`

Keep Pages configured as:

- **Deploy from a branch**
- Branch: `main`
- Folder: `/(root)`

## Workflow

The active workflow must exist at:

`.github/workflows/radar-scan.yml`

A visible backup copy is also included at:

`WORKFLOW_BACKUP/radar-scan.yml`

This backup is included because some Windows upload workflows can make the dot-prefixed `.github` directory easy to miss.
