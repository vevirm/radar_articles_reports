# V17.7.3 — matrix-first depth + interpretive weak signals

The supplied 2026-08-23T18:22Z state showed that V17.7.2 substantially improved overall recall (8 new A and 2 new B), but not where the radar most needed evidence. Seven of the sixteen Frontier cells were still empty, only 14 scholarly gap queries were allocated in the run, Strand C added 0 items, and the scanner finished after 415.7 seconds despite a 1200-second scanner budget.

V17.7.3 changes allocation rather than lowering the A/B quality gate.

## 1. Empty Frontier cells now dominate gap discovery

When any 4×4 Frontier cell has zero evidence, zero-count cells receive the first gap-search slots. The initial scholarly gap lane expands from 14 to 28 queries. With the supplied state, that gives each of the seven empty cells four distinct scholarly formulations before near-empty cells receive a scholarly gap slot.

The current zero cells are: Knowledge-C, Knowledge-D, Infrastructure-C, Infrastructure-D, Conversion-D, Rules-A and Rules-C.

News gap coverage expands from 8 to 14 formulations, giving zero cells repeated current-evidence searches. Gap-specialist institutional sources expand from 6 to 10 extra sources per scan.

## 2. Spare runtime becomes real depth, not an early exit

The overall scanner budget stays 1200 seconds. After the normal concurrent scholarly/news phase and institutional phase, a matrix-first deepening phase uses remaining runtime.

The deepening phase:

- searches zero-count cells first;
- fetches deeper OpenAlex/Crossref result pages directly, without re-fetching page 1 merely to advance depth;
- uses up to 32 bounded waves of 14 queries;
- tracks depth independently through the existing persistent result-depth state;
- moves to the next-thinnest cells only after the zero-cell depth bank is exhausted;
- stops with a 60-second scanner-finalisation reserve.

OpenAlex and Crossref normal gap depth ceilings increase from 6 to 10 pages. Source-specific 429/fatal failures disable only the affected deepening family rather than causing repeated hammering.

## 3. Strand C now matches the intended interpretation role

C remains A-anchored and curated-source-only, but a candidate no longer has to look linguistically “early” (pilot/draft/trial/delay) or explicitly say “new study shows”. A consequential current change can now enter the C prefilter when it combines:

- a real change/action (launch, approval, restriction, investment, partnership, closure, scale-up, export control, regulation, etc.);
- R&I/science/technology substance; and
- strategic stakes such as capacity, competitiveness, dependence, access, collaboration, talent, sovereignty or security.

The later Strand-A anchor is still mandatory. A generic consumer technology launch still fails. A US/China action without an EU mention can be considered by the prefilter only when it is materially R&I/strategic; without a matching A anchor it is discarded.

The signal-discovery version changes to `v17.7.3-matrix-first-interpretive-signals`, so the next run gets one 30-day C recovery scan and then returns to the seven-day rolling window.

## 4. Weak signals receive protected spare-time searches

During matrix depth waves, a bounded weak-signal follow-up runs independently of A/B allocation (maximum four follow-up passes). It uses empty-cell queries plus direct searches for talent flows, technology dependence, research cooperation, critical-technology capability and new empirical competitiveness evidence.

## 5. State preservation

The bundled `radar.json` is byte-for-byte identical to the supplied `radar (14).json`: 66 Strand A, 19 Strand B and 5 Strand C. The V17.7.2 A/B recall profile is deliberately unchanged, so this patch does not reset the accepted corpus or reopen A/B solely because allocation changed. Only the C discovery version changes to trigger the intended one-time weak-signal recovery window.
