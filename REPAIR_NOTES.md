# V17.11.0 — exact-link reviewed manual evidence repair

V17.11.0 fixes the failure mode where a matrix-oriented manual list was parsed correctly but left inert because packaging had used `--no-fetch` and the runtime HTTP client could not retrieve source text.

The corrected path is: **exact supplied URL → underlying/reviewed source evidence → substantive gate → matrix classification**. There is no broad web-search step in manual ingestion.

Key repairs:

- reviewed evidence must be bound to the exact curator-supplied URL;
- resolved primary records are allowed only for explicit bibliographic/primary-source resolution cases and preserve the starting URL;
- reviewed substantive evidence can establish aboutness when the scanner's lexical heuristic misses an implicit geopolitical mechanism, while retaining the scanner result for diagnostics;
- curator matrix cells remain hypotheses, never admission or classification gates;
- reviewed `matrix_dimension` controls the frontend row instead of topic-word re-inference;
- `quadrant_claimed` remains separate from `quadrant_implied`;
- title-only deduplication is tightened to prevent distinct but similarly named sovereignty papers from merging;
- reviewed weak signals can use substantive matrix evidence without mandatory directional keyword matches.

Applied to the matrix-oriented supplement, the repair newly admits **17 substantive sources and 2 weak signals**, all of which appear in the Frontier. No live-scan timestamp or cursor was changed.
