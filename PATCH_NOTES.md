# v17.20.53

- Fixes the curated-core regression test so GitHub browser uploads that retain a recognised legacy hidden workflow do not fail before scanning.
- Preferred packaged workflow remains archive-aware; legacy workflow compatibility relies on the scanner's own active+archive preservation invariant and active-core save marker.
- No page/UI logic changes and no scanner discovery/admission changes from v17.20.52.

# v17.20.52

- Fixes the post-scan save failure caused by the curated 200-item core moving accepted records from active Strand A/B into `ab_archive`. The safety model now treats active A + active B + `ab_archive` as one accepted-history preservation domain.
- Adds a scanner-side hard invariant: an ordinary scan refuses to write if any previously accepted A/B identity disappears from both the active core and archive. Active-to-archive rotation is allowed; genuine loss is not.
- Adds compatibility for GitHub browser uploads that retain an older workflow safety block. The scanner exposes the existing cleanup-compatible marker only after the stricter active+archive invariant has passed, so the stale workflow no longer mistakes curation for deletion.
- Previously accepted active records that age out of the visible presentation window are handed to the archive before rebalancing instead of being silently dropped.
- The packaged workflow safety check is archive-aware as well. No scanner discovery/admission thresholds, OpenAlex authentication, 200-item core policy, page structure, page logic, or reader files are changed.

# v17.20.51

- Deployment-residue repair: explicitly ships `tests/test_v172047_fresh_start_and_snowball.py` so GitHub browser uploads overwrite the obsolete v17.20.47 test that was left in the repository and blocking every scan before startup.
- The replacement test checks the current curated-core/incremental architecture rather than the retired destructive corpus-reset implementation.
- Citation snowball seed capacity is restored to 20 DOI-resolvable scholarly seeds per pass now that authenticated OpenAlex is configured.
- No page/UI file or reader logic is changed.

# v17.20.50 — curated 200-item core; preserve history, retire scanner baggage

- Keeps the existing page structure and reader logic byte-for-byte unchanged. This release changes scanner state, discovery/curation logic and `radar.json` data only.
- Re-ranks the accepted Strand A+B history into a compact 200-item active core (190 A / 10 B when available). The packaged reset contains 200 active records and 424 archived accepted records.
- Nothing accepted is deleted: displaced A/B records move to `ab_archive`, keep their DOI/title/link identities, remain part of duplicate detection, and are reconsidered whenever the active core is rebalanced. An older important work can therefore return to the active 200.
- Git-history recovery is archive-aware. A whole-repository browser upload cannot resurrect the pre-reset 624-row active corpus; recovered accepted records that are not in the current active core are preserved in the archive instead.
- The active-core ranking strongly favours peer-reviewed papers, working/research papers and substantive formal/institutional reports over routine calls, appointments, registrations, event notices and grant-competition news. It does not change the underlying admission gate or manufacture a daily quota.
- Marks the legacy source-expansion/backfill campaign complete and clears stale family-failure/backfill flags without resetting useful query, journal-depth, source and citation cursors. Normal discovery therefore starts in the v17.20.48/49 incremental steady state rather than reopening old migration work.
- Keeps authenticated OpenAlex discovery, DOI enrichment, rotating priority-journal depth and DOI-first citation snowballing from v17.20.48/49. The existing `OPENALEX_API_KEY` repository secret is reused automatically.
- Adds a regression contract for the 200-item core, archive-aware dedupe, archive-aware Git recovery and no four-month source-expansion bootstrap.

# v17.20.49 — compatibility repair for retained full-suite preflight

- Preserves the v17.20.48 incremental scholarly engine and corpus unchanged.
- Restores the legacy OpenAlex explicit deep-lane contract: `explore`, `gap`, `finding-context`, `curator-seed`. Evidence-first queries remain first-class page-1 discovery; deeper evidence exploration is handled by rotating journal-depth and citation-adjacency lanes instead of silently expanding every evidence query.
- Restores `crossref_source_first_depth_pages_max` to 3. Because v17.20.48 changed source-first Crossref filtering to the incremental `from_date`, this does **not** restore the old four-month sweep; it only allows depth within the current incremental overlap when a high-output journal fills page 1.
- No admission thresholds, source lists, OpenAlex authentication, saved corpus, page structure, or dedupe identities changed.

# v17.20.48 — retire migration load; make scholarly discovery truly incremental

- Preserves the complete accepted corpus, reader pages, history, source lists, Strand A/B/C structure and deduplication identities. This release changes scanner control logic, not the retained evidence base.
- Ends the permanent four-month source-expansion loop. A stale top-level completion marker is migrated safely when the current target has already completed source-family rotations; future source-list changes use bounded rotating refresh instead of resetting every crawler family.
- Admission-profile changes no longer zero scholarly/institutional cursors or reopen four-month backfills. The old 24-source A-recall migration loop is retired from normal scans; accepted older works remain untouched.
- Normal source-first journal checks now use the incremental overlap window. A separate small rotating depth lane handles delayed indexing for Research Policy, Technological Forecasting and Social Change, Futures, Technology in Society and related R&I journals.
- Citation snowballing now prioritises DOI-resolvable scholarly seeds and persists a seed cursor, instead of filling the top-20 pool with Tier-1 institutional notices that OpenAlex cannot use effectively.
- Low primary yield no longer disables researcher/citation adjacency. With an authenticated OpenAlex key, bounded high-information scholarly adjacency runs before generic rescue rotation.
- Cuts the protected low-yield reserve from 600s to 240s and bounds generic rescue waves, so productive OpenAlex/Crossref/institutional discovery is not truncated merely to save 40% of the run for broad fallback queries.
- Main workflow is a real four-hour cycle with one shared Main/Historical concurrency group and no external rescue dispatch; Historical has no push trigger. Scheduled scans run a compact scanner-critical regression set rather than the slow full repository suite.
- Adds v17.20.48 regression coverage for stale-backfill migration, no global reset on profile/source changes, incremental journal windows, rotating DOI snowball seeds, bounded time allocation and the fixed workflow contract.

