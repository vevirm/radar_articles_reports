# v17.18.4 — institutional hub/container integrity fix

This release fixes a discovery-container false positive without changing the substantive A/B/C relevance thresholds.

## Why
A Commission hub page titled **“All research and innovation news”** was admitted as Strand A. The page itself is only a listing; the scanner then borrowed the first child story's snippet/date and treated the container as evidence.

## Changes
- Institutional listing/index/archive/search pages are now discovery surfaces only; they can never become A/B/C evidence records.
- The rule uses exact generic titles and exact hub paths, so individual stories underneath a news hub remain eligible.
- Container pages are rejected before date extraction, weak-signal consideration, or the EU-official-news exception can run.
- Saved-corpus sanitation and Git-history restoration apply the same rule, so a previously admitted container page is removed automatically on the next scan after upload.
- Source adapters still crawl those hubs and follow individual publication/story links; recall is not reduced by discarding the hub itself.
- No change to source rotation, four-hour cadence, evidence-quality ranking, Matrix/Read-at-least-this/Risks & opportunities update logic, or the A/B/C substantive gates.

# v17.18.3 — recall allocation repair

This release increases discovery depth without weakening any admission gate.

## Why
The live diagnostics showed OpenAlex HTTP 429 stopping the public endpoint while later recall lanes still treated OpenAlex as available. That wasted part of the scan on an endpoint that had already asked the scanner to stop, while the run still ended below the search-depth target.

## Changes
- HTTP 429 / explicit endpoint-stop warnings now mark a source family unavailable for the remainder of that run.
- A bounded source-failure reallocation stage immediately transfers that time to unused EU/institutional publication sources and the surviving scholarly source family.
- If OpenAlex stops, the replacement scholarly slice prioritises rotating trusted journals in Crossref plus a fresh mixed A/B query slice.
- If Crossref stops, the replacement slice uses OpenAlex plus unused institutional sources.
- Institutional rotation per normal scan increases from 24 to 30 sources, with 12 protected official-EU slots and 10 source-adapter slots.
- Trusted journal source-first rotation increases from 10 to 12 journals per scan.
- Dedicated futures-method queries increase from 12 to 16 per scan; foresight-author follow-up increases from 4 to 6.
- Main runtime budget increases modestly from 20 to 22 minutes; GitHub's 30-minute hard timeout remains unchanged.
- The substantive A/B/C gates, source-quality rules, deduplication, source-link integrity checks, and Matrix qualification rules are unchanged.

The bundled radar.json is marked as a repository bundle seed. On the first scan after a whole-repository upload, the scanner merges the larger pre-upload live corpus and its persisted rotation cursors from Git history after integrity filtering, so newer live evidence is not intentionally erased by the ZIP.
