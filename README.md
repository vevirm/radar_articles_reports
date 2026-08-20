# R&I × Geopolitics Radar — V11

EU-first, cumulative R&I/geopolitics and foresight-methodology radar for GitHub Pages.

## V11: deeper A/B report and paper coverage

V11 changes the discovery layer rather than weakening the admission criteria.

- **First V11 scan: four calendar months of Strand A/B backfill.** On a new installation, and once when upgrading from an older radar build, the scanner searches from `today - 4 months` through the current date. On 20 August 2026 that means a discovery window beginning 20 April 2026.
- **Then every 12 hours.** The GitHub Action keeps a 14-day A/B discovery overlap to catch late indexing and corrected metadata, while the accepted corpus remains cumulative.
- **OpenAlex + Crossref are now broad scholarly discovery layers.** Relevant journal articles are no longer rejected just because the journal was missing from a small hard-coded list. Exact core journals still rank higher, but the A/B substantive gates remain the admission control.
- **Much larger direct-report source universe.** The institutional crawler now covers more EU bodies, European research/innovation organisations, think tanks, foresight organisations, and major non-EU policy/research players.
- **Institutional recall is improved.** Recent pages from a whitelisted institution are eligible even when the CMS URL has an opaque slug. Report/publication-looking URLs are prioritised, but a URL keyword is no longer mandatory.
- **More pages are inspected during the four-month bootstrap** and the workflow timeout is extended to 60 minutes for that one heavier pass.
- **Everything still accumulates.** Accepted A, B and anchored C items are deduplicated and retained. A quiet scan cannot erase earlier material.

## Source coverage model

### Scholarly publishers and journals

OpenAlex and Crossref search across the scholarly literature rather than crawling a finite publisher list. This covers material from major publisher families such as Springer Nature, Elsevier, Wiley, Taylor & Francis, SAGE, Oxford University Press, Cambridge University Press, IEEE, ACM, Emerald, MDPI, Frontiers, PLOS and comparable journals. Core R&I/foresight journals retain priority ranking.

### Direct institutional/report publishers

The configured direct-source set includes EU institutions and agencies; OECD and European research-policy organisations; Bruegel, CEPS, MERICS, SWP, IFRI, EUISS, Clingendael, Chatham House, ECFR, CER, EPC, ECIPE, DGAP, CIDOB, Jacques Delors Institute, Bertelsmann Stiftung, Fraunhofer ISI, Rathenau, CWTS, Nesta, Demos Helsinki and the Copenhagen Institute for Futures Studies; plus major non-EU players such as RAND, CSIS, Brookings, Carnegie, CSET, ASPI, NBER, CFR, Atlantic Council, ITIF, Belfer, CNAS, National Academies Press, UNESCO and the World Bank.

The exact current list is in `radar_config.json`, so it can be extended without changing the UI.

## What qualifies

### Strand A — R&I under geopolitical/economic-security change

A publication must have substantive R&I/science/technology policy content, substantive geopolitical/economic-security content, a supported connection between them, and direct or explicit derived EU relevance. Eligible material includes peer-reviewed papers, working papers, institutional reports, policy studies and substantive briefs.

### Strand B — foresight methodology

B is methodology-first: strategic foresight, horizon scanning, scenarios, weak-signal detection, anticipatory governance, Delphi, backcasting, morphological analysis, participatory methods, strategic intelligence, robustness/evaluation and related methods. Direct EU practice is prioritised; strong transferable public-sector R&I/S&T methodology can enter as derived EU relevance.

### Strand C — anchored weak signals

C uses trusted current-news sources and requires an explicit connection to accepted A/B literature or a recurring A/B theme. Discovery uses a current window, but once a signal is admitted it stays in the cumulative corpus.

## Scan schedule

The active workflow is `.github/workflows/radar-scan.yml`.

- commit/upload to `main` → scan immediately;
- first V11 run → four-month A/B source-expansion backfill;
- after that → every 12 hours;
- later A/B scans use a 14-day overlap;
- first-ever C run uses 7 days, later C scans use 48 hours;
- accepted material is never removed merely because it falls outside a later discovery window.

## Important upload rule

Do **not** overwrite a populated live `radar.json` with an empty template. This package intentionally does not include `radar.json`. Upload these files over the repository, retain the existing live radar data, and commit to `main`. V11 will then run its one-time four-month source-expansion backfill and merge the results into the existing cumulative corpus.

## GitHub Pages

Expected site: `https://vevirm.github.io/radar_articles_reports/`

Pages settings should remain **Deploy from a branch → main → /(root)**.

The main radar and `/briefing/` both read the same cumulative `radar.json`.
