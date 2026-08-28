# Architecture — V17.13.3 reader-first, high-recall / strict-admission radar

The system separates **discovery**, **admission**, **presentation**, and **Matrix classification**. V17.13 deliberately widens discovery while keeping admission conservative.

## 1. Discovery entrances

### Automated discovery

`scripts/scan_radar.py` rotates across OpenAlex, Crossref, direct institutional/journal sources, futures-method searches and Matrix-gap searches. V17.13 adds a small `finding-context` scholarly lane whose queries are derived from recurring themes already visible in Strand A.

The current findings are therefore allowed to influence **where the scanner looks**, but not **what it automatically accepts**.

### Researcher fallback attention

`priority_people.json` contains the named-researcher attention list. The scanner resolves authors where possible and sends their recent works through the same scholarly candidate builders as ordinary discovery. In V17.13 this lane is mainly used when normal scholarly yield is low or Matrix coverage is very sparse. A name is never an admission credential.

### Manual candidate ingestion

`scripts/manual_ingest.py` parses common office/data formats, normalizes bibliography/URLs, deduplicates against state and targets the exact URL supplied by the curator. The curator file is a candidate/recovery source, not primary evidence.

When runtime retrieval is unavailable, a reviewed-evidence cache may stand in only when it is explicitly tied to the same canonical supplied URL and records source verification/evidence mode. The supplied URL remains provenance even when a primary URL is resolved.

## 2. Strand-A admission

A substantive finding needs:

1. direct EU/European scope;
2. genuine R&I/science/technology-system substance; and
3. strategic context.

There are two routes for item 3.

**Explicit route:** the source directly discusses geopolitics, geoeconomics, economic/research security, strategic competition or equivalent context.

**Triangulated route:** literal geopolitical language is absent, but at least two independent strategic families are present and at least one is relational/control-oriented. Current families cover dependence/control, competition/capability, international coordination, security/resilience, rules/standards power and research-talent position.

This prevents a single vague cue such as “competitiveness” from becoming a permissive gate.

Source-aware aboutness remains in force: full text can use recurrence/section spread; abstract-only material is judged on the evidence that actually exists; metadata-only material defers.

## 3. Strand B and Strand C

Strand B remains a method lane: a source has to develop/adapt/extend/refine a reusable futures or forward-looking R&I/technology-analysis method. Merely applying a method or describing a trend is not enough.

Strand C remains the weak-signal lane. Its protected follow-up query wave is disabled in V17.13. After merge, C is capped at 15% of the public A+B+C corpus; that percentage is a maximum, never a target.

## 4. Hard public time boundary

The public evidence corpus is always the latest four calendar months. `preserved_corpus_floor()` now returns the rolling floor rather than preserving older saved state. The rule also applies to `frontier_evidence`, so historical Matrix-recovery rows cannot silently stretch the public window.

## 5. Reader write boundary

Raw bibliographic evidence and the reader-facing claim are separate fields. `plain_language_claim()` is the final scanner write boundary for newly written claims; frontend helpers provide the same treatment for older stored rows.

The rule is: state the substantive point in ordinary language, omit biography/method boilerplate unless it changes the meaning, and keep titles/authors/source/date/link separately available.

## 6. Primary site components

- `read/` — eight stable issues, expandable branches/subissues, live evidence below them.
- `/` — main A/B/C radar.
- `frontier/quick/` — simple 4×4 Matrix with claims and counts only.
- `frontier/` — full Matrix with evidence/source detail.
- `priorities/` — decision-oriented risks and opportunities.
- `briefing/` — secondary evidence browser, not a primary navigation destination.

This is progressive disclosure: the first screen should answer “what are the main issues?”, the quick Matrix should answer “what direction is the evidence pointing?”, and detail should appear only when requested.

## 7. Matrix hand-off

All admitted Strand-A records are passed to the Matrix candidate classifier. V17.13 removes the previous hidden frontend `dynamic` pre-filter. Matrix admission is still evidence-led: a record is shown only when row and direction can be supported.

The internal classifier keeps stable analytical concepts (knowledge, infrastructure, conversion, rules; independence/control and competitiveness axes) for continuity. The reader-facing UI translates them to simpler language; see `frontier_criteria.md`.

Curator cell hints are stored as hypotheses (`curator_primary_cell`, `curator_cells`). Reviewed underlying-source fields (`matrix_dimension`, `quadrant_claimed`, `quadrant_implied`) override keyword re-inference when present. Claimed and evidence-implied direction remain distinct.

## 8. State and provenance

Automated and manual provenance remain explicit. Manual ingestion is not a live scan. Packaging may normalize display claims and enforce the date boundary without advancing scanner cursors or fabricating `last_updated`.

V17.13's bundled state keeps the uploaded scanner timestamp and records a four-month floor of 2026-04-28.



## V17.13.3 Matrix-balance rotation

Matrix coverage is now a search-allocation input. The scanner calculates the current 4×4 occupancy with the same classifier used by the Matrix page, takes the bounded median cell count as the moving depth target, and directs reserved gap queries toward cells below that target. Empty cells remain first priority, but thin non-empty cells continue receiving attention until they approach the current Matrix middle. Coverage is recomputed during depth waves so the target list can change within a scan. This affects discovery effort only; it never lowers admission criteria or forces equal cell counts.

## V17.13.2 subject, language and external-shock boundary

- Strand A's subject is EU/European R&I in geopolitical context, not general innovation with an EU relevance score.
- Non-EU material has one exceptional route: a major R&I capability shock + a same-domain current EU anchor + a specific one-sentence Europe-position bridge, explicitly marked as radar inference.
- English applies to the evidence used for admission and reader claims. Non-English publications can pass through a substantive source-provided/indexed English abstract or summary; no machine-translated text is treated as evidence.
- The reader-first main radar keeps progressive disclosure: the easy card is short, while **All record details** and **Show all details** expose the underlying user-facing record fields.


## V17.13.2 reader-point contract

- Primary reader points are complete sentences of at most 120 characters.
- Points must begin with an explicit actor, system or topic; vague anaphora such as “this”, “these”, “it”, “they”, “the study”, “the findings” and “the developments” are rejected.
- Long source prose is reduced only at sentence/clause boundaries. Hard cuts and ellipses are forbidden.
- The same shared `RadarInsights.readerPoint()` boundary is used by the main radar, Read page, Quick Matrix and full Matrix claim surfaces.
- `plain_language_claim()` applies the same rule at scanner write time, so new `core_message` values are safe before they reach the frontend.

## V17.13.4 source-attention lanes

The source planner now has two bounded preference lanes inside the existing rotation: (1) SCImago-Q1-verified journal source sweeps and (2) official-EU institutional sweeps. Both have independent persisted cursors. The general journal and general institution rotations remain active and retain a configured minimum share, so source preferences cannot starve broad discovery. Admission/classification code is unchanged.
