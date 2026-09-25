# v26 — the engine writes the cards

The reasoning engine now does both halves of the job inside the GitHub scan: it reasons from the findings, and it states what the reasoning found. No LLM runs at card time, and no card text is fixed in advance: every card is recomputed from the current evidence on each scan, so assessments change and cards move between page and reserve as before.

## 1. Better reasoning from findings

**Coherence gates** (`_coherence` in `claim_reasoning_live.py`). Candidate formation stays broad, so the engine can still connect items in new ways. Before a card goes public, the connection must have a mechanism:

- **Shock:** a named exposure mechanism for the pressure and the asset's field (`card_writer.EXPOSURE_MECHANISMS`). Domain-specific pressures (rule change, technology leap, chokepoint, provider, data, takeover) must come from the asset's own field.
- **Practice before rules / operating before rules:** the later rule must concern the same practice (same country, a shared name, or shared distinctive vocabulary).
- **An old link returning:** the historical link must be at least two years older, and a current side must echo it.
- **Rules in collision:** two different requirements, not the same one twice.
- **Unused lever:** a real gap, and a live public instrument as the lever.
- **Money without a yardstick:** the instrument and the objective must be linked.

**Grounding fixes.**

- "Becoming conditional" now needs conditionality of access, participation, funding or approval. "Absorptive conditions" and "resilience requires" no longer count.
- A technology leap needs an actual leap, not a mention of "frontier AI".
- An abrupt rule change needs a ruling, repeal or ban, not the words "AI Act".
- A chokepoint needs a supplier dependence, not an "innovation bottleneck".
- "Post-war" is not war.
- For trend sides, a reviewed rule placed on an activity (data-centre standards) counts as a constraint on that activity. For objects that are themselves rules (research security), a new rule is growth of the object.

**New reasoning moves** (`scripts/reasoning_moves.py`). These are connections the object graph cannot see, each with its own mechanism:

- `magnitude_contrast`: amounts stated in separate sources, compared. One project against a whole programme, one deal against a whole sector, or two EU instruments with very different sizes.
- `external_opening`: a restriction abroad next to a European gain in the flow it redirects.
- `cross_pressure`: two European policies acting on the same people in opposite directions.
- `common_driver`: one outside dependency named across several fields.
- `national_convergence`: three or more member states building the same thing separately.

**Deliberate mix.** Wow 1–5 still gets three slots each. When three or more kinds of reasoning are ready for a page, no single kind takes more than four slots, and each card shows a chip naming its kind.

## 2. Better reasoning to what the card says

`scripts/card_writer.py` writes every card as a **point about the EU R&I system**, not a report of who did what.

- **Headline = the point.** Trends are stated as one idea ("AI and compute: money is arriving faster than the rules on how it can be used"); patterns, chains, collisions, levers, scale checks and shocks likewise. No country, company or programme names; places appear only as counts ("in three member states").
- **First line = the reasoning:** why it matters or what follows (the stake, the condition that would make an opportunity count, the lock-in risk, the ratio's meaning).
- **Small print = the evidence and its status:** "Evidence: three studies and the EU, since May." plus what is sourced and what is the Radar's inference. The records themselves are in the card's source list.
- **Single events** (one source reporting one action) are *early signs*: stated at system level ("Quantum pilot lines are starting to get dedicated money"), chip "Early sign", and ranked after the points within their wow level, so they only fill space the points leave.
- **Labels:** `reader_labels.py` names every controlled object. Engine keys never reach a reader.
- **Reader Language:** the exact lines readers see (`reader_lead`, `reader_basis`, plus the existing fields) enter the optional LLM language queue, so wording can be polished later without touching the engine.

The reader pages (Trends, Risks & Opportunities, Ongoing Phenomena, External Shocks) render this copy through `reader_cards.js`. Page-level title pools and rewrites are removed.

## Guardrails kept

- Scanner, Deep Scan authority, admission and raw evidence are untouched.
- Moves and the card writer are fail-safe: an exception never blocks a scan.
- Falsifier query text for existing grammars is unchanged, so the falsifier ledger keeps matching.
