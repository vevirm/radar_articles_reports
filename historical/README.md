# Historical radar: source-age archive and coverage rotation

This historical layer is **not** a radar about the past. It is a separate, cumulative evidence layer for high-quality EU R&I material whose **publication date** is older than the Main Radar's rolling six-month window.

- Historical status is decided by the publication date of the paper/report, not by whether its content looks backward or forward.
- The scanner computes the upper boundary as **today minus six months** and includes sources strictly before that boundary, back to **1 January 2015**.
- New automated additions must still pass the elite-source, EU/European R&I, strategic/geopolitical-context, topic and merit gates. Generic EU research-system material is not admitted merely because it discusses careers, capacity or open science.
- Accepted historical evidence is cumulative: normal scans add or enrich evidence but do not silently delete previously accepted rows.

## How daily discovery now avoids low-hanging fruit

Historical discovery has persistent cursors for several independent dimensions. A daily run deliberately moves through:

1. **Topic families** — different EU R&I/geopolitics themes.
2. **Elite source batches** — different institutions and trusted source families.
3. **Two-year publication bands** — for example 2015–2016, 2017–2018, and so on up to the rolling six-month cutoff.
4. **API result depth** — later result pages are visited rather than always restarting from page 1.
5. **Direct-source depth** — institutional adapters/sitemaps rotate deeper into ranked publication links instead of repeatedly fetching only the top links.
6. **Curated workbook seeds** — known-good titles rotate as year-scoped backfill searches.
7. **Known-good authors** — first authors from admitted evidence rotate through a Crossref backtracking lane to find earlier relevant work.

Every run also probes a small number of the **thinnest topic × publication-band cells** in the retained archive. The gap selector itself rotates within the under-covered pool, so one permanently empty cell cannot consume every future run.

If the strict-gate yield remains below the configured target (currently 8), the scanner can perform fresh continuation waves **inside the same daily GitHub job**. Each continuation advances topic, source, time-band and depth cursors. The target controls search depth only; it never lowers admission quality. There is no separate dispatched Historical rescue job.

## Curated layers

- `manual_evidence.json` contains deliberately reviewed EU R&I geopolitical signals. These are persistent and are not overwritten by automated reclassification.
- `curated_seed_evidence.json` is a discovery/backfill queue. Seed entries still need to pass the automated source-quality and relevance gates.
- `Research_Workforce_Consolidated_25_2_historical_geopolitical_manual.xlsx` is the workbook provenance for the manual review layer.
