# R&I × Geopolitics Radar — V14 zero-config resilient scanner

A cumulative GitHub Pages radar for research papers, analytical reports, foresight methodology and anchored weak signals relevant to European research and innovation in a geopolitical context.

## What V14 changes

V14 removes the setup dependency introduced in V13. There are **no API keys, no repository secrets and no manual credentials**. Commit the files and the scanner runs.

The scanner keeps the balanced V12/V13 relevance criteria and the resilient failure handling, but restores full zero-config scholarly discovery:

- the full configured Strand A + Strand B query universe is attempted on every relevant scan;
- public scholarly metadata sources are queried anonymously and conservatively;
- Crossref public discovery is rate-limited and retried without requiring a contact secret;
- OpenAlex public discovery is attempted anonymously across the full query universe; if that public endpoint is temporarily unavailable, the scan continues with Crossref and direct publisher/institution scanning rather than failing;
- all configured institutional publishers/players are still scanned directly through their public sites/sitemaps/PDFs;
- source failures cannot wipe or replace the cumulative corpus;
- a degraded four-month backfill is not marked complete, so it is retried on the next scheduled run;
- GitHub Actions logs show live stage progress;
- the optional GitHub Pages refresh failure remains non-fatal.

## Admission profile

The balanced-relevance policy is retained. Strand A accepts serious research/reports on EU/European R&I and related systems — R&D and scientific capacity, universities, research infrastructures, talent, innovation ecosystems, deep tech, technology development/transfer, technological capabilities and related areas — when there is a substantive geopolitical or geoeconomic connection.

Relevant geopolitical channels include research security, strategic dependencies, supply-chain security/resilience, investment screening, technology/export controls, critical raw materials, techno-nationalism, sanctions/de-risking, strategic autonomy, science diplomacy and great-power technology competition.

Safeguards remain against generic geopolitics, generic innovation/business, pure technical papers, calls, project pages, events, press releases and other non-analytical material.

## Discovery schedule

- **First V14 run:** four-calendar-month A/B backfill under the balanced criteria.
- **Later runs:** every 12 hours with a 14-day A/B overlap.
- **Corpus:** A, B and C remain cumulative and deduplicated.
- **Zero configuration:** no keys/secrets need to be created in GitHub.

## Safe upgrade

Do **not** overwrite a populated live `radar.json`. This package intentionally does not include one.

Upload/replace the other files, keep the live `radar.json`, and commit to `main`. The push starts the V14 four-month backfill immediately. Later scans run every 12 hours.

## Local tests

```bash
python -m unittest discover -s tests -v
```
