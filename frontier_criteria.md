# Sovereignty-Frontier Signal — analytical criteria

This criterion is an **analytical lens above the cumulative Radar**. It is not an admission rule for Strands A, B or C, and it never deletes or rewrites accepted radar material.

## Definition

A Sovereignty-Frontier Signal is an observed event, decision, trend break or emerging development, arising in any domain and at any point along the research and innovation chain — from fundamental science through applied research, infrastructure, talent, capital, standards and regulation to defence and security research — that materially changes the answer to at least one of three questions about the European Union:

1. **Sustain:** could the EU sustain the activity in question without reliance on a non-EU actor?
2. **Compete:** if it did so, would it remain competitive against the best available alternative?
3. **Fail:** what could cause either of those conditions to fail?

The signal qualifies irrespective of its subject matter, origin or apparent proximity to EU policy. What matters is whether it alters the EU's position on the trade-off between independence and performance, either by shifting the trade-off itself or by revealing that the EU is losing on both counts at once. A signal that moves two or more of the three questions, particularly in opposite directions, is a strong candidate.

Among candidates, priority is given to developments whose effects reach across multiple fields or institutions, whose consequences would be difficult to reverse once realised, which appear under-attended in EU policy, and for which an identifiable EU-level or member-state actor retains a meaningful opportunity to act within approximately two years.

## Axis 1 — where the signal bites

1. **Knowledge & people** — science, publication, collaboration, talent flows and training.
2. **Infrastructure & inputs** — compute, data, instruments, materials, energy and facilities.
3. **Conversion** — firms, products, capabilities, defence and dual-use, capital and procurement.
4. **Rules & institutions** — export controls, research security, standards, funding programmes and decision speed.

## Axis 2 — what it does to the EU position

- **A. Opening** — more independent and more competitive.
- **B. Costly autonomy** — more independent, less competitive.
- **C. Productive dependence** — more competitive, less independent.
- **D. Double loss** — less independent and less competitive.

## Cell names

| R&I-chain location | A. Opening | B. Costly autonomy | C. Productive dependence | D. Double loss |
|---|---|---|---|---|
| Knowledge & people | Talent windfall | Closed lab | Borrowed brains | Brain drain |
| Infrastructure & inputs | Home chokepoint | Expensive mirror | Rented frontier | Cut supply |
| Conversion | Home champion | Protected niche | Foreign exit | Hollowing out |
| Rules & institutions | Rule-setter | Fortress rules | Rule-taker | Gridlock |

Column A is opportunity, B is the sovereignty bill, C is productive exposure, and D is the alarm column. Column C deserves particular monitoring for movement toward D if a partner changes access, terms or political willingness.

## Triage inside a cell

The matrix classifies the **kind** of situation. Four criteria rank signals within and across cells:

- **System reach** — whether effects cross fields, institutions or multiple links of the R&I chain.
- **Reversibility** — whether capability loss, lock-in, infrastructure choices, standards, firm exits or talent flows would be difficult to unwind.
- **Attention gap** — whether the development appears under-reflected in mainstream EU policy attention.
- **Two-year actionability** — whether a nameable EU-level or member-state actor still has a meaningful lever.

The current static implementation treats the attention-gap criterion as a transparent **proxy** based on recency, source type and direct EU-policy linkage. It does not claim to know the true level of policy attention.

## Implementation boundary

`frontier/frontier.js` reads the same cumulative `radar.json` used by the existing pages. Strand C is the primary signal pool. Accepted A/B evidence can also surface when its extracted finding contains an explicit observed change or decision. The result is computed in the browser and is not written back to `radar.json`.
