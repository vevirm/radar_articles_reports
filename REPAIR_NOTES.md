# V17.8.1 — surgical precision + major-EU-R&I ranking

V17.8.1 fixes the excessive deletion caused by V17.8.0.

## Core correction

V17.8.0 incorrectly treated “major EU R&I under geopolitical competition” as a hard historical admission gate and also disabled broad journals. Because saved records contain shortened summaries rather than full abstracts, re-auditing the whole corpus against that gate produced many false negatives.

V17.8.1 changes the architecture:

- broad peer-reviewed journals are retained;
- source tier is a ranking/confidence factor, not a deletion rule;
- quality-profile migration uses `surgical_precision_cleanup()` instead of a fail-closed full-corpus re-audit;
- saved A/B records are removed only for high-confidence contamination or malformed/excluded/non-English-title cases;
- major EU R&I/geopolitical relevance is calculated by `major_eu_ri_priority_score()` and controls ordering of new and historical A/B evidence;
- live A admission still rejects obvious sports/consumer contamination;
- live B admission remains methodologically strict and requires a policy/R&I/technology-system destination.

## Strand C

C remains much narrower than A/B. Direct EU/European weak signals are preferred. A narrow class of external strategic shocks (for example export controls, semiconductors/compute, quantum, critical inputs or research-system changes) may pass the news prefilter, but they still must anchor to an existing Strand-A evidence base. Generic foreign AI/business, health, education and political stories do not qualify.

## Sovereignty Frontier

The V17.8.0 risk corrections are retained:

- ambiguous evidence is not forced into +/+;
- column A is a **demonstrated opening**, requiring realised gains on both autonomy and competitiveness;
- plans, strategies, recommendations and funding calls are not openings;
- risk columns receive stronger ranking weight;
- matrix discovery prioritises B/C/D risk cells before searching for empty opening cells.

## Bundled-state migration

Starting from the supplied `radar (17).json`:

- Strand A: **109 → 108** (table-tennis false positive removed)
- Strand B: **27 → 23** (four obvious domain/method false positives removed)
- Strand C: **22 → 9** (generic/unanchored weak-signal noise removed)
- Frontier-only evidence: **19 → 19** (preserved; classifier decides qualification)

Regression suite: **212 tests pass**.
