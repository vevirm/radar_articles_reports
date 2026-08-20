# R&I × Geopolitics Radar — V17.2 incremental scanner

V17.2 keeps the V17 evidence logic and Insights page, but changes **how discovery work is scheduled** so a 30-minute GitHub Actions job cannot repeatedly spend its whole runtime on the same reports or the same first scholarly queries.

## What is unchanged

The evidence/admission logic remains V17:

- **Strand A:** substantive EU/Europe + R&I/science/strategic-technology + geopolitics/geoeconomics/economic-security connection.
- **Strand B:** substantive foresight/horizon-scanning/scenario methodology on that same EU + R&I + geopolitical substance.
- **Strand C:** curated factual weak signals linked to the evidence base or an approved strategic watch theme.
- The site is **cumulative**. Previously accepted A/B/C items remain visible. New scans append genuinely new identities; they do not replace the corpus.
- `/briefing/` remains the balanced **Insights** view with Research publications, EU & institutional reports, and Weak signals.

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

This package includes a `repository_bundle_seed` marker in `radar.json`. On the first scan after upload, the scanner checks recent Git history. If the repository had a larger cumulative `radar.json` immediately before the upload, it merges that larger A/B/C corpus back before scanning. The one-run seed marker is then removed.

## Tests

Run:

```bash
python -m unittest discover -s tests -v
```

The package includes the earlier V12–V17 tests plus V17.2 tests for persistent cursors, non-wrapping batches, per-run caps, known-item loading, separate source-family time slices, and immediate-push/12-hour workflow triggers.
