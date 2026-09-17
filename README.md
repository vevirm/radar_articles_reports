# Research & Innovation × Geopolitics Radar

Static GitHub Pages reader plus automated research scanners and an offline authoritative Deep Scan verification layer.

## Reader paths

- `/` — simple start page: briefing, Radar, or deeper analysis
- `/read/` — shortest useful briefing
- `/radar/` — searchable current evidence
- `/explore/` — question-led route into Matrix, Trends, phenomena, risks, shocks, history, sources and methods

## Data / trust layers

- `radar.json` — raw scanner evidence plus regenerated derived state; raw A/B/C records are retained for audit/reversibility
- `radar_active.json` — generated active corpus used by reader/analysis; applies authoritative Deep Scan V2 semantics, admission and corrections
- `reader_text.json` — Deep Scan interpretations, including preserved legacy versions
- `admission_state.json` — centralized provisional/keep/review/drop/drop_unverifiable/duplicate state
- `record_corrections.json` — validated metadata/provenance corrections
- `historical/historical.json` — older historical evidence kept separate from current signals

Records without V2 verification remain provisionally active, so the automatic scanner never waits for manual Deep Scan work. Once V2 is imported, V2 is authoritative for the active interpretation/admission and downstream reasoning is rebuilt from the active corpus.

## Scanners and Deep Scan

- `scripts/scan_radar.py` — main automatic scanner/admission logic
- `historical/scan_historical.py` — historical scan
- `.github/workflows/radar-scan.yml` — main automatic scanner workflow
- `.github/workflows/historical-scan.yml` — historical automation
- `scripts/active_corpus.py` — centralized active-corpus policy
- `scripts/rebuild_active_radar.py` — rebuilds active evidence and all derived reasoning from active evidence
- `scripts/prepare_deep_scan_package.py` — prepares the next persistent Deep Scan V2 worker package; no model API and no direct LLM connection
- `scripts/import_deep_scan_results.py` — validates/imports a `deep_scan_results.json` file only after the operator manually uploads it to `deep_scan_inbox/`
- `.github/workflows/deep-scan-prepare-workers.yml` — manually reserve/prepare the next two persistent Deep Scan worker lanes
- `.github/workflows/deep-scan-import.yml` — automatically imports uploaded Deep Scan results and refreshes the worker lanes
- `.github/workflows/radar-v2-migration.yml` — one-time post-install initialization/validation + first V2 package

See **`DEEP_SCAN_SETUP.md`** for the manual repo → operator → external LLM → operator → `deep_scan_inbox/` → import rotation.


## Reader Language (manual, presentation-only)

The optional Reader Language layer keeps public analytical pages clear without giving an LLM access to GitHub. A small local prose checker runs in GitHub Actions and queues only new/changed reader-facing wording that looks heavy, bureaucratic or too close to internal analysis language. Normal publishing never waits for this review.

- `.github/workflows/reader-language.yml` — manually prepares a small Reader Language package; default mode includes only flagged, unreviewed wording
- `scripts/prepare_reader_language_package.py` — deterministic local checker/package builder; no AI API
- `reader_language_inbox/` — operator uploads the returned `reader_language_results.json` here
- `.github/workflows/reader-language-import.yml` — validates the returned file and updates only `reader_language/approved.json`
- `reader_language.js` — presentation-only exact-text overlay with fingerprint safety; stale rewrites stop matching automatically

Main Radar evidence, Earlier Findings evidence, Sources, Stuff/Excel, scores, dates, links, Deep Scan decisions and analytical reasoning are outside this language layer. See **`READER_LANGUAGE_SETUP.md`** for the simple manual rotation.

## Evidence feedback and reader semantics

The existing higher-order inference rules remain the analytical authority for cross-source reasoning. Reader products do not replace or simplify those rules. Risks, opportunities and dynamic shocks now contribute a small, bounded set of balanced discovery questions alongside the existing higher-order missing-link/falsifier queries. Support searches are paired with searches for substitution, resilience, implementation failure or other counter-evidence, and every discovered item still faces the normal scanner/admission/Deep Scan process. The feedback lane does not receive extra query budget or an admission waiver.

On reader synthesis pages, repeated cards are consolidated by interpreted mechanism and exposed asset when that semantic match is clear. The underlying Radar and Excel-style record views remain record-level evidence products, so separate reports are not deduplicated merely because their wording overlaps. Authoritative Deep Scan V2 fields are carried into pathway interpretation and reader evidence links; higher-order findings remain explicitly marked as cross-evidence inference and expose their supporting roles/evidence when opened.

## Tests

The repository includes the existing scanner/reader regression suite plus V2 tests covering active-corpus filtering, raw-evidence immutability, Deep Scan authority, metadata corrections, exhaustive unverifiable handling, duplicate suppression and downstream retrace behavior.

Version: **v25.1.0-evidence-linked-reader**
