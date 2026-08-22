# R&I × Geopolitics Radar — V17.5.5 semantic cells + scarcity-balanced scanning

V17.5.5 keeps the strict A/B/C admission logic and the persistent source rotations from the current repository, but fixes the remaining imbalance between **corpus relevance** and **Frontier-cell assignment**.

A paper/report may be relevant enough to stay in the radar without being evidence for a specific Sovereignty-Frontier cell. V17.5.5 therefore separates those decisions.

## Current corpus carried forward

The bundled `radar.json` is the user's latest post-scan file from 22 August 2026:

- Strand A: **72**
- Strand B: **5**
- Strand C: **19**
- Total: **96**

Its earlier corrective A/B and C cleanup markers are already complete. V17.5.5 **does not run another historical cleanup**. It preserves this current corpus and applies the improved logic to Frontier classification and future discovery.

The current OpenAlex, Crossref and institutional cursors are also preserved. The scanner does not restart source rotation just because the Frontier balancing logic changed.

## What V17.5.5 fixes

### 1. Cell assignment uses balanced semantic evidence

The Frontier is neither a loose keyword bucket nor a literal cell-label matcher. Placement now uses two stages: **row mechanism** plus **directional evidence** (independence and competitiveness). For evidence-derived signals, a substantive title/summary can establish the mechanism and relationship even when the extracted display sentence does not repeat every keyword.

Examples:

- strategic dependence on non-EU reactor technology can populate an infrastructure dependence cell even without the phrase “rented frontier”;
- critical external dependencies in technologies/resources/supply chains can count as infrastructure exposure or double loss when the document also establishes the performance downside;
- EU capacity-building, secure-supply and investment measures can populate opening cells when they plausibly improve both autonomy and competitiveness;
- `Knowledge-D / Brain drain` remains deliberately specific and still requires actual European/EU-member researcher or talent outflow.

Short tokens remain boundary-aware, so semantic broadening does not revive acronym-substring errors.

This fixes the reported false assignment of **“Mitigate, deter, escalate: Europe’s options against US economic coercion”** to Brain Drain. The report may remain relevant to the broader radar, but it does not count as a Brain Drain signal.

### 2. Short acronyms/tokens use boundaries

Short terms such as `ERC` and `AI` no longer use raw substring matching. Thus:

- `ERC` cannot match inside `coercion`.
- `AI` cannot match inside ordinary words such as `against`.

Longer deliberately stemmed terms still support controlled prefix matching where intended.

### 3. All 16 cells are scarcity-weighted

There is no permanent Brain-Drain priority or other hard-coded favourite cell.

Before every scan the scanner runs the exact browser Frontier classifier over the current cumulative corpus and counts all 16 cells. The configured balancing target is **3 qualifying signals per cell**.

For each cell:

- count 0 → deficit 3 → highest extra search weight
- count 1 → deficit 2
- count 2 → deficit 1
- count 3+ → no extra gap budget

Ties rotate using the persisted `frontier_gap_cursor`, so equally sparse cells take turns rather than one theme monopolising every run.

### 4. Scarcity affects several discovery channels

The scarcity overlay is added **on top of** normal persistent rotation. It can allocate extra capacity to:

- weak-signal/news gap queries;
- OpenAlex scholarly queries;
- Crossref scholarly queries;
- specialist institutional sources;
- institution URL ranking terms.

Every one of the 16 cells has its own discovery profiles. Empty cells get more distinct query/source attempts than merely low cells.

### 5. Normal rotation continues from the user's current state

V17.5.5 deliberately keeps the source-expansion state compatible with the user's current scanner. On the next run it continues from the existing cursors rather than restarting at query/source zero.

## What the corrected classifier sees right now

Using the bundled current `radar.json`, the balanced classifier finds **18 qualifying Frontier signals**, up from 7 under V17.5.4:

- Knowledge: A 0 / B 0 / C 0 / D 0
- Infrastructure: A 2 / B 2 / C 2 / D 1
- Conversion: A 5 / B 1 / C 2 / D 1
- Rules: A 1 / B 0 / C 0 / D 1

The current view therefore contains **4 dependence-column signals (C)** and **3 double-loss signals (D)** rather than leaving obvious dependency material outside the matrix. Empty/low cells still receive scarcity-weighted discovery on subsequent scans.

### Opportunities & risks list length

The Opportunities & Risks page no longer forces six items per side. It shows all qualifying high-ranked items available **up to a hard cap of 15 per list**. Risks and opportunities may therefore have different lengths, and the page does not print a fixed-number promise.

## First run after installing V17.5.5

The next scan does **not** re-audit the historical corpus. It performs:

1. load the current cumulative `radar.json`;
2. retain the existing A/B/C corpus and current source cursors;
3. recompute all 16 Frontier cells using the stricter semantic classifier;
4. calculate each cell's deficit to the target count;
5. allocate scarcity-weighted extra news/scholarly/institutional discovery;
6. run the normal rotating OpenAlex/Crossref/institution/news scan;
7. screen every newly discovered candidate through the existing strict admission gates;
8. save the updated corpus, coverage, deficits and cursors.

## Validation

V17.5.5 includes regression tests for:

- the economic-coercion/`ERC` false Brain Drain assignment;
- real researcher outflow mapping to `Knowledge-D / Brain drain`;
- token-boundary handling;
- proportional scarcity weighting;
- all 16 cells having discovery profiles;
- cumulative corpus preservation and cursor continuation.

Current local validation: **92/92 unittest tests** and **96/96 pytest tests** pass, plus Python and JavaScript syntax checks.

## Deployment

Upload the repository contents over the current repository, keeping `radar.json` from this package (it is the exact current file supplied for this build). A push to `main` runs the normal scanner workflow. No additional one-time cleanup marker is required for V17.5.5.
