# R&I × Geopolitics Radar

## Radar Insights (V9)

The main radar and scanner remain the source of truth. `/briefing/` reads `radar.json` directly and presents only topical headings with concise signal bullets. The Insights transformer synthesises one clear point from each admitted radar item instead of copying report prose. It filters PDF/OCR debris, metadata, methodology headings and generic article-purpose language; items that cannot yield a clear point are omitted.

There is no separate briefing dataset or briefing-generation workflow.

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


## Balanced v3 changes
- Broader A/B discovery queries and larger candidate pools.
- Strand A accepts a supported document-level R&I/geopolitics bridge; same-sentence wording is no longer mandatory.
- Strand B admits strong transferable public-sector R&I/S&T foresight methodology as derived EU relevance.
- First C scan looks back 7 days; later scans use a 48-hour overlap.
- C anchor threshold is moderately relaxed but an explicit A/B anchor remains mandatory.
- Hard exclusions for calls, facilities, project pages, ordinary news and marketing remain.

## Recovery safeguard
This recovery build seeds the three accepted Strand B publications that were present in the last healthy corpus on 2026-08-18 at 01:52 UTC. It also detects an empty/pending `radar.json` during future package upgrades and searches recent Git history for the strongest populated cumulative A/B corpus before scanning, preventing an upgrade template from silently wiping accepted literature.
