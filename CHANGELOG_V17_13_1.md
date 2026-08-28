# Changelog — V17.13.1

## Purpose

V17.13.1 tightens V17.13.0 around the actual subject of the product: **EU/European research and innovation in geopolitical context**. It also preserves the reader-first interface without hiding the richer evidence record.

## Admission boundary

- Made EU/European R&I in geopolitical or strategic context the explicit subject of Strand A, not a generic relevance filter.
- Preserved the normal three-part gate: European subject + substantive R&I + strategic/geopolitical mechanism.
- Added a narrow **external strategic shock** route for major developments outside Europe (for example a step-change in US or Chinese AI, quantum, semiconductor or comparable capability) when:
  - the event is genuinely capability-changing rather than ordinary foreign tech news;
  - a current same-domain EU/European Strand-A anchor exists; and
  - the consequence for Europe can be stated in one specific plain-language sentence.
- The Europe-impact sentence is stored and displayed as a **radar inference**, not falsely attributed to the source.
- Generic foreign product launches, domestic innovation stories or vague competitiveness implications remain out.

## Language boundary

- Replaced the whole-publication English assumption with an **English-evidence** rule.
- English publications qualify normally.
- A non-English publication may qualify when the source or trusted index exposes a sufficiently informative English abstract, executive summary or equivalent source text that establishes the finding.
- An English title or tiny metadata stub is insufficient.
- Machine translation of inaccessible foreign-language material is not treated as verified evidence.

## Discovery and weak signals

- Added bounded US/China frontier-capability queries so the external-shock exception can actually be discovered.
- Kept the hard four-calendar-month window for every query family.
- Kept Strand C as a minority with a 15% ceiling.
- Within that ceiling, qualifying external strategic shocks rank ahead of ordinary weak signals so the cap cannot hide a genuinely position-changing event.

## Easy radar / full evidence

- Kept the main radar reader-first: plain claim and short relevance explanation remain the default surface.
- Added **All record details** to each visible card.
- Added **Show all details** to reveal detailed fields across the current result set in one action.
- The disclosure can expose the original title, authors, source, date, type, source tier, EU relevance, discovery route, tracked-since date, full available summary, admission note, R&I evidence, strategic evidence, Matrix fields and evidence, and the explicit external-Europe bridge when used.
- External-shock bridge text is visibly labelled as radar inference.

## Radar → Matrix

- Added the stored external-Europe bridge to Matrix evidence inputs.
- `material_external` items can satisfy the Europe-scope test only when that bridge exists.
- Every admitted Strand-A record still reaches the Matrix classifier; the classifier may leave it unplaced if row/direction evidence is not defensible.

## State handling

- Updated release/config/profile metadata to V17.13.1.
- Did **not** run a fresh external discovery scan while packaging this release.
- Existing corpus claims are retained; old records are not presented as if they had been newly admitted under the external-shock exception.
