# R&I × Geopolitics Radar

EU-first radar for **R&I under geopolitical change**, **foresight methodology**, and an **anchored weak-signal news layer**.

## Automatic operation

The workflow at `.github/workflows/radar-scan.yml` runs:

- immediately when this package is committed to `main`;
- every 12 hours thereafter;
- manually whenever **Actions → R&I Radar Scan → Run workflow** is pressed.

The scanner rewrites `radar.json`, commits the fresh results, and explicitly requests a GitHub Pages rebuild so the updated radar becomes visible on the site.

Public URL: `https://vevirm.github.io/radar_articles_reports/`

Keep Pages configured as **Deploy from a branch → main → /(root)**.

## Password gate

The landing page is protected by a lightweight client-side password gate. The clear-text password is not written into `index.html`; the browser checks its SHA-256 digest. This is intended only to deter casual visitors, not to make a public GitHub Pages repository cryptographically private.

## Scanner

The scanner uses no mandatory API key. It combines:

- Crossref for whitelisted journals;
- optional OpenAlex discovery (works without a key at reduced volume; `OPENALEX_API_KEY` can be added later);
- institutional sitemaps and page/PDF metadata for whitelisted policy/research institutions;
- current-window Google News RSS queries restricted to the Strand C media whitelist.

The selection code is conservative, applies the April 1, 2026 publication-date floor to A/B, enforces the EU angle, does not pad shortfalls, and requires Strand C items to anchor to caught A/B publications or recurring A/B themes.

Editorial criteria are preserved in `radar_criteria.md`.
