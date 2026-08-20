# R&I × Geopolitics Radar — V12

A cumulative GitHub Pages radar for research papers, analytical reports, foresight methodology and anchored weak signals relevant to European research and innovation in a geopolitical context.

## V12: balanced relevance

V11 improved source coverage but the admission gates were still too narrow. V12 deliberately loosens them **moderately**, not indiscriminately.

The scanner now accepts analytical work about the wider EU R&I system when the geopolitical connection is substantive even if the publication does not repeatedly use formal phrases such as `research policy` or `innovation governance`. This includes R&D/scientific capacity, universities and higher education where they affect research, research infrastructures, talent, technology development and transfer, deep tech, innovation ecosystems, technological capabilities, and critical/emerging technologies.

The geopolitical/economic-security side is also broader: supply-chain security/resilience, investment screening, critical raw materials, techno-nationalism, strategic dependencies, technology controls and great-power competition can establish the geopolitical context when they materially interact with R&I.

Important safeguards remain: an A item still needs (1) real R&I/related-system substance, (2) real geopolitical/economic-security substance, and (3) EU/European/member-state relevance. Generic geopolitics, generic innovation/business, pure technical papers and ordinary web/news/event/call/project pages remain excluded.

## EU relevance changes

V12 treats `Europe`, `European`, and EU member states in a title/abstract as direct European scope. V11 was too literal about explicit `EU` wording and could miss papers framed as, for example, European innovation, German research security or French technology strategy.

Non-European work still needs explicit lessons/implications for Europe to enter Strand A. High-quality foresight methodology can be marked derived when clearly transferable to EU public-sector R&I/S&T practice.

## Strand B changes

B remains methodology-first. It now better handles substantial institutional reports where the methodology section comes after a long executive summary. Trend reports and scenario outputs without methodological reflection are still rejected.

## Discovery schedule

- **First V12 run:** one-time four-calendar-month A/B re-backfill under the new criteria. On 20 August 2026 the window starts on 20 April 2026.
- **Later runs:** every 12 hours with a 14-day overlap for A/B discovery.
- **Corpus:** A, B and C remain cumulative and deduplicated. Accepted historical items are not removed by later scan windows.

The V12 marker is intentionally different from V11, so upgrading triggers the four-month rescan and gives previously rejected papers/reports another chance to qualify.

## Sources

OpenAlex and Crossref are searched broadly across peer-reviewed literature, while institutional discovery covers the curated EU/European and major international publishers/players in `radar_config.json`. Discovery queries have also been expanded toward European R&D, technological capabilities, deep tech, innovation competitiveness, research infrastructures, universities, supply-chain security and strategic technology ecosystems.

## Institutional quality floor

- normal trusted analytical institutional material: roughly 900+ words;
- concise Tier-1 analytical briefs: roughly 500+ words when the title/type and substantive gates are strong;
- Tier-3 institutional material: 1,200+ words.

Hard document-type exclusions remain in place.

## Safe upgrade

Do **not** overwrite a populated live `radar.json` with an empty template. This package intentionally does not include `radar.json`.

Upload the package files over the repository, retain the existing live `radar.json`, and commit to `main`. The GitHub Action will run the V12 four-month re-backfill, merge newly qualifying items into the cumulative corpus, and then continue on its 12-hour schedule.

## Local tests

Run:

```bash
python -m unittest discover -s tests -v
```