# v17.20.47 — research-evidence / long-form balance

- Adds an evidence-first OpenAlex/Crossref query lane on every scan for empirical European R&I research: collaboration, careers/talent, research performance, infrastructure, technology transfer, R&D intensity, innovation-system performance and evaluation.
- Gives a recurring priority slice to long-form publication sources (JRC Publications, JRC, EU Publications Office, European Parliament/EPRS, OECD, Bruegel, CEPS, CWTS, Rathenau and Science Europe) without bypassing the ordinary admission gate.
- Adds a bounded `research-evidence` Strand-A route for Tier-1/2 completed scholarly/analytical evidence. It still requires direct European/EU scope, central R&I aboutness, empirical/analytical evidence and a recognisable R&I-system mechanism; generic regional firm studies and project recaps remain out.
- Tightens the high-confidence strategic-technology fallback so a technology name such as AI alone cannot turn a local hospital/school/application study into EU R&I-system evidence.
- Ranking now prefers completed peer-reviewed papers, working papers and substantive formal/institutional reports over routine funding/current-event notices when candidates compete for the limited NEW slots.
- Reserves up to three of the five NEW A/B slots for completed evidence products when at least that many qualifying evidence products exist; remaining slots retain ordinary strategic ranking.
- No page structure, corpus history, deduplication identifiers or existing reader products were changed.
# v17.20.46 — separate source quality from metadata availability and admission yield

- No configured scholarly source is pruned, demoted or disabled because it admitted few or zero items. `source_yield_pruning_enabled` is explicitly false; source-health observations are diagnostic only.
- Crossref source-first batches now measure raw abstract coverage separately from admission. `source_metadata_health` reports records seen, Crossref abstracts present/missing, known/duplicate skips, enrichment attempts/recoveries, judgeable records after enrichment and emitted gate candidates.
- When a configured journal batch is empirically metadata-sparse (enough records but very low Crossref abstract coverage), authenticated OpenAlex DOI lookups recover a bounded rotating sample of abstracts before the ordinary A/B gate. The persisted rotation cursor prevents every scan from enriching the same first records.
- DOI landing-page recovery remains a bounded fallback. Neither OpenAlex nor publisher enrichment changes source tiers or admission thresholds; recovered text must pass the same language, EU, R&I and A/B tests.
- Adds a regression reproducing the concrete failure mode: eight recent Research Policy records with zero Crossref abstracts are recognised as metadata-sparse, enriched through OpenAlex, and judged without treating the source as low quality. The same invariant covers Technological Forecasting and Social Change, Futures, Technology in Society and other configured journals when their Crossref batches are similarly sparse.
- Makes the release-marker regression future-proof: VERSION, admission profile and patch-note marker must agree, instead of hard-coding the previous release number and breaking every legitimate version bump.

# v17.20.45 — close the Horizon governance and browser-upload compatibility gap

- Formal Horizon Europe association Joint Committee / Joint R&I Committee notices are no longer misclassified as routine event recaps when the retrieved evidence describes programme governance, association, research-security, mobility or R&I-cooperation substance.
- The final shared A/B worthiness guard now uses the same governance-event exception as `eu_ri_centrality()`, eliminating the second-stage contradiction where an item could pass centrality and then be discarded later.
- The live `tests/test_v172041_recall_guard.py` contract is included in the package so browser uploads cannot leave an untested stale file behind.
- Routine workshops/conferences remain excluded.

# v17.20.44 — make scanner startup independent of hidden workflow deployment

- Fixes the repeated pre-scan failure seen on GitHub when browser whole-repo uploads update visible code/tests but leave `.github/workflows/*.yml` at the older revision.
- `scripts/check_workflow_contract.py` is now **warning-only by default**. A stale workflow still prints every mismatch, but exits 0 so `python -m unittest discover ...` cannot kill the radar before `Run radar scan`. `--strict` remains available for release/package verification.
- Keeps the visible runtime compatibility layer already present in v17.20.43: legacy Main hourly + six-hour due-gate scheduling is slot-aligned by scanner state, legacy Historical push runs are deployment-only, stale Historical minimum-runtime environment is ignored, and Main/Historical use the runtime peer guard when the shared YAML concurrency group is unavailable.
- The preferred corrected Main/Historical YAML is still included in the ZIP, but scanner operation no longer depends on GitHub successfully replacing those hidden files.
- Keeps all v17.20.42/43 admission fixes and authenticated OpenAlex support via `OPENALEX_API_KEY`.
- No corpus reset, deletion, recall-profile bump, or source-expansion reset.

# v17.20.43 — package the workflow repair that v17.20.42 claimed but did not actually ship

- Fixes the v17.20.42 packaging error: that archive included tests expecting the restored workflow contract while still carrying legacy workflow YAML. GitHub therefore failed the pre-scan tests and **never reached `Run radar scan`**.
- The shipped Main workflow is now physically present in the package with the fixed four-hour cron `17 0,4,8,12,16,20 * * *`, no legacy six-hour age gate, shared `ri-research-scanners` concurrency, a 36-minute scan job envelope, and scanner-critical preflight tests.
- The shipped Historical workflow is physically present with daily `53 6 * * *`, no push trigger, the same shared scanner lock, and `HISTORICAL_MIN_RUNTIME_SECONDS: '0'`.
- Keeps all v17.20.42 admission fixes: R&I vocabulary alignment, `deep tech` centrality, substantive Horizon Europe Joint Committee governance notices, and source-expansion progress preservation.
- Keeps authenticated OpenAlex support through the repository secret `OPENALEX_API_KEY`. The failed v17.20.42 run never reached the scanner step, so it never exercised the key.
- No corpus deletion, quality migration, or source-expansion reset is introduced by this packaging repair.

