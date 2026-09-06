# R&I × Geopolitics Radar

An EU-first evidence radar for research and innovation in geopolitical context.

## Operating model

- **Main Radar** is scheduled every four hours at minute 17. Every Main research run uses the standard **24-minute** scanner budget.
- **Historical Top-Tier Scan** is scheduled every four hours at minute 57, 40 minutes after Main, and uses a **15-minute** scanner budget.
- Main and Historical share one GitHub Actions concurrency group. They never research at the same time. Historical waits; if Main becomes due while Historical is still active, Main has priority and may pre-empt Historical.
- Historical searches only material published **strictly before the rolling six-month Main boundary** and uses the Main scanner's A/B admission philosophy. It does not create current weak signals.
- **Strand A** and **Strand B** are cumulative. The original 190 A + 10 B corpus is a starting baseline, not a cap.
- **Strand C** is a current signal layer. A C item must be a distinct current development anchored to substantive Strand-A evidence and expires **60 days after `first_seen`**.
- Production workflows do **not** run legacy regression-test discovery before research. Runtime preflight, output validation and write-boundary checks protect the live state instead.

## Evidence flow

Main scanner → Radar evidence → Matrix → Trends → Risks & opportunities → External shocks.

**What matters now**, **Read at least this**, **Evidence by topic** and **Sources** are reader views of that same current evidence. Matrix, risks/opportunities and shock logic do not run independent web searches; they interpret the accepted current Radar corpus and scanner-produced analytical fields.

Historical is deliberately separate. Older A/B evidence is accumulated in `historical/historical.json`; it does not feed current Strand C, the live Matrix or current shock state.

## Discovery and quality

The scanner rotates rather than repeating one giant query. It combines OpenAlex, Crossref, journal/source-first discovery, EU and trusted institutional sources, researchers/authors, citation neighbourhoods, method discovery and Matrix-gap recovery.

Query families are dimensional rather than depending on the literal phrase “R&I geopolitics”: EU/institutional context × research/innovation/capability object × strategic mechanism for A; method × method-development evidence for B; trusted source × strategic object × observable change for C. Broad retrieval generates candidates; admission remains stricter than retrieval.

`OPENALEX_API_KEY` materially expands scholarly discovery, author/citation neighbourhoods and rotating query depth.

## Writing

Visible copy follows `STYLE.md`, based on the project writing specification: evidence units use **WHAT + WHY**, with concrete EU R&I consequences and hard surface budgets on Radar and Matrix. Technical terminology is retained where useful for accuracy, but definitions and method/classifier vocabulary live primarily in the **Glossary** and **Stuff** workbooks rather than making every surface card dense.

The Stuff directory contains:

- `source_merit_ranking.xlsx` — evidence/provenance ranking snapshot.
- `eu_ri_radar_phrases_by_strand.xlsx` — admission phrase/guard reference.
- `radar_technical_grammar.xlsx` — computational foresight vocabulary, C change grammar, query-family design and writing contracts.

## Live data and fresh repositories

This bundle includes the current live `radar.json` and `historical/historical.json` supplied with the repo used to build it, so replacing the current repository preserves its accumulated corpus.

The clean `radar_seed.json` remains the fresh-repository fallback. If a genuinely new repository has no `radar.json`, Main starts from the 190 A + 10 B seed and creates its own scan state/history on the first 24-minute run. The Historical scanner has the corresponding `historical/historical_seed.json` fallback.

## Security boundary

The public pages are static HTML/JS and only fetch JSON; they have no GitHub write credential. Scanner checkout uses `persist-credentials: false`. The OpenAlex key is supplied only as an Actions secret environment variable. After scanning, unexpected repository changes are restored/removed, output is validated, and authentication is added only for the final commit of the permitted generated JSON file.


### Browser-upload compatibility

GitHub browser uploads can leave hidden `.github/workflows` files from an older repository version in place. The visible runtime therefore remains compatible with the retained workflows: old regression discovery is reduced to the current live contract plus quarantined legacy suites; upload-triggered Historical runs perform no source requests; and an old Main workflow's one post-Main dispatch is repurposed as the sequential 15-minute Historical cycle. This preserves Main-first ordering and prevents simultaneous research even when the hidden YAML was not replaced.
