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
