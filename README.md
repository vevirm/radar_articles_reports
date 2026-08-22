# R&I × Geopolitics Radar — V17.5.4 semantic cells + scarcity-balanced scanning

V17.5.4 keeps the strict A/B/C admission logic and the persistent source rotations from the current repository, but fixes the remaining imbalance between **corpus relevance** and **Frontier-cell assignment**.

A paper/report may be relevant enough to stay in the radar without being evidence for a specific Sovereignty-Frontier cell. V17.5.4 therefore separates those decisions.

## Current corpus carried forward

The bundled `radar.json` is the user's latest post-scan file from 22 August 2026:

- Strand A: **69**
- Strand B: **5**
- Strand C: **19**
- Total: **93**

Its earlier corrective A/B and C cleanup markers are already complete. V17.5.4 **does not run another historical cleanup**. It preserves this current corpus and applies the improved logic to Frontier classification and future discovery.

The current OpenAlex, Crossref and institutional cursors are also preserved. The scanner does not restart source rotation just because the Frontier balancing logic changed.

## What V17.5.4 fixes

### 1. Cell assignment now requires cell-specific evidence

The Frontier is no longer a loose keyword bucket. Before a signal can occupy a cell, the observed headline/finding must express that cell's actual mechanism.

Examples:

- `Knowledge-D / Brain drain` requires direct evidence of researcher/scientist/talent outflow, people leaving, failed retention, etc.
- `Infrastructure-D / Cut supply` requires actual access loss, supply disruption, shortage, chokepoint or no-substitute evidence.
- `Conversion-D / Hollowing out` requires firm exit, relocation, closure, loss of production/capability, scale-up failure, etc.
- `Rules-D / Gridlock` requires decision failure, blocked access, conflicting rules, export-control blockage, etc.

The same principle applies to all 16 cells.

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

V17.5.4 deliberately keeps the source-expansion state compatible with the user's current scanner. On the next run it continues from the existing cursors rather than restarting at query/source zero.

## What the corrected classifier sees right now

Using the bundled current `radar.json`, the stricter Frontier classifier currently finds **7 qualifying Frontier signals**:

- Knowledge: A 0 / B 0 / C 0 / D 0
- Infrastructure: A 2 / B 0 / C 1 / D 0
- Conversion: A 3 / B 0 / C 1 / D 0
- Rules: A 0 / B 0 / C 0 / D 0

This is intentionally more conservative than the previous display. A cell stays empty until evidence genuinely fits it.

With the existing gap cursor preserved, the next scan will prioritise a rotating subset of the highest-deficit cells, then subsequent scans continue rotating through the remaining sparse cells. Once cells begin filling, the extra budget automatically shifts toward whichever cells remain emptiest or thinnest.

## First run after installing V17.5.4

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

V17.5.4 includes regression tests for:

- the economic-coercion/`ERC` false Brain Drain assignment;
- real researcher outflow mapping to `Knowledge-D / Brain drain`;
- token-boundary handling;
- proportional scarcity weighting;
- all 16 cells having discovery profiles;
- cumulative corpus preservation and cursor continuation.

Current local validation: **93 tests pass** plus Python and JavaScript syntax checks.

## Deployment

Upload the repository contents over the current repository, keeping `radar.json` from this package (it is the exact current file supplied for this build). A push to `main` runs the normal scanner workflow. No additional one-time cleanup marker is required for V17.5.4.