# v17.20.42 — repair admission vocabulary, governance notices, backfill progress and shipped workflows

- Fixed the R&I vocabulary drift between `_ri_hits()` and the mandatory `_central_ri_hits()` gate. Every direct `A_RI_CORE` term is now centrality-visible, and every strategic-technology mechanism accepted by `_ri_hits()` is also available to `_central_ri_hits()`. This removes the contradiction where the scanner recorded valid `ri_evidence` and then rejected the same candidate as `ri_not_central`.
- `deep tech` is therefore centrality-visible. Canonical EIC material such as the EIC Tech Report and EIC Impact Report no longer fails solely because `deep tech` existed in `A_MAJOR_RI_SYSTEM`/`A_RI_CORE` but not in `A_CENTRAL_RI_TERMS`.
- Narrowed the institutional event-recap guard so Horizon Europe Joint Committee / Joint Research and Innovation Committee notices with substantive programme-governance evidence (agreement implementation, reciprocal access, financial contribution, work programmes, governance structures, etc.) are treated as primary Strand-A evidence. Routine workshops/conferences/visits still fail.
- Added positive recall regression coverage for EIC deep-tech reports, Horizon Europe association Joint Committee governance, vocabulary alignment, and backfill progress, alongside the existing false-positive guards.
- Fixed the source-expansion state machine: once a source-expansion target has been opened in `scan_state`, incomplete per-family backfill flags are no longer reset to `false` on every run merely because the top-level completion marker is still old. Long rotations can now actually finish.
- Restored the workflow contract that earlier release notes claimed but the packaged YAML did not contain: Main runs at `00:17/04:17/08:17/12:17/16:17/20:17 UTC`, Main and Historical share `ri-research-scanners`, Historical runs at `06:53 UTC` with no push trigger, Historical minimum runtime is `0`, the legacy six-hour age gate is removed from the shipped Main workflow, and low-yield continuation stays inside the scanners instead of dispatching a second workflow run.
- Main scheduled preflight is scanner-critical rather than the full reader/release test suite; Main job envelope is 36 minutes and Pages publish is 6 minutes.
- The OpenAlex global keyless request cap from v17.20.41 remains unchanged. A repository `OPENALEX_API_KEY` secret is still strongly recommended for normal scholarly capacity.
- No corpus rows are deleted and no recall/quality migration marker is bumped by this release.

# v17.20.41 — restore useful EU-R&I recall + enforce the keyless OpenAlex cap globally

- Fixes the v17.20.25–40 zero/one-item regression: strategic/geopolitical context remains a preferred Strand-A route, but it is no longer a universal final veto. A bounded Tier-1/2 major EU-R&I-system route restores strong Horizon Europe, research-infrastructure, research-capacity and strategic-technology evidence when the title itself establishes European or R&I centrality.
- Keeps the v17.20.39 precision guard: the known `Regional knowledge base and firm efficiency...` false positive and similar non-major/local/consumer material do not qualify through the restored route.
- Fixes v17.20.40 keyless OpenAlex protection at the request layer. All OpenAlex callers now share one per-scan anonymous request budget, so curator/author/fallback calls cannot silently turn a planned six-query scan into 40+ requests and an HTTP 429.
- A configured `OPENALEX_API_KEY` still removes the local anonymous cap and enables the full OpenAlex discovery/citation lanes.
- No corpus rows are deleted by this release.

# v17.20.39 — novelty-first low-yield repair + hard strategic precision

- Fixed the live false positive `Regional knowledge base and firm efficiency: Evidence from start-ups and fast-growing medium-sized firms`. Ordinary phrases such as `access to`, `dependence`, `resilience` and generic `technological capabilities` can no longer combine to manufacture a geopolitical/strategic mechanism.
- The triangulated strategic-context route keeps genuinely relational mechanisms such as foreign/non-EU suppliers, chokepoints, strategic dependencies, rule power, brain drain/outflow and other externally positioned R&I effects.
- Removed the live false-positive paper from the packaged Strand-A corpus and added it to the exact retired-title guard so upload-state recovery cannot resurrect it.
- Crossref ordinary broad discovery now uses bibliographic retrieval, not title-only retrieval. A paper can therefore be discovered when its EU-R&I/geopolitical mechanism is mainly in the abstract/metadata; the strict final subject and quality gate is unchanged.
- The low-yield Strand-A rescue bank no longer spends scarce slots on Strand-B foresight-method queries. Strand B keeps its own recurring method lane.
- Researcher adjacency and citation snowballing now run before the extra low-yield broad/depth waves. Live runs had been exhausting OpenAlex with 18 extra queries and only then attempting citation discovery, often after HTTP 429 made the smarter lane unusable.
- Restored the intended four-hour Main workflow and separated Historical workflow in the release package, while retaining the stale-workflow runtime compatibility guard for browser uploads.
- Added regression tests for the live false-positive mechanism, a genuine external-dependency counterexample, low-yield Strand-A query allocation, adjacency ordering, and broad Crossref bibliographic retrieval.
- The ~5 Strand-A items per cycle remains a search-depth sanity target, never an admission quota. Relevance still requires central EU/European R&I plus a source-supported geopolitical/strategic mechanism.

# v17.20.38 — signal integrity + recall plumbing cleanup

