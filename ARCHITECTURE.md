# Radar architecture — V17.3

## 1. Cumulative state

`radar.json` is both the cumulative public dataset and the persistent scan checkpoint. A/B/C items are retained and deduplicated. `scan_state` stores independent source-family cursors so the next run continues instead of restarting.

## 2. Discovery scheduling

Weak signals, OpenAlex and Crossref begin in parallel. Institutional crawling starts as a separate bounded phase after that parallel phase.

The large scholarly/report universes are rotated across runs:

- OpenAlex: 40 queries/run out of 145.
- Crossref broad: 35 queries/run out of 145.
- Crossref priority: 45 journal/query tasks/run out of 216.
- Institutions: 18 sources/run out of 57.

A batch never wraps inside one run; the final batch of each cycle is shorter. The next cursor is saved in `radar.json`.

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

The public dataset has one source of truth: `radar.json`. The three site views only read it.

- `/` — cumulative Radar: accepted A/B evidence and Strand C signals.
- `/briefing/` — balanced Radar Insights: research, policy/report evidence and weak signals.
- `/frontier/` — Insight Summary / Sovereignty-Frontier Signals: a strict decision-attention lens.

The Sovereignty-Frontier layer is implemented in `frontier/frontier.js`. It does not modify scanner state or write classification fields back to `radar.json`. This separation protects historical material while allowing the prioritisation logic to evolve independently.

