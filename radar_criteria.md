# Radar admission criteria — V17.9.0 source-aware aboutness profile

## Governing rule

**Reject incidental mentions, not short documents.** A pass-1 candidate must substantively connect Europe/EU, an R&I dimension, and geopolitical context. Repetition and section spread are evidence of aboutness only when enough document structure is actually available.

## Pass 1: core reports and papers

A retained item must satisfy all three substantive blocks:

1. **European scope:** direct EU/European R&I relevance, not merely EU funding boilerplate or a foreign case that mentions Europe as a comparator.
2. **R&I dimension:** knowledge & people; infrastructure & inputs; conversion; or rules & institutions.
3. **Geopolitical context:** autonomy/dependence, economic or research security, strategic competition, external chokepoints, export controls, supply dependencies, or another mechanism connecting R&I to geopolitical position.

### Text modes

- **Full text:** use recurrence, distinct-section spread and co-occurrence to reject incidental mentions.
- **Abstract only:** do not require nonexistent sections. Require a coherent EU + R&I + geopolitical connection in the title/abstract/keywords, with semantic/contextual evidence taking precedence over raw count alone.
- **Metadata only:** return `insufficient_text` and defer. Attempt richer retrieval later; do not equate missing text with irrelevance.

### EU acronym rule

A bare `EU` token is not sufficient when context is ambiguous. If the source defines `EU` as another term, it cannot establish European Union relevance. Prefer unambiguous anchors such as European Union, European Commission, Horizon Europe, European Research Area, or clearly European R&I context.

### Diagnostics

Record the actual dominant reason for rejection/defer: `insufficient_text`, `no_direct_eu`, `no_ri`, `no_geopolitics`, or `no_substantive_bridge/aboutness`. Do not collapse these into one scope label.

## Publication quality

English remains a hard publication invariant. Core messages must be source-backed and informative. The displayed line states the claim itself; it does not prepend a generic attribution phrase.

## Matrix hand-off

Pass-1 records that clear admission are handed to the matrix with their source-backed summary/relevance evidence. Direction vocabulary may support independence/competitiveness interpretation, but it is not an additional admission gate.

## V17.10 manual candidate lane

A curated manual list is a candidate/recovery source, not evidence. A newly supplied item may enter the radar only after its underlying primary source is retrieved/verified and passes this same admission profile. Metadata-only records defer. Secondary references, forthcoming/unpublished items and context-only references remain outside the matrix. Provenance records whether discovery was automated, manual, or both.