- Strand-C watch-theme matching now uses real word/phrase boundaries. This fixes the live `engaging` -> `aging` substring bug that misclassified an ESPI lunar-governance tabletop as demographic/research-workforce evidence.
- New and saved weak signals now need a source-backed R&I/strategic mechanism in their own headline/description. A Strand-A anchor may explain relevance but cannot manufacture the EU-R&I connection from unrelated source text.
- Removed the live lunar-governance false signal and retired that exact headline so Git-history recovery cannot restore it. The one-time C quality migration is reopened for the new relational gate.
- Crossref low-yield/depth and 4–6 month recovery now use bibliographic search rather than title-only search. Normal broad discovery remains title-first for precision; only the recall lanes widen retrieval, and all results still face the unchanged strict final EU R&I + geopolitical gate.
- Institutional date recovery now accepts explicit `/YYYY/MM/` publication paths when a CMS exposes no date metadata, labelled as month-level evidence instead of silently discarding the page.
- When an institutional wrapper page borrows a linked PDF as its evidence body, the PDF's own visible/path publication date now outranks the wrapper date. This fixes the live ALLEA case where a June-2026 wrapper laundered a February-2025 PDF into the current Main corpus.
- Removed that misdated ALLEA wrapper record from the packaged Main corpus and retired the exact title from automatic Main restoration. The underlying 2025 evidence belongs in Historical if it qualifies there.
- Added regression tests for the lunar substring bug, source-backed C bridge, month-only institutional dates, linked-PDF date precedence, and Crossref title-first vs bibliographic low-yield retrieval.
- Scanner regression tests no longer make the hidden workflow YAML a hard runtime dependency: the shipped workflow is still checked separately by `scripts/check_workflow_contract.py`, while stale browser-upload workflows remain compatible instead of blocking discovery before Python starts.
- The final Strand-A subject rule is unchanged: central EU/European R&I plus a source-supported geopolitical/strategic mechanism. The ~5-per-cycle figure remains a search-depth sanity target, never a quota.

# v17.20.37 — plumbing cleanup: stop losing good evidence after discovery

- Manual/curator scholarly references, especially DOI links, now use scholarly resolution (Crossref/OpenAlex/publisher metadata) instead of being misrouted through the institutional HTML parser.
- Curator candidates in the 4–6 month recovery window now use the same high-quality journal rule as the repaired fallback, so Tier-1/Tier-2 peer-reviewed articles are no longer discarded for failing an institution-only authority check.
- Curator rejections are versioned. Rejections made under older broken source/gate plumbing are automatically re-tested once under the current profile, then become stable again.
- Journal metadata variants such as `Survival: August-September 2026` inherit the configured journal tier, and the source-first Crossref lane uses the same safe matcher. Unsafe generic prefix matching such as `Science` -> `Science Advances` remains forbidden.
- Direct institutional PDF URLs discovered in sitemaps or publication hubs now have a dedicated PDF parser and pass through the ordinary institutional A/B gate instead of dying at the HTML content-type check.
- Institutional seen-cache fingerprints are now written only after a document was successfully fetched, genuinely dated and read. Transient fetch/date-extraction failures remain retryable instead of being permanently skipped.
- A known institutional URL can be revisited when its sitemap `lastmod` changes; the old known-URL shortcut no longer blocks that changed-fingerprint path before parsing.
- Institutional reports discovered through bibliographic APIs may retain a DOI link when the scanner explicitly records `bibliographic_doi` source integrity. Unmarked institutional-title/DOI chimeras still fail closed.
- Duplicate identity no longer assumes titles are globally unique. Same title + different DOI is allowed; same DOI is duplicate; DOI-less publisher representations of an already saved DOI record are still suppressed.
- The Main low-yield sanity target now counts genuinely new Strand-A evidence only. Strand-B foresight-method papers cannot make the scanner stop searching for EU R&I-geopolitics evidence.
- Added regression tests for each of the above cases. The strict final subject rule is unchanged: central EU/European R&I plus a source-supported geopolitical/strategic mechanism.

# v17.20.36 — repair rotation progress, rate-limit recovery and anti-low-hanging depth

- Fixed a fundamental rotation bug: OpenAlex/Crossref queries and source-first journals now advance their persistent cursors **only after a successful HTTP 200 response**. HTTP 429/failed attempts no longer consume unsearched rotation slots.
- HTTP 429 is now treated as a temporary throttle, not a permanent source-family failure. The protected low-yield phase may retry the scholarly family after cooldown; true 401/403/409/fatal endpoint failures still disable it.
- Low-yield continuation is now a **depth rotation** (page 2/3/4...) over persisted query state instead of another page-1 pass over easy records. Up to three bounded depth waves are available when the genuinely-new A/B count remains below the five-item search-depth target.
- Crossref broad discovery now uses one page-1 request per ordinary query instead of relevance + newest for every query. OpenAlex/newest/source-first lanes still provide recency coverage, while Crossref capacity is preserved for more distinct and deeper searches.
- Crossref stops the current collector promptly after a sustained 429 and leaves all not-yet-successful tasks pending, rather than burning the remaining stage on repeated throttled requests.
- Rebalanced primary public-API load (72 OpenAlex / 80 Crossref broad; bounded 20 source-first and 20 priority Crossref tasks) and reduced low-yield-zero metadata enrichment work so protected depth/search capacity survives to the controller.
- The 4–6 month low-yield fallback can now retain genuinely high-quality Tier-1/Tier-2 peer-reviewed journal evidence, not only a tiny official-institution allowlist. The ordinary EU R&I + geopolitical relevance gate is unchanged.
- Low-yield rescue prioritises curator-derived and live-finding query neighbourhoods before the generic bank.
- Removed the resurrected WEFE and dramatherapy false positives from the packaged corpus and added them to the permanent retired-title guard so Git-history recovery cannot bring them back.
- Restored the intended shipped workflows: Main runs on upload/manual + fixed four-hour schedule with one internal low-yield cycle; Historical remains daily and separate under the shared scanner lock. Legacy hidden-workflow compatibility remains in visible code.

