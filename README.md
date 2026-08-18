# R&I × Geopolitics + Foresight Methodology Radar

EU-first, automatically updated GitHub Pages radar.

## What this repository does

- Runs a first scan immediately when the repository files/workflow are committed to `main`.
- Runs again every 12 hours via GitHub Actions.
- Requires no OpenAI key and no paid API.
- Discovers candidates through OpenAlex, Crossref, whitelisted institutional websites/sitemaps, and a whitelist-only current-news layer.
- Applies strict admission gates before anything is shown publicly.
- Writes accepted results to `radar.json`.
- Writes an automatic evidence briefing to `findings.json` in the same scan.
- Serves `findings.html`, a one-sentence findings view of the accepted A/B literature plus anchored Strand C signals.
- Requests a GitHub Pages rebuild after each scan so fresh results become visible on the site.
- Keeps accepted A/B publications as a cumulative corpus; Strand C is a current-window signal layer.
- Requires no OpenAI key for the findings page: the one-sentence findings are selected extractively from the strongest source text already captured by the admission process.

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

## Automatic evidence briefing

The detailed radar remains at `index.html`. The additional briefing is at `findings.html`.

Every normal scan now performs both jobs together:

1. discover and admit material into the existing radar;
2. create/update a dedicated one-sentence `finding` for each accepted A/B publication;
3. backfill older corpus entries from their stored summaries when they predate the findings feature;
4. compute recurring corpus themes and select a representative source-level finding for each;
5. convert the current accepted Strand C layer into concise signal findings with its literature anchor;
6. write `radar.json` and `findings.json`, commit both, and request the same GitHub Pages rebuild.

The briefing is intentionally auditable rather than generative: it does not claim cross-paper consensus. Recurring-theme cards report how often a theme appears and show a representative accepted finding.

When this v4 package is installed over an already-running repository, the first scan also checks the parent Git commit. If the packaged `radar.json` is the pending template, the scanner recovers the previous committed radar corpus automatically before scanning, then backfills the new `finding` field and builds `findings.json`. A genuinely new repository simply performs the normal first-run backfill.

## Password gate

The page uses the simple casual-visitor password gate requested for this radar. Password: `TutuRadar2026?`

This is not server-side security; the repository and `radar.json` remain public because the site is hosted as a public GitHub Pages project.

## Expected GitHub Pages address

`https://vevirm.github.io/radar_articles_reports/`

Evidence briefing:

`https://vevirm.github.io/radar_articles_reports/findings.html`

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

## Balanced v4 changes
- Preserves all Balanced v3 discovery, admission, corpus and weak-signal behavior.
- Adds `findings.html` and `findings.json`.
- Adds an extractive one-sentence `finding` to new accepted A/B items.
- Automatically backfills findings for older saved A/B corpus entries.
- Adds recurring-theme briefing cards based on corpus counts plus representative findings.
- The scheduled/manual scanner commits `radar.json` and `findings.json` together.
- The original radar and the evidence briefing share the same casual-visitor password session.
