RADAR INSIGHTS — SAFE TOPIC-DIGEST ADD-ON
==========================================

Purpose
-------
Radar insights is a subject view of the material already admitted to radar.json.
It is not a second scanner and it does not create a separate narrative analysis.

The page groups the existing radar items under practical headings such as:
- Raw materials & supply chains
- Research & science
- AI & compute
- Chips, quantum & critical tech
- Energy & climate tech
- Security, defence & dual use
- Trade, industry & economic security
- Digital infrastructure & cyber
- Space
- Health & biotech
- Talent, skills & mobility
- International partnerships & geopolitics
- Foresight & methods

Each radar item is assigned to ONE primary heading to avoid repetition. If it also
strongly touches another subject, that appears only as a small secondary tag.

The bullet wording, source, date, link, Strand and any Strand C anchor come from
the existing radar record. The topic builder does not fetch new evidence and does
not modify radar.json.

Timing
------
The workflow runs on installation/update and again after every successful radar
scan, so the topic digest follows the live corpus automatically.

Safety
------
The workflow checks that radar.json is populated, records its checksum, builds
only briefing/index.html and briefing/briefing.json, verifies the checksum again,
and stages only files under briefing/.