# v17.20.35 — isolate upload-state recovery from regression tests

- Fixes the v17.20.34 GitHub upload failure where `Run scanner regression tests` saw the repository push event and the new pre-upload Git-history recovery fired inside ordinary unit-test calls to `load_previous()`. That contaminated isolated test fixtures with hundreds of live-corpus rows and stopped the scan before discovery began.
- Git-history recovery is now an explicit production capability: `load_previous()` is local-only by default, while the real Main scanner entry point calls `load_previous(allow_git_recovery=True)`. Regression tests and temporary fixtures therefore cannot accidentally reach the repository corpus merely because GitHub set `GITHUB_EVENT_NAME=push`.
- The dedicated whole-repository-upload regression still exercises the recovery path explicitly and verifies that a stale bundled corpus cannot roll back newer corpus size or OpenAlex/Crossref cursor state.
- No discovery allocation, relevance gate, corpus record, or saved rotation cursor is changed by this release. All v17.20.34 low-yield method switching and monotonic upload-state behavior remain active in real scanner runs.

# v17.20.34 — monotonic upload state + low-yield method switching

- Fixes a fundamental whole-repository-upload bug visible in the live scan history: repeated upgrade uploads could replace a newer live `radar.json` with an older bundled snapshot, shrinking Strand A (for example 590 → 587) and rolling discovery cursors backward. On `push`, Main now inspects the pre-upload Git history, unions any newer/larger cumulative corpus, and keeps whichever scan-state checkpoint is genuinely newer. A ZIP upload therefore cannot send query/source rotation backwards.
- Low-yield discovery no longer protects generic broad-query capacity by suppressing every high-information lane. Once the protected continuation phase begins, it first retries curator/manual exact evidence, then performs fresh broad/source rotation, then switches method to Crossref researcher adjacency plus OpenAlex citation snowballing if yield is still low.
- Generic continuation waves are reduced from three to two; the third repeated wave is replaced by adjacency discovery. The 4–6 month Highest-merit fallback is widened modestly after these current-window methods have been tried.
- The strict final subject gate is unchanged: central EU/European R&I plus a source-supported geopolitical/strategic mechanism. No quota or lower-quality admission route was added.
- The known poverty/social-exclusion false positive is also blocked from resurrection when older Git-history snapshots are merged.

# v17.20.33 — low-yield scholarly continuation repair

- Fixes the post-v17.20.32 one-item run where all three protected continuation waves became institution-only. Auxiliary priority-researcher HTTP 429 warnings no longer mark the entire OpenAlex/Crossref family unavailable.
- When the primary pass is below the five-item search-depth sanity target, exact-author, foresight-author, citation-snowball and weak-signal scholarly follow-ups are deferred so they cannot consume or rate-limit the broad-query capacity reserved for continuation.
- The strict final admission rule is unchanged: evidence still needs central EU/European R&I plus a source-supported geopolitical/strategic mechanism. The target changes search depth only and never lowers quality.
- Current corpus and rotation state are preserved; this release changes discovery allocation, not retained evidence.

# v17.20.32 — browser upload again triggers a real Main Radar scan

This release corrects v17.20.31, which wrongly made repository uploads deployment-only.
The user maintains the project by replacing the whole repository through GitHub's browser
uploader and expects that upload to run the Main Radar immediately. That behavior is restored.

- A push/upload to `main` is again a **real Main Radar discovery cycle**.
- The proper Main workflow listens to `push`, the fixed four-hour schedule, and manual dispatch.
- `radar.json` is excluded from the push trigger, so the scanner's own result commit cannot
  recursively start another Main scan.
- Historical remains deployment-only on repository push and continues to scan on its daily
  schedule/manual dispatch. A stale Historical push workflow is explicitly non-blocking, so it cannot
  steal the runtime slot from the real Main upload scan.
- The visible role-aware compatibility guard preserves the same behavior even when GitHub's
  browser uploader leaves the old hidden workflow YAML in place: stale Main push runs scan;
  stale Historical push runs exit before source requests.
- All v17.20.30/31 discovery improvements remain intact: breadth-first scholarly rotation,
  protected low-yield continuation time, strict EU R&I + geopolitical admission, and persisted
  rotation cursors.

# v17.20.31 — repository uploads are not radar scans

This release fixes the misleading short “Add files via upload” scanner runs. A repository
push is now deployment-only at the scanner-code level, so even a stale hidden GitHub
workflow cannot make a browser upload move discovery cursors/timestamps, compete for the
scanner runtime slot, or masquerade as a completed evidence scan.

- Main discovery runs only on the fixed four-hour schedule or explicit manual dispatch.
- Historical discovery runs only on its daily schedule or explicit manual dispatch.
- The shipped workflows no longer contain push triggers. GitHub Pages continues to deploy
  branch changes independently.
- A stale legacy workflow may still appear in Actions after browser uploads, but when it
  invokes either scanner on `push`, visible scanner code exits before any source request and
  without changing radar/historical state.
- Scheduled/manual scans retain the v17.20.30 breadth-first scholarly allocation, protected
  low-yield continuation reserve, strict EU R&I + geopolitical relevance gate, and all
  persistent rotation cursors.

# v17.20.30 — breadth-first scholarly rotation under real API limits

