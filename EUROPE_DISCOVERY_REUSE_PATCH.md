# European publication discovery reuse — 27 October 2026

Based on the uploaded **Europe Radar — Exact Discovery Routes and How to Reuse Them** guide and the repository as supplied.

## Changes

- Configured official Council RSS routes and the EPO news RSS candidate route, while preserving existing domains, source tiers and scan budgets. **CORDIS and EPO already existed as tier-1 sources** in this repository; they were not duplicated or downgraded. Added source-specific publications/research hubs and URL/link hints for Council, CORDIS, EPO, OECD and Chatham House.
- Improved institutional RSS validation in both regular (`scan_radar.py`) and private Strand-A (`scan_radar_deep_a.py`) scanner code. HTML block responses are not healthy feeds; an empty but valid RSS/Atom feed is healthy and quiet. A reachable publication hub with no usable candidates is likewise quiet rather than a false transport failure. Entry links must belong to the source domain, as must configured feeds and publication-hub seeds.
- Recover visible DOI-publisher-page abstracts in bounded semantic abstract sections (40–1500 words, first five matching elements). Uses the same existing DOI response, no new network request and no admission shortcut.
- Replaced hard-coded 2025/2026 adapter ranking with the dynamic configured scan date span and made sitemap year scoring dynamic. Kept source rotation and global budgets unchanged.
- Deduplicated overlapping adapter/feed candidate jobs before the ordinary sitemap jobs.
- Added per-domain diagnostics (`scan_diagnostics.institution_discovery_routes`) to regular scans: adapter/feed candidate jobs, successful hub/feed responses, sitemap entries, fallback jobs, and whether a discovery route recovered from absent sitemap entries. These measure candidate discovery, **not admissions**. Existing `source_transport_attempts` and `source_transport_health` are unchanged.
- Added `python scripts/audit_source_coverage.py` (read-only) with `--json` support and a five-source focus view. The main workflow runs it after regular scans as a non-blocking diagnostic step. The most recent scan before this patch will not have per-route detail.
- Added deterministic offline regressions to the normal preflight gate, updated the workflow-contract check to recognize the existing production preflight step name, and refreshed the explicit scanner-core hash baseline so the existing scanner freeze workflow remains functional. No corpus/state files were intentionally changed.

## Running

```bash
python scripts/run_scan_preflight_tests.py
python scripts/audit_source_coverage.py
python scripts/audit_source_coverage.py --json > source-coverage.json
```

The original scan evidence criteria, Strand-A/B/C gates, fair selection and saved cursors remain in place. **No forced backfill, finding quota, or relaxation of quality checks.** No live GitHub Actions scan has been performed here, so these endpoints remain configured—not verified as actually reached/parsed by a production scan. Inspect the audit and GitHub scan logs after deployment.

The historical scanner was not altered: adapting the source routes to past-date searches requires separate historical-specific registration and an explicit historical date policy.
