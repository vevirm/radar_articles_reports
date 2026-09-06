# R&I × Geopolitics Radar

An EU-first evidence radar for research and innovation in geopolitical context.

## Operating model

- **Main Radar** runs every four hours at **00:17 / 04:17 / 08:17 / 12:17 / 16:17 / 20:17 UTC**. Every Main run has the standard **24-minute** research budget.
- **Historical Top-Tier Scan** runs every four hours at **00:57 / 04:57 / 08:57 / 12:57 / 16:57 / 20:57 UTC**, after Main, with a **15-minute** research budget.
- Main and Historical share one GitHub Actions research slot, so they never research concurrently. Historical waits and never cancels Main. If Main becomes due while Historical is still active, Main has priority and may pre-empt Historical.
- Historical accepts only material published **strictly before the rolling six-month Main boundary** and uses the Main scanner's substantive A/B admission philosophy. It does not create current Strand-C signals.
- **Strands A and B are cumulative.** The original 190 A + 10 B corpus was a starting baseline, not a cap.
- **Strand C is temporary and relative to A.** Every C signal must represent a distinct current development anchored to substantive Strand-A evidence. C discovery covers the current **60-day** window and each signal expires **60 days after `first_seen`**.
- Production workflows do **not** run the old repository-wide regression-test discovery before research. Runtime preflight, output validation and write-boundary checks protect the live state instead.

## Evidence flow

Main scanner → Radar evidence → Matrix → Trends → Risks & opportunities → External shocks.

**What matters now**, **Read at least this**, **Evidence by topic**, **Briefing** and **Sources** are reader views of the same current Main evidence. The Matrix, risks/opportunities and shock pages do not launch their own research scans; they interpret accepted Radar evidence and scanner-produced analytical fields.

Historical is deliberately separate. Older A/B evidence accumulates in `historical/historical.json`; it does not become current C and does not overwrite the live Matrix or shock state.

## Discovery and quality

The scanner rotates rather than repeating one giant query. It combines OpenAlex, Crossref, journal/source-first discovery, EU and trusted institutional sources, researchers/authors, citation neighbourhoods, method discovery, observable-change discovery for C, and Matrix-gap recovery.

A queries combine EU/institutional context × research/innovation/capability object × strategic mechanism. B combines method × evidence of method development. C combines a trusted context × strategic object × observable change, then requires an A anchor before publication.

Retrieval is deliberately broader than admission. Generic terms such as *Europe*, *innovation*, *technology*, *security* or *strategic* do not qualify material by themselves. Source quality, phrase combinations, document context and substantive mechanism matter at admission.

Repeated zero-yield Matrix depth waves are bounded: when the same gap set produces no A/B candidates twice, the scanner stops hammering that lane for the run and returns time to other rotating discovery families.

`OPENALEX_API_KEY` materially expands scholarly discovery, author/citation neighbourhoods and query depth.

## Writing

Visible text follows `STYLE.md`.

- Every evidence unit is written as **WHAT + WHY**.
- Radar surface budget: WHAT ≤ 20 words; WHY ≤ 20 words.
- Matrix surface budget: WHAT ≤ 12 words; WHY ≤ 15 words.
- WHY must name a consequence specific to EU research and innovation in geopolitical context; generic relevance prose is a writing failure.
- Matrix items use parallel `WHAT — WHY` grammar and honest gaps rather than filler.
- Surface prose uses concrete language and expands opaque abbreviations where practical.
- More technical vocabulary, method language and classifier/search grammar remain available in the **Glossary** and **Stuff** workbook rather than being deleted from the system.

The Stuff directory contains:

- `source_merit_ranking.xlsx` — evidence/provenance ranking snapshot.
- `eu_ri_radar_phrases_by_strand.xlsx` — admission phrase/guard reference.
- `radar_technical_grammar.xlsx` — computational foresight vocabulary, C change grammar, query-family design, surface-term expansions and writing contracts.

## Live data and fresh repositories

This bundle preserves the current live `radar.json` and `historical/historical.json` from the repository supplied for this build.

`radar_seed.json` remains the clean 190 A + 10 B fallback for a genuinely new repository. A new Main scanner creates its own state/history on its first normal 24-minute run. Historical has the corresponding `historical/historical_seed.json` fallback.

## Security boundary

The public pages are static HTML/JavaScript and only read JSON; they have no GitHub write credential. Scanner checkout uses `persist-credentials: false`. `OPENALEX_API_KEY` is supplied only through GitHub Actions secrets. After research, workflows validate output and isolate unexpected repository changes. Authentication is added only for the final commit of the permitted generated JSON file.

## Browser-upload compatibility

The scanner retains compatibility guards for repositories where GitHub browser upload leaves an older hidden workflow file behind. The supported workflows in this bundle are nevertheless the authoritative production configuration: Main first every four hours, Historical 40 minutes later, one shared research slot, 24/15-minute budgets, and no production regression-test gate.
