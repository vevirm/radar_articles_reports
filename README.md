# R&I × Geopolitics Radar — V16.1 weak-signal repair

V16 keeps the working V15 A/B scanner and fixes the two remaining problems: Strand C was starved of runtime during long backfills, and the Insights page did not explain signals in a fast intelligence format.

## What V16 changes

- **Weak-signal discovery starts at the beginning of every scan**, in parallel with OpenAlex/Crossref. It is no longer the last network stage.
- **One-time 30-day Strand C recovery scan** on the V16 upgrade, then a **7-day rolling weak-signal window every 12 hours**. Deduplication means the overlap does not create duplicates.
- **30 curated news/official sources** plus 18 cross-source Google News discovery queries cover major European and international publishers and EU institutional players.
- A factual signal can connect to a specific A/B publication, a recurring A/B theme, **or a curated strategic watch theme**. This prevents a thin A/B corpus from suppressing otherwise strong R&I/geopolitical signals.
- The Strand C gate is still selective: it requires an event/change, a relevant strategic R&I theme, and either European scope or a strong external R&I + geopolitical bridge.
- Each new signal stores explicit fields for **WHAT changed**, **WHY it matters for EU R&I**, watch theme, signal kind, relationship type and evidence connection.
- The `/briefing/` page is now signal-first: weak signals are shown first with `WHAT CHANGED`, `WHY IT MATTERS FOR EU R&I`, `WATCH THEME`, source and evidence connection. Research/reports are a separate view.
- Existing A/B/C records remain cumulative and deduplicated.
- No API keys or custom GitHub secrets are required.

## Runtime

The GitHub Action timeout is 45 minutes and the scanner's internal network budget is 30 minutes. This gives long A/B backfills room to complete while the weak-signal crawl is protected by running at the start of the scan.

## Complete repository upload

This V16.1 package is a **complete repository** and includes `radar.json` as well as the active `.github/workflows/radar-scan.yml`. Upload all files and folders, including `.github`, to the repository root and commit to `main`.

For upgrades over an existing repository, the bundled `radar.json` is marked as a one-run upload seed. On the first scan, the scanner checks recent Git history and automatically restores/merges a larger prior A+B+C corpus before adding new material. The seed marker is removed from the next generated `radar.json`, so normal scans do not walk Git history repeatedly.

## Tests

```bash
python -m unittest discover -s tests -v
```

V16 includes 50 regression tests.

## Complete-repository package

The V16.1 complete package includes `radar.json`; there is no separate file to preserve manually. When upgrading an existing repository, the scanner compares the bundled/current corpus with recent Git history and automatically restores/merges a larger prior A+B+C snapshot before scanning. This prevents a full upload from erasing a newer accumulated corpus.