- Diagnosed the latest saved zero-yield run from the downloaded live repository: the v17.20.29 low-yield reserve worked and ran three fresh continuation waves, but Crossref executed 41 source-first journals and 32 journal/query tasks before executing **0 of 110 broad rotating queries**; OpenAlex reached 54/100 queries before keyless HTTP 429.
- Crossref work is now interleaved instead of source-first → priority → broad. Broad rotating queries receive two slots for every source-first and priority slot, so a partial/time-limited stage still explores fresh query territory instead of spending its whole budget on the easiest journal feeds.
- Ordinary Crossref query tasks no longer spend a third request on deep result pages. Deep-page rotation is preserved explicitly for exploration, Matrix-gap, finding-context and curator-seed lanes; source-first journals keep their own persisted depth rotation.
- Ordinary OpenAlex queries are now breadth-first (newest page first). Persisted deep pages remain active for exploration/gap/context/curator lanes, reducing request consumption so more distinct rotating queries can execute before the anonymous endpoint rate-limits.
- The ~5-good-items-per-cycle value remains a search-depth sanity target only. The hard EU/European R&I + source-supported geopolitical/strategic gate is unchanged.
- Legacy hidden-workflow compatibility remains active because GitHub browser bulk uploads can leave `.github/workflows` at an older revision. The old hourly workflow may show harmless no-op runs between real four-hour slots; visible scanner state aligns its six-hour due gate to the intended four-hour slots and disables its external rescue dispatch.
- Historical compatibility also ignores the stale hidden workflow's old 600-second minimum-runtime environment value; current Historical rotation remains target-driven even when that YAML cannot be replaced by the browser uploader.

# R&I Radar v17.20.29

## Protected low-yield continuation time

- Fixes the remaining v17.20.28 failure observed in the live 5 September run: the controller correctly counted **0 genuinely new A/B items**, but ordinary discovery had already consumed about 22m55s of the 24-minute scanner budget, leaving only about 65 seconds; the continuation therefore could not legally start.
- A low-yield Main cycle now protects **600 seconds (10 minutes)** of the existing 24-minute scanner budget for fresh continuation. Ordinary pre-continuation stages see the reduced working budget and cannot consume that protected tail.
- If the primary pass already reaches the **5-item search-depth sanity target**, the reserve is released immediately so curator/author/snowball and other ordinary follow-up lanes may use the remaining time. The five-item target remains a search-depth trigger, never an admission quota.
- Fresh continuation waves are shortened to a bounded 150-second slice with a 90-second start threshold, allowing the same run to make multiple genuinely fresh rotations instead of arriving at the controller too late. The extended highest-merit fallback is likewise bounded to 120 seconds.
- Adds explicit run diagnostics for `low_yield_reserved_seconds` and `low_yield_actual_seconds_remaining_at_controller`, so future zero-yield runs show whether the controller actually had time to act.
- Admission remains unchanged: only high-quality, highly relevant European/EU R&I evidence with a source-supported geopolitical/strategic mechanism can enter Strand A. No quality threshold was lowered.
- Preserves the uploaded v17.20.28 corpus and persisted scan cursors as the authoritative base.

# R&I Radar v17.20.28

## Low-yield continuation correctness

- Fixes the controller bug where pre-final A/B candidates could satisfy the five-item search-depth target even though the published scan retained zero genuinely new items.
- Low-yield counts now apply the same final shared worthiness guard and treat DOI/title representation changes as already known.
- Adds an institutional continuation lane to every low-yield wave. If OpenAlex and Crossref are both rate-limited, the same four-hour cycle now keeps rotating through previously unexecuted institutional/report sources instead of stopping.
- Keeps the five-item figure as a search-depth sanity target only. Admission quality is unchanged.
- Preserves the uploaded v17.20.27 corpus and scan state as the authoritative base.

# R&I Radar v17.20.27
## Browser-upload compatibility: stale hidden workflow can no longer block Main
- GitHub's browser bulk upload can update visible scanner/test files while leaving `.github/workflows/*.yml` at an older revision. The observed failure was exactly this: the new regression suite ran under the old hourly/six-hour-gate workflow and stopped before `scan_radar.py` executed.
- Main regression tests now accept either the preferred fixed four-hour workflow or the explicitly recognized legacy hourly/six-hour workflow **only when** the scanner compatibility layer is present.
- Under that legacy workflow, `scan_radar.py` already aligns `scan_state.last_completed_at` so the old six-hour due gate becomes due at the next real four-hour slot, and it writes `full_rescue_run_enabled=false`, so the old separate GitHub rescue step computes `dispatch=false`.
- The preferred shipped workflow is unchanged: 00:17/04:17/08:17/12:17/16:17/20:17 UTC, one logical cycle, low-yield continuation inside the scanner, shared Main/Historical lock.
- This release is deliberately deployment-robust: uploading the complete repository through the browser should no longer produce a red Main job merely because the hidden workflow YAML was not overwritten.

# v17.20.26 — Historical coverage rotation and deeper backfill

- Reworked the Historical scanner from broad whole-period keyword rotation into persistent **coverage rotation** across topic families, elite source batches, two-year publication bands, API result depth and direct-source depth.
- Added a daily under-coverage lane that searches the thinnest retained **topic × time-band** cells while rotating within the gap pool, so a permanently empty cell cannot monopolise future scans.
- Added rotating known-good-author backtracking through Crossref to find earlier work by researchers already present in high-quality admitted evidence.
- Curated workbook title seeds are now searched in their likely publication year where available instead of spending the current time-band budget on a seed known to belong elsewhere.
- Fixed direct institutional/PDF date fallback that previously recognised only 2023–2025-style dates; fallback recovery now covers the full eligible historical window from 2015 to the rolling cutoff.
- Institutional direct-source discovery now rotates through deeper ranked link pages rather than repeatedly reading only the first block of adapter/sitemap results.
- Historical low-yield continuation is fully self-contained in the same daily GitHub job. The old separately dispatched Historical rescue workflow is removed. The 8-item target remains a search-depth sanity target, never an admission quota.
- Tightened Historical precision: generic EU research-system capacity language no longer substitutes for geopolitical/strategic context. New automated additions must contain a source-supported strategic/geopolitical mechanism.
- Historical scan runtime is target-driven rather than padded to a minimum wall-clock duration; the GitHub job still has the same 30-minute hard ceiling and 17.5-minute scanner budget.
- Main Radar v17.20.25 discovery/admission, four-hour schedule, shock toy and retained live corpus are otherwise unchanged.

