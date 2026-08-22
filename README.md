# R&I × Geopolitics Radar — V17.4 gap-priority + opportunities/risks

V17.4 keeps the cumulative/incremental V17.2 source rotations and the strict V17.3 Sovereignty-Frontier classifier, but now uses the matrix itself to improve discovery coverage. It also adds a fourth analytical view: **Greatest Opportunities & Risks**.

## What remains unchanged

- The Radar is cumulative: previously accepted A/B/C items remain unless an explicit quality migration rejects an old item under the established V17 substance gate.
- OpenAlex, Crossref and institutional sources keep their persistent rotating cursors and existing per-run caps.
- The Sovereignty-Frontier admission gate remains strict. Empty cells are never padded with weak matches.
- `radar.json` remains the single source of truth. The Frontier and Opportunities/Risks pages are read-only.
- This delivery embeds the live cumulative `radar.json` you supplied (257 A/B/C records) directly. The older `repository_bundle_seed` + Git-history recovery mechanism remains available in the scanner as a fallback for future seed-based upgrades, but this live file does not need that marker.

## New in V17.4: matrix-gap-aware discovery

Before each scan, `scripts/frontier_coverage.js` runs the exact same `frontier/frontier.js` classifier used by the browser and counts occupancy across all 16 Sovereignty-Frontier cells. The scanner then adds **six** extra curated global-news queries for the currently emptiest/sparsest cells.

Cells with the same occupancy rotate using a persistent `frontier_gap_cursor`, so one stubborn gap does not monopolise every run. This is discovery prioritisation only: newly found items still have to pass the existing weak-signal admission logic and the existing Frontier classifier.

The selected cells and pre-scan coverage counts are saved in scan metadata for auditability. The discovery profile version is bumped, so the first V17.4 scan receives the existing 30-day weak-signal recovery window before returning to the normal seven-day rolling window.

## New in V17.4: Greatest Opportunities & Risks

`/priorities/` reads the full cumulative `radar.json` and the same Frontier classifier. It presents two deliberately simple bullet lists:

- **Greatest opportunities:** A / Opening signals, where autonomy and competitiveness improve together.
- **Greatest risks:** D / Double loss first, then C / Productive dependence and B / Costly autonomy.

The lists are cumulative rather than latest-only. Older qualifying items remain available and can be expanded with **Show all cumulative**. Ranking emphasises structural triage rather than dropping items because they are no longer new.

## Sovereignty-Frontier Insight Summary

`/frontier/` remains the 4 × 4 independence–competitiveness matrix. Rows identify where the signal bites — **Knowledge & people**, **Infrastructure & inputs**, **Conversion**, or **Rules & institutions**. Columns identify the effect — **A Opening**, **B Costly autonomy**, **C Productive dependence**, or **D Double loss**.

## The V17.2 fix: persistent source cursors

`radar.json` now stores `scan_state` with independent cursors for:

- OpenAlex scholarly queries;
- Crossref broad scholarly queries;
- Crossref priority-journal/query tasks;
- institutional report sources.

Every scheduled scan resumes from those saved cursors. It does **not** start again at query/source 1.

Per run, the scanner currently processes at most:

- **40 / 145** OpenAlex scholarly queries;
- **35 / 145** Crossref broad queries;
- **45 / 216** Crossref priority-journal tasks;
- **18 / 57** institutional sources.

The last batch in a cycle is shorter rather than wrapping back to the beginning, so the same early queries are not repeated before the checkpoint is saved. A complete discovery cycle takes at most about **5 scheduled runs**. With the 12-hour schedule, the whole configured scholarly/report universe is revisited across roughly 2.5 days, while weak-signal discovery remains fresh every 12 hours.

## Known-item skipping

Before network discovery starts, the existing cumulative corpus is loaded into identity sets.

- OpenAlex/Crossref records whose DOI or normalized title is already known are skipped **before expensive classification**.
- Institutional sitemap URLs already present in the corpus are skipped **before page/PDF fetching when the saved URL matches**.
- Successfully fetched institutional page fingerprints are also persisted (including pages that were later rejected); unchanged pages are not downloaded again on the next source cycle. A changed sitemap `lastmod` creates a new fingerprint and allows a revisit.
- Previously admitted weak-signal headline/source identities are skipped before signal classification.
- Final merge/deduplication still runs as a second safety layer.

APIs can still return a known record in a search response; public APIs do not provide a practical “exclude these thousands of DOIs” filter. The important change is that V17.2 no longer runs the entire query/source universe on every 12-hour scan, and known records are discarded as early as possible.

## Progressive four-month backfill

A repository upgrade still gets the intended **four-month A/B backfill**, but V17.2 completes it progressively rather than trying to do everything in one job.

Each source family stays in four-month backfill mode until its persisted cursor has completed a clean full cycle. If a source family hits its local budget or fails, the cycle is marked incomplete and a later cycle retries it instead of falsely declaring the backfill finished.

After backfill, each rotating source batch uses the normal **14-day overlap** so delayed indexing can still be discovered.

## Runtime protection

- GitHub Actions job timeout: **30 minutes**.
- Scanner hard budget: **20 minutes**.
- Network/commit reserve: **150 seconds**.
- Weak-signal time slice: **240 seconds**.
- OpenAlex time slice: **360 seconds**.
- Crossref time slice: **450 seconds**.
- Institutional-report time slice: **480 seconds**, started after the parallel news/scholarly phase.

Because the first three families run in parallel and reports have a separate bounded phase, one family cannot monopolise the whole scanner runtime. `radar.json` is written before the GitHub job timeout and then committed.

## Automatic operation

The active workflow is `.github/workflows/radar-scan.yml`.

- A **push to `main` immediately starts a scan**. Therefore uploading/committing this repository starts the first V17.2 scan automatically.
- It then runs automatically every **12 hours** at `23 */12 * * *` UTC.
- `workflow_dispatch` remains available for a manual run.
- Bot commits that change only `radar.json` are ignored by the push trigger, preventing an infinite scan loop.

## Safe full-repository upload

This package contains the live cumulative `radar.json` supplied for this build: **152 Strand A + 9 Strand B + 96 Strand C = 257 records**. The packaged file is copied byte-for-byte from that upload, so the repository starts with the accumulated corpus already present.

The scanner still contains the `repository_bundle_seed` + Git-history recovery code for future upgrade bundles that use a small seed, but no seed marker is required in this delivery.

## Tests

Run:

```bash
python -m unittest discover -s tests -v
```

The package includes the earlier V12–V17 tests plus V17.2 tests for persistent cursors, non-wrapping batches, per-run caps, known-item loading, separate source-family time slices, and immediate-push/12-hour workflow triggers.
