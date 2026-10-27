# Historical Archive + Deep Scan V2: targeted patch

**Scope:** Historical source-age scanner and Deep Scan V2 package source recovery only. Built on `Europe_Radar_Improved_Scanners_FULL.zip` from the previous step, 27 October 2026.

## Installation

Extract the ZIP **into the existing repository root**, preserving the included directory names. Replace existing files at the exact same paths and add the two new test files and this README. Do **not** create a new enclosing project folder. No `radar.json`, historical archive data, or Deep Scan state is supplied or overwritten by the patch.

## Changed/new paths

- `historical/config.json` — source-owned archive hub routes and bounded per-source limits.
- `historical/scan_historical.py` — follows promising archive/catalogue links up to two additional levels; retains existing regular adapter and sitemap discovery, publication-date verification and Main-aligned historical admission criteria.
- `historical/tests/test_historical_archive_discovery.py` — tests dated cards, archive depth, domain scoping, historical age and year-only evidence safety.
- `scripts/deep_read_works.py` — extracts first-party PDF/full-document leads from already-fetched HTML, follows at most three primary-document links per record, rejects explicit contradictory DOI/title metadata, checks publisher domain on followed links, and verifies exact DOI on OpenAlex recovery. Any unverified text is labelled, not certified.
- `scripts/prepare_deep_scan_package.py` — includes `identity_status` and `identity_note` with retrieved material and instructs the human/LLM verifier to independently check them. No decision criteria or importer gates changed.
- `tests/test_deep_primary_document_recovery.py` — offline tests for first-party primary links, mismatched identity, unsafe redirects and recovery limitations.

## Protections unchanged

- Historical means *actual publication date* from `2015-01-01` through the day **before** the rolling live-radar six-month cutoff, not page crawl year, PDF creation time or the subject year in a report title.
- The original Historical scanner's Main A/B admission and evidence gate remains authoritative. No automatic backfill or changes to persistent research state, budgets or findings targets.
- Deep Scan V2 original manual KEEP / REVIEW / DROP / DEFER / DROP_UNVERIFIABLE decision policy, source trust standards, importer, duplicate rules and three-validated-attempt handling are untouched. New identity labels only help the verifier.
- OpenAlex API credentials are never written to the package. Bearer authorization is limited to OpenAlex hosts for cached content.

## Validation

- Historical scanner tests: 19 passed.
- Primary-document recovery tests: 6 passed.
- Existing scanner-route parity tests: 23 passed.
- Production preflight: 179 passed, 7 skipped, with 5 additional live-content checks reported as non-blocking.
- Routes and extraction were checked with offline mocks. A later real GitHub scan is required to confirm individual external endpoints work and yield publications. An empty scan can still be healthy.

**Known pre-existing broader-test drift (not changed here):** the older worker-ZIP gate test imports `_portable_importer_rules`, which is absent in the uploaded baseline. Another older third-attempt test expects `scan_package_attempts`, but the baseline package code correctly uses validated `recovery_attempts`. This patch deliberately does not change either recovery-contract behavior to satisfy obsolete tests.
