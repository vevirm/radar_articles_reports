# Radar architecture — V17.5.2

## 1. Cumulative state

`radar.json` is both the cumulative public dataset and the persistent scan checkpoint. A/B/C items are retained and deduplicated. `scan_state` stores independent source-family cursors so the next run continues instead of restarting.


## 1A. One-time inherited-corpus migration

A legacy `radar.json` without `inherited_corpus_audit_complete` is audited **once before discovery**. Saved Strand A/B evidence is checked against the current admission gate. A failing saved snippet gets one best-effort DOI/page/PDF refresh before the final keep/remove decision; Strand C is left untouched. The completed run writes `inherited_corpus_audit_complete: true`.

Normal later scans never revalidate the retained historical A/B corpus. Quality-profile changes therefore do not trigger recurring mass cleanup. The strict gate applies to every newly discovered candidate, while existing retained material stays cumulative.

## 2. Discovery scheduling

Before discovery, the scanner asks the exact Sovereignty-Frontier classifier for current 4×4 cell occupancy. Weak signals, OpenAlex and Crossref then begin in parallel. Institutional crawling starts as a separate bounded phase after that parallel phase.

The large scholarly/report universes are rotated across runs:

- OpenAlex: 40 queries/run out of 155, with up to four slots reserved for the currently sparse Frontier cells.
- Crossref broad: 35 queries/run out of 155, with up to four slots reserved for the currently sparse Frontier cells.
- Crossref priority: 45 journal/query tasks/run out of 380.
- Institutions: 18 sources/run out of 57.

A batch never wraps inside one run; the final batch of each cycle is shorter. The next cursor is saved in `radar.json`.

Weak-signal discovery receives six extra global-news searches aimed at the emptiest/sparsest Frontier cells. The same gap plan contributes targeted scholarly queries to OpenAlex and Crossref and adds a small number of gap-specialist institutional sources **on top of** the normal persistent institution rotation. `knowledge-D` (Brain drain) and `knowledge-C` receive persistent priority when equally sparse; remaining ties rotate via `frontier_gap_cursor`. Gap scholarly retrieval stays inside the preserved live corpus window by default. Gap-specific URL terms only affect fetch ranking; admission thresholds remain unchanged.

## 3. Early known-item rejection

The existing corpus is loaded before discovery. DOI/title identities, institutional links, and signal identities are used to discard known material as early as possible. Successful institutional page fetches also create persisted URL+lastmod fingerprints, so unchanged accepted **or rejected** report pages are not downloaded again on later source cycles. Final corpus merge/deduplication remains in place.

## 4. Backfill and incremental windows

A new V17.2 installation performs the four-month A/B backfill progressively. Each source family remains in backfill mode until it completes a clean cursor cycle. Failed/budget-hit cycles are remembered and do not falsely complete the backfill.

After that source family completes backfill, its rotating batch uses the normal 14-day discovery overlap.

## 5. Evidence logic

Strand A requires substantive EU/European scope + R&I/science/strategic technology + geopolitical/economic-security substance. Strand B requires substantive foresight methodology on the same substantive triangle. Strand C remains curated weak signals, anchored to A/B evidence where possible or to approved strategic watch themes.

## 6. Runtime

- GitHub job: 30 minutes.
- Scanner hard budget: 20 minutes.
- Network reserve: 150 seconds.
- News: 240-second local slice.
- OpenAlex: 360-second local slice.
- Crossref: 450-second local slice.
- Institutions: 480-second local slice after the parallel phase.

## 7. Automation

A push to `main` starts a scan immediately. Scheduled scans run every 12 hours. Pushes that modify only `radar.json` are ignored so the scanner's own commit does not trigger itself again.
## 8. Analytical pages

The public dataset has one source of truth: `radar.json`. The four site views only read it.

- `/` — cumulative Radar: accepted A/B evidence and Strand C signals.
- `/briefing/` — balanced Radar Insights: research, policy/report evidence and weak signals.
- `/frontier/` — Insight Summary / Sovereignty-Frontier Signals: a strict decision-attention lens.
- `/priorities/` — Greatest Opportunities & Risks: cumulative, simple ranked bullets derived from the same Frontier signals.

The Sovereignty-Frontier layer is implemented in `frontier/frontier.js`. Browser pages do not write classification fields back to `radar.json`. The scanner reuses that exact classifier through `scripts/frontier_coverage.js` only to choose which cells deserve extra discovery searches; accepted corpus items are still written only by the normal scanner merge logic.

