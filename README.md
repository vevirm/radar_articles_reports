# R&I Geopolitics Radar V17.8.1

V17.8.1 corrects the over-pruning introduced in V17.8.0. The radar remains precision-oriented, English-only for new evidence, and risk-weighted in the Sovereignty Frontier, but **major EU R&I relevance is now primarily a ranking objective rather than a blanket deletion rule**.

## What changed

- **Broad corpus restored:** unrecognised/broad peer-reviewed journals are allowed again. Source tier affects confidence and ranking; it is not an automatic exclusion.
- **Surgical historical cleanup:** quality-profile upgrades no longer re-run every saved paper against its shortened stored summary. Historical A/B rows are removed only for high-confidence failures such as non-English titles, document exclusions, malformed records, or obvious off-topic contamination such as sports.
- **Major EU R&I ranked first:** system-level R&I, research security, strategic technologies, economic security, dependencies, talent, infrastructure and geopolitical competition receive a strong priority score so they surface before peripheral material.
- **Live Strand B stays strict:** newly discovered futures-method papers still need a policy/R&I/technology-system destination. The relaxed migration applies only to historical preservation.
- **Weak signals stay selective:** direct European developments are preferred. Narrow external shocks such as export controls, compute/chip restrictions, quantum or research-system changes may enter the prefilter, but they still require a concrete Strand-A anchor before display.
- **Specific card wording:** the main UI no longer falls back to the repeated generic geopolitical sentence; it uses a paper-specific finding or readable title.
- **Risk-first Sovereignty Frontier:** +/+ cells require realised gains on both autonomy and competitiveness. Plans, funding calls, roadmaps and ambiguous evidence do not count as openings, and discovery prioritises B/C/D risk cells while they are sparse.

The bundled `radar.json` is rebuilt from the user-supplied 24 August 2026 state. It retains **108 A / 23 B / 9 C** records and all **19** matrix-only Frontier evidence records. The one removed A paper is the table-tennis industry false positive; four B records are obvious domain/method false positives. The C reduction is intentionally stronger because C is an actionable weak-signal layer rather than a literature archive.

Run the scanner as before with `python scripts/scan_radar.py`. Persistent discovery cursors are preserved.