# v17.20.25 — one-cycle rotation + hard EU R&I geopolitics precision

- Treats ~5 high-quality A/B additions per four-hour scan as a discovery-depth sanity target, never an admission quota.
- Keeps low-yield rescue inside the same scanner process with up to three fresh, unexecuted rotating query waves; no second GitHub rescue run is launched.
- Stops re-reading every Crossref journal from page 1 on every run. Source-first journal attention now rotates in bounded batches while persisted depth pages continue to advance.
- Institutional source attention also rotates in substantial batches, leaving unused trusted sources available for same-run source-failure reallocation.
- Strand A now has a hard final geopolitical/strategic-context requirement in addition to central EU/European R&I and substantive R&I aboutness. Generic Europe/R&I material cannot be admitted merely because it mentions capability, access, cost, coordination or dependence.
- Main workflow is a single fixed four-hour schedule with the shared Main/Historical scanner lock. Historical remains separate.

# v17.20.24

- Added an experimental **one-shot shock hypothesis** button at the top of External Shocks. It is reader-side only: nothing is written to `radar.json`, scanner state, local storage or session storage, and pressing again replaces the previous result.
- The constructor follows the curator method rather than ranking shocks: it starts from a random low-score outside event, uses a 93–100 EU source only to define the European commitment/capability, and uses a 75–92 peer-reviewed/policy source for the explanatory mechanism. The Stuff/source-merit score assigns source roles only.
- Added conservative structural routes currently supported by the corpus: research-information/indicator dependence, foreign restrictions reaching research organisations, lab-specific substitute blind spots, partner-country funding shocks, external talent pull, and quantum subsidy/supplier competition. Internal route names are never shown to readers.
- Every displayed hypothesis uses three different sources, keeps the event in the low-score source, limits the path to four steps, rejects the familiar framing vocabulary in the shock sentence, checks that no retained row substantially states the constructed sentence, and always labels the result as constructed/not admitted/not retained.
- Duplicate titles count once and repeated extracted core-message text is ignored defensively. Weak/current-event sources can carry the event but cannot supply the explanation. After at most five failed constructions the toy shows the failed check instead of padding.
- The existing realised, emergent, direct and reasoned shock machinery is unchanged. Main Radar discovery/admission and all rotation cursors are unchanged.

# v17.20.23

- Main Radar recall recovery remains narrowly focused on **European/EU research & innovation in geopolitical context**; no shock-generator/toy feature was added.
- Reworked the soft EU-R&I centrality recovery so Europe/EU scope, substantive R&I evidence and the geopolitical mechanism may be supported in different sentences or report sections. The previous near-adjacency behaviour was a major false-negative source.
- The new document-level bridge still fails generic EU innovation/administrative material: it requires explicit or conservatively implied geopolitical/geoeconomic, dependency, security, rules-power, international-position, talent or capability mechanisms.
- Trusted Tier-3 peer-reviewed metadata can now survive a missing abstract only when the **title itself** establishes European scope + substantive R&I + geopolitical/strategic context. Generic title-only Tier-3 material remains deferred/rejected.
- Added semantic institutional publication-date recovery for common CMS markup (`publication-date`, published/issued/release fields and publication-shaped application-state JSON), reducing false `no date` rejection without using arbitrary body dates or sitemap modification time as publication evidence.
- When OpenAlex is rate-limited/unavailable, the replacement lane is now much larger and still rotates: up to 32 additional Crossref queries, 20 trusted journals and 24 institutional sources rather than a token fallback. The OpenAlex cursor is preserved for the next run.
- Curator-known examples receive more recurring discovery attention: the rotating adjacent-query bank is expanded and 12 seeds are used per scan; exact manual-recovery throughput rises to 25 URLs per scan. These routes never bypass admission.
- Crossref missing-abstract recovery is enlarged, including more recoveries per task.
- Bumped only the source-expansion/backfill marker and the targeted A-recall version. The persistent main OpenAlex/Crossref/query rotation cursors are **not reset**.
- Corrected the shipped GitHub Actions schedule to six real Main scans per day (every four hours) and restored the shared Main/Historical concurrency lock; the stale six-hour due gate is removed.
- Added regression coverage for document-level EU-R&I-geopolitical evidence separation, Tier-3 title-only safeguards, CMS date recovery, stronger failure reallocation, curator rotation, and rotation-preserving backfill.

# v17.20.22

- Fixed low recall in the Main Radar while preserving its core focus: **European/EU research & innovation in geopolitical context**.
- Added a conservative centrality-recall bridge for sources where EU scope, R&I substance and geopolitical mechanisms are clearly source-backed but appear in separated sentences/sections. Generic EU R&I policy material does not receive this rescue.
- Curator-supplied known-good examples now seed a small rotating adjacent-discovery lane instead of being used only as exact-item regression/recovery checks. Curator examples never bypass admission.
- Crossref source-first journal discovery now checks the newest page plus one persisted deeper page for high-output journals, preventing relevant four-month-window articles from being permanently hidden behind the newest 100 records.
- Increased institutional page depth from 10 to 14 pages per domain, expanded adapter coverage to all configured adapters per run, and increased the global institutional page budget while keeping breadth-first allocation.
- Increased ranked Crossref missing-abstract recovery so promising EU-R&I-geopolitics records are less likely to be discarded only because Crossref omitted an abstract.
- Bumped the discovery expansion marker so the new recall logic gets a fresh rolling-window catch-up rather than relying only on old scan-state assumptions.
- Added regression tests proving that separated EU/R&I evidence is rescued only when genuine geopolitical/strategic context is present.

