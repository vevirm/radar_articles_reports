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
