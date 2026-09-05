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
