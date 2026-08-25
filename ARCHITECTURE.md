# Architecture — V17.9.0 source-aware aboutness and evidence-led matrix

The radar has four layers: discovery, admission, cumulative storage, and interpretation/ranking.

## 1. Discovery
Discovery remains broad across OpenAlex, Crossref, institutional/report sources and external-news sources. Sparse Frontier cells can still steer rotating/deepening queries. Missing text is treated as a retrieval problem rather than negative topical evidence; DOI-bearing scholarly records can receive bounded abstract recovery.

## 2. Admission
Pass-1 remains strict on substance: Europe/EU scope, an R&I dimension, and geopolitical context must be connected. Aboutness adapts to source text availability. Full documents can use recurrence and spread; abstracts are judged inside the available abstract; metadata-only records defer. Bare `EU` is contextual and cannot establish European Union scope if explicitly defined as another abbreviation.

## 3. Cumulative storage
The supplied corpus/state, cursors, fingerprints and history are preserved. This implementation change uses separate aboutness/matrix/display profile identifiers and does not bump the existing quality profile solely to force a destructive re-audit. Confirmed hard scope false positives can still be removed surgically.

## 4. Interpretation / Sovereignty Frontier
The Frontier asks two independent questions: does the evidence improve or weaken European autonomy, and does it improve or weaken R&I/industrial competitiveness? For vetted core evidence, classification can use the full source-backed record carried in `radar.json`, including summary/relevance evidence; direction-marker vocabulary supports interpretation but is not a second gate. Weak signals remain stricter and must carry an external event/mechanism.

There are no numeric cell quotas. Sparse cells are acceptable when evidence is genuinely sparse. On the bundled repaired state, 69 qualifying evidence items populate all 16 cells with unequal counts.
