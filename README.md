# R&I × Geopolitics Radar

This repository is a public GitHub Pages radar that scans automatically and writes its results directly to `radar.json`, which the page displays.

## What happens after upload

1. Upload **all files and folders in this package** to the root of `vevirm/radar_articles_reports` and commit them to `main`.
2. The new `R&I Radar Scan` GitHub Action is triggered by that upload. Normally the first scan starts immediately and the public page is populated after the scan and Pages rebuild finish (often within several minutes; source response times can make it longer).
3. After that, the workflow runs every 12 hours at minute 17 UTC.
4. Every scan rewrites `radar.json`, commits it, and explicitly requests a GitHub Pages rebuild, so the newest results become visible on the public site.

The public URL is expected to be:

`https://vevirm.github.io/radar_articles_reports/`

GitHub Pages should remain configured as **Deploy from a branch → main → /(root)**, which is how this repository was already configured.

## If the first scan does not start

Open **Actions → R&I Radar Scan → Run workflow**. This manual button is also useful whenever you want an extra scan between the 12-hour scheduled runs.

## Scanner design

The scanner is intentionally conservative and does not pad results.

- **Strand A/B scholarly discovery:** Crossref plus a small optional OpenAlex layer.
- **Strand A/B institutional discovery:** whitelisted institutional sitemaps, verified publication metadata, and PDF/page text where accessible.
- **Strand C discovery:** current-window Google News RSS searches restricted to the specified trusted media domains.
- **Strand C anchoring:** an item is discarded unless it shares a substantive theme with a caught A/B publication or a recurring A/B theme.
- **Date rule:** institutional items require a publication date found in page metadata; sitemap modification dates are used only for discovery, not as publication dates.
- **Shortfall rule:** fewer than 3 A or B items, or 0 C items, is shown explicitly rather than padded.

The exact editorial criteria are in `radar_criteria.md`.

## No API key is required

The package works without secrets. Crossref, institutional websites, and the news feed layer are enough to run the scanner. The script also supports an optional `OPENALEX_API_KEY` environment variable for additional scholarly discovery, but it is not required.

## Important limitation

A fully automated open-web scanner cannot guarantee human-level interpretation of every borderline article. The code uses strict whitelists, verified dates, topic co-occurrence, EU relevance checks, methodology checks, hard exclusions, word-count checks where full text is accessible, and explicit A/B anchoring for news. It is tuned to prefer missing a borderline item over admitting a clearly irrelevant one.