# v17.20.21

- Prevent stale hidden GitHub workflow YAML from blocking the main scanner regression step.
- Scanner-serialization tests now accept either the current shared concurrency lock or the visible runtime guard used when GitHub browser upload leaves `.github/workflows` unchanged.
- Main and Historical scanners still use `scanner_run_guard.py` as a runtime backstop, so legacy workflows defer the later scanner before source requests instead of colliding.
- Historical peer-defer remains non-destructive and cumulative.

# v17.20.20

- Fixed Main/Historical scanner coordination: both shipped GitHub Actions workflows now use the same repository-level `ri-research-scanners` concurrency group with `cancel-in-progress: false`, so they queue instead of running source retrieval at the same time.
- Main Radar now uses a fixed four-hour schedule (`00:17, 04:17, 08:17, 12:17, 16:17, 20:17 UTC`); Historical is deliberately placed at `06:53 UTC`, between Main slots.
- Removed the old six-hour due gate from the fixed four-hour workflow; every scheduled Main slot is a real scan slot. The scanner itself still carries the 24-minute evidence-search budget.
- Main workflow envelope is 36 minutes and Pages publish is 6 minutes; Historical publish is also 6 minutes.
- Added a visible-code compatibility safeguard for stale hidden workflow YAML: if an older Historical workflow reaches the runtime collision guard, it performs no source requests, removes no evidence, and refreshes only the expected historical date-window metadata so the legacy verification step does not turn an intentional defer into a false red failure.
- Historical cumulative retention is unchanged. This release changes coordination only, not historical admission or evidence removal rules.

# v17.20.19

- Added **What matters now** as the landing page: a plain-language current picture drawn dynamically from the live Radar evidence.
- The landing page shows up to eight well-supported issues, each with a short explanation, a plain **Why it matters**, and a **Read more** section with live supporting sources.
- Moved the full three-strand evidence reader to **/radar/** and added a large **THE MAIN RADAR** link on the landing page.
- Added a clear page directory from the landing page to Read at least this, Matrix, Trends vs. countertrend competition, Risks & opportunities, External shocks, Historical, Sources, Glossary and Stuff.
- Updated reader navigation so **What matters now** and **Main Radar** are distinct destinations; Radar query links now open the separate Main Radar page.
- Kept scanner-first operation: scheduled scans run the scanner-critical regression suite rather than the complete reader/UI suite before evidence gathering.
- No A/B/C admission or retrieval logic was loosened by this reader change; the scanner remains the primary evidence engine.

# v17.20.18

- External-shock inference is no longer capped by the fixed 4 direct + 10 reasoned scenario library. The scanner now maintains a persistent cross-evidence **emergent shock registry**.
- A genuinely **NEW** emergent shock requires fresh evidence that itself bridges a European R&I capability and a fast external mechanism, plus multiple independent high-quality supporting sources.
- Later scans can mark an existing shock **UPDATED** when fresh supporting or counter-evidence changes its evidence set; unchanged hypotheses remain retained rather than being reinvented.
- Existing direct/reasoned shock scenarios also retain relevant fresh corroboration, so they are labelled **UPDATED**, not incorrectly labelled new.
- External Shocks now shows a top `new · updated` count, includes emergent inferred shocks in the Shock list, and keeps the ↑ supporting / ↓ counter-evidence view plus variants for emergent shocks.
- The current retained corpus seeds one genuinely new emergent seam: a security reclassification narrowing access to European biotechnology/clinical research, supported by the latest dual-use biotechnology evidence plus stronger research-security sources.
- Scanner output records `inferred_shocks_new_this_run`, `inferred_shocks_updated_this_run`, and the retained emergent-shock registry size on every run.

# v17.20.17

- Scanner-first CI: scheduled scans now run scanner-critical regression tests only, so reader/UI release checks cannot prevent evidence collection.
- Removed the brittle ranking test assumption that exactly 17 items must be new in every future scan; ranking is still checked without depending on the latest rotation.
- Renamed the standalone page to **Trends vs. countertrend competition** with a light "evidence tug-of-war" edge, while keeping the inference method private.
- Renamed the External Shocks top index to **Shock list** and ensured realised, direct inferred and reasoned inferred shocks are all added dynamically; shocks using newly scanned evidence get a `new` marker.
- Kept the Radar scanner and A/B/C evidence gathering as the operational priority.

# v17.20.17

- Kept Trends & countertrends as its own analytical page in the reader path.
- Removed reader-facing explanation of the trend/countertrend inference method.
- The page now simply says what the Radar evidence appears to show, while still exposing the supporting source material.
- Removed actor/observer, hostile-witness, claim-role and internal evidence-weight labels from the public Trends page.
- External Shocks remains a separate page; its for/against shock evidence arrows are unchanged.

# v17.20.15

- Added a Trends & countertrends analytical page built from retained Radar evidence.
- Trend pairs count distinct claims rather than publication cadence, distinguish actor-reporting from observer-reporting, and boost hostile-witness evidence.
- Each side of a published trend pair must have multiple high-quality evidence anchors; odds sum to 100 and update from radar.json.
- Added Trends to the guided reader path: Radar → Matrix → Trends → Risks & opportunities → External shocks.
- Every supported shock scenario now shows two directional evidence arrows on the main shock page: what points toward it and what pushes against it.
- Realised shocks with a mapped shock family show the same balance view; full variants retain detailed for/against evidence.
- Counter-evidence on shock variants is ordered by reader-facing evidence quality.
