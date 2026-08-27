# Manual ingest & matrix review — EU_RI_Found_Items_List

Batch: `697d3b227e28-d9d09026`  
Ingested: `2026-08-27T06:39:00Z`  
Manual source: `EU_RI_Found_Items_List.docx`  
Authoritative pre-ingest state: `radar (26).json` (`last_updated` preserved as `2026-08-26T19:37Z`)

## Outcome

| Measure | Count |
|---|---:|
| Curator bibliography entries reviewed | 63 |
| Existing corpus matches (no duplicate) | 7 |
| New substantive radar items | 23 |
| New matrix placements | 12 |
| Core-gate rejects | 24 |
| Context/reference/outside-window only | 8 |
| Record-level deferred | 1 |
| Additional deferred component inside a compound entry | 1 |

No live scan was run and no scanner cursor or `last_updated` timestamp was advanced. The standalone JSON supplied with the task was newer than the ZIP copy, so it was used as the authoritative state before this manual batch.

## New matrix placements

| ID | Publication | Curator primary | Reviewed placement | Agreement |
|---|---|---|---|---|
| F05 | Beijing’s critical raw material weapon – and how to dismantle it | I-D | **I-D — Cut supply** | agrees |
| F07 | Made in China, Powered by Europe: Mapping the EU’s Strategic Leverage Over the People’s Republic of China | I-A | **I-A — Home chokepoint** | agrees |
| F13 | EU Defence Series: European Autonomy in Orbit | I-A | **I-C — Rented frontier** | differs |
| F16 | Technological Dependencies of the European Union | I-C | **I-D — Cut supply** | differs |
| F18 | The flaws in the European Union’s proposed Industrial Accelerator Act and how to fix them | C-B | **C-B — Protected niche** | agrees |
| F19 | Paradigm Shift in Principle, Paper Tiger in Practice? How to Make the Industrial Accelerator Act Count | C-B | **R-D — Gridlock** | differs |
| F22 | Europe’s Geo-Industrial Deal: A path to securing Europe’s competitiveness abroad | C-A | **C-A — Home champion** | agrees |
| F23 | Strategic procurement in Global Europe: Why EU preferences risk undermining its own ambitions | C-B | **C-B — Protected niche** | agrees |
| F29 | Driving Defence: The automotive sector’s role as a potential enabler of Europe’s defence surge | C-A | **C-A — Home champion** | agrees |
| F32 | Mitigate, deter, escalate: Europe’s options against US economic coercion | R-C | **R-C — Rule-taker** | agrees |
| F35 | Selective Conditionality: The EU’s Emerging Approach to Foreign Investment | R-B | **C-C — Foreign exit** | differs |
| F36 | From openness to deterrence: Europe’s doctrine of reactive assertiveness | R-B | **R-B — Fortress rules** | agrees |

Matrix placement was intentionally withheld for admitted sources whose reviewed evidence was mixed, scenario-based, descriptive, or insufficiently directional on both independence and competitiveness.

## Existing corpus matches — no duplicate

- **F01** — Can science diplomacy help safeguard science as a global public good? Reflections on strategy, data and people → existing `strand_a` item: Can science diplomacy help safeguard science as a global public good? Reflections on strategy, data and people
- **F04** — A self-reliance framework for identifying strategic advanced materials → existing `strand_a` item: A self-reliance framework for identifying strategic advanced materials
- **F06** — Materealistic? How European energy system models exceed raw material reserves. arXiv:2606.12201 → existing `strand_a` item: Materealistic? How European energy system models exceed raw material reserves
- **F10** — Mapping of technology specialisation, complexity and relatedness of the EU and selected global partners → existing `strand_a` item: Mapping of technology specialisation, complexity and relatedness of the EU and selected global partners – CEPS
- **F11** — Beware of Geeks Bearing Gifts: Building True EU Frontier AI Sovereignty. arXiv:2606.07536 → existing `strand_a` item: Beware of GeeksBearing Gifts: Building True EU Frontier AI Sovereignty
- **F40** — Shared gains, secure links: rethinking EU–Asia digital cooperation → existing `strand_a` item: Shared gains, secure links: rethinking EU-Asia digital cooperation – CEPS
- **F61** — Artificial-intelligence competition in Europe: the role of DMA Article 6(7) → existing `frontier_evidence` item: Artificial-intelligence competition in Europe: the role of DMA Article 6(7)

## Deferred

- **F15** — *The strategic autonomy imperative: defending Europe’s digital infrastructures in the age of hard geopolitics*: thematically plausible, but the underlying primary publication could not be verified to the repository’s source-evidence standard in this review.
- **F29 component** — *Marshalling the EU’s emerging industrial policy for defence*: the companion EPC *Driving Defence* paper was verified and admitted; this separate Brussels Institute component remains deferred rather than being inferred from the combined citation.

## Compound citations

- **F29** was split for evidence purposes: *Driving Defence* is admitted; *Marshalling the EU’s emerging industrial policy for defence* remains deferred.
- **F36** was split: the *Brussels Economic Security Review, Vol. I* wrapper is context, *Conditional openness, contingent security and wicked trade-offs* does not clear the substantive R&I bridge, and *From openness to deterrence* is admitted and placed at **R-B**.

## Rejection policy

Rejections follow the radar’s core rule: direct EU/European scope, a substantive R&I mechanism, and a geopolitical/economic-security bridge must all be present. Foreign comparator papers, broad trade/financial/geoeconomic pieces without a substantive R&I mechanism, and explicit reference/context items were not forced into the radar or matrix.

## State integrity

- The standalone `radar (26).json` was used as the starting state so the three records that were newer than the ZIP copy were preserved.
- Public additions were hard-deduplicated across `strand_a`, `strand_b`, `strand_c`, and `frontier_evidence` by canonical URL and normalized title.
- Two pre-existing duplicate-source records in the newer standalone baseline were also consolidated: one identical ALLEA PDF record and one superseded Open Research Europe article version; alternate/version metadata was preserved on the retained records.
- All 23 new substantive items are stored in `strand_a`; the 12 matrix-eligible items carry reviewed `matrix_dimension` and `quadrant_implied` fields.
- The original curator cell list is retained on each admitted item and in the decision ledger, including agreement/difference with the reviewed placement.
