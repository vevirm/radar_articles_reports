# R&I × Geopolitics Radar — V17.5.3 precision + current-gap recall

V17.5.3 keeps the cumulative/incremental source rotations and the strict Sovereignty-Frontier model, while fixing a matcher bug that could create spurious R&I/geopolitics evidence and rebalancing discovery toward under-covered research-talent flows.

## What changed in V17.5.3

### Admission precision

- Plain text is no longer passed through an HTML parser unnecessarily, so abbreviations such as `R&D` remain `R&D` instead of collapsing to `RD`.
- Short/ambiguous admission terms use token boundaries. This prevents `R&D` from matching the letters `rd` inside words such as *regarding*, and prevents `national security` from matching *international security*.
- Generic legal/administrative sanctions no longer count as geopolitical sanctions without strategic context.
- Strand-A relevance notes now expose the actual R&I evidence, strategic evidence and bridge mode instead of a generic “all gates passed” sentence.
- For repositories that have already run V17.5.1, V17.5.3 performs a **one-time corrective precision cleanup** before discovery when `precision_corpus_cleanup_complete` is absent. Saved A/B records that pass the corrected gate are retained immediately; failures get one best-effort DOI/page/PDF refresh before removal. The cleanup writes `precision_corpus_cleanup_complete: true` and is never repeated on normal later scans. All newly discovered material always uses the strict corrected gate.


### One-time corrective audit of the supplied current corpus

The bundled `radar.json` is the user's current post-scan corpus from 22 August 2026: **72 Strand A + 5 Strand B + 101 Strand C = 178 records**. It already has `inherited_corpus_audit_complete: true`, but it does not yet have either `precision_corpus_cleanup_complete` or `precision_signal_cleanup_complete`. Therefore the first V17.5.3 run performs one corrective A/B audit and one corrective Strand-C weak-signal audit before any new discovery.

If a saved title/summary passes the corrected gate, the item is retained immediately. If it fails, the scanner tries to refresh the DOI/landing page/PDF and re-runs the same gate on fuller evidence. Records still failing are removed. Strand C is also rechecked once under the corrected EU-first weak-signal gate. Then the scanner recomputes Frontier coverage from the cleaned corpus and runs normal rotating + sparse-cell discovery.

Once complete, the scanner writes both `precision_corpus_cleanup_complete: true` and `precision_signal_cleanup_complete: true`. Subsequent scheduled runs skip historical cleanup entirely and screen only newly discovered material.

### Research talent / brain drain

Research-talent allocation is now an explicit R&I + geoeconomic evidence family. The gate recognises research/academic brain drain and gain, researcher/scientist mobility, research-talent inflow/outflow, attraction, retention and return mobility when the document is clearly about the research workforce. Generic labour migration or student mobility still does not qualify by itself.

**V17.5.3 correction:** an empty Frontier cell is now searched **inside the live corpus window first** (the preserved corpus floor, e.g. 21 April 2026), rather than being explained away by an older paper. The gap plan also adds a small set of specialist institutional sources without consuming the persistent institution rotation. For `knowledge-D`, this includes European Parliament/EPRS, EU Publications, DG R&I, EURAXESS, CESAER, EUA, Science Europe and ECAS. Gap-relevant URL slugs such as `brain-drain`, `researcher-mobility` and `research-talent` are fetched earlier, but they still face the normal admission gate.

The Frontier evidence extractor also now treats a documented research brain-drain/outflow statement as a structural Frontier condition. When an admitted EU report contains both a generic R&I sentence and a specific researcher brain-drain sentence, the latter is used for `knowledge-D` instead of allowing the generic sentence to misclassify the report as a Knowledge/A opportunity.

Discovery now includes dedicated scholarly queries such as European research brain drain/brain gain, academic research careers, researcher mobility, talent attraction/retention and intra-European mobility. Sparse Frontier cells also feed up to ten targeted queries directly into **OpenAlex and Crossref** each scan, rather than only adding news queries. `knowledge-D` (Brain drain) and `knowledge-C` receive persistent priority when equally sparse.

### Greatest Opportunities & Risks

The `/priorities/` page no longer dumps every cumulative qualifying Frontier signal. It shows **six risks and six opportunities by default**, with at most two items from the same Frontier row before filling remaining slots. This keeps the page decision-oriented while preserving the full cumulative evidence in `radar.json` and the Frontier matrix.

## What remains unchanged

- After the one-time inherited-corpus audit, the Radar is cumulative: retained historical items are not re-audited on later runs, while every new candidate must pass the current gate.
- `radar.json` is still the single source of truth.
- Frontier cells are never padded with fabricated or weak matches.
- OpenAlex, Crossref and institutional sources retain persistent cursors and bounded scan budgets.
- Weak signals remain cumulative after admission.

## The V17.2 fix: persistent source cursors

`radar.json` now stores `scan_state` with independent cursors for:

- OpenAlex scholarly queries;
- Crossref broad scholarly queries;
- Crossref priority-journal/query tasks;
- institutional report sources.

Every scheduled scan resumes from those saved cursors. It does **not** start again at query/source 1.

Per run, the scanner currently processes at most:

- **40 / 155** OpenAlex scholarly queries;
- **35 / 155** Crossref broad queries;
- **45 / 380** Crossref priority-journal tasks;
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

- A **push to `main` immediately starts a scan**. Therefore uploading/committing this repository starts the one-time V17.5.3 corrective cleanup + scan automatically.
- It then runs automatically every **12 hours** at `23 */12 * * *` UTC.
- `workflow_dispatch` remains available for a manual run.
- Bot commits that change only `radar.json` are ignored by the push trigger, preventing an infinite scan loop.

## Safe full-repository upload

This package contains the user's current `radar.json` supplied after the latest scan: **72 Strand A + 5 Strand B + 101 Strand C = 178 records**. It already completed the earlier inherited-corpus migration, so V17.5.3 does not repeat that migration. Instead, because both corrective markers are absent, the first run performs the one-time A/B precision audit plus the one-time EU-first Strand-C cleanup described above, then scans from the cleaned state.

The scanner still contains the `repository_bundle_seed` + Git-history recovery code for future upgrade bundles that use a small seed, but no seed marker is required in this delivery.

## Tests

Run:

```bash
python -m unittest discover -s tests -v
```

The package includes the earlier V12–V17 tests plus V17.2 tests for persistent cursors, non-wrapping batches, per-run caps, known-item loading, separate source-family time slices, and immediate-push/12-hour workflow triggers.

### V17.5.3 corrective current-corpus cleanup

Repositories that already ran V17.5.1 may contain A/B false positives admitted by the older permissive gate. V17.5.3 therefore performs one corrective audit of the **current** A/B corpus before discovery when `precision_corpus_cleanup_complete` is absent. It keeps records that pass the corrected evidence gate, refreshes thin records before deciding, removes records that still fail, writes `precision_corpus_cleanup_complete: true`, recomputes Frontier coverage, and only then runs normal rotating/gap-priority discovery. Later scans never re-audit historical A/B. Strand C is not forced through the A/B gate; it gets its own one-time EU-first weak-signal cleanup and then only new signals are screened.
