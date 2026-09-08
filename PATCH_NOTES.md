# v23.4 — cumulative adversarial inference + protected A priority

This release adds a hidden post-scan analytical layer for the higher-order patterns discussed in the Level-4/5 worked examples. The examples are encoded as **reasoning grammars**, not as canned conclusions or topic lookups. The exact worked-example detectors remain only as executable regression/specification helpers; the production detector list uses relation-level grammars rather than privileged programme/document-name shortcuts. Every completed main scan runs the analytical pass. Most new evidence should change nothing visible; unfinished candidates persist, accumulate support or counter-evidence, generate bounded missing-link/falsifier searches, and compete for a very small number of reader-facing slots.

## Constant thinking, sparse output

- Every newly admitted **A/frontier** record and **C** weak signal is evaluated by the post-scan high-order pass. Strand B is intentionally absent because it is the independent methods library.
- Candidate state persists in `radar.json` under `high_order_inference`: status, covered/missing evidence roles, evidence IDs, counter-evidence, lifecycle state and bounded follow-up queries. This is structured audit state, not reader-facing chain-of-thought.
- Most candidates remain dormant/watch. They are not deleted merely because a later scan fails to redetect the pattern; analytical state decays slowly and qualification does **not** guarantee display.
- Higher-order publication is capped at **two additional findings per reader product** (`shock`, `risk`, `opportunity`, `continuity`, `trend`). Candidates compete on evidence strength, source diversity and distinctiveness; duplicate grammar/topic variants do not fill multiple slots. Publication uses hysteresis: a merely newer candidate does not automatically evict an incumbent; a challenger must be materially stronger or the incumbent must weaken.
- Every surfaced higher-order candidate must be **denial-tested** and carry at least one explicit falsifier/counter-case search. Counter-evidence reduces the candidate score; it never rewards novelty.
- Level 5 has the higher publication threshold. A surprising inference therefore has a higher evidence burden, rather than receiving a novelty bonus.

## Level-4/5 reasoning grammars

The worked examples were reduced to reusable structural moves that can apply to subjects not named in the examples:

1. **Omitted dependency → dependency-of-dependency → propagation** (shock).
2. **Conflicting criteria acting on the same decision object + missing arbitration rule** (risk).
3. **Unresolved programme problem + adjacent institution that already has the required capability + live connection/precedent** (opportunity).
4. **Goal repeatedly invoked across domains + missing/fragmented measurement** (continuity).
5. **Commercial first mover acts before standards/testing infrastructure is ready → path-dependence risk** (shock).
6. **Programme success condition differs from what the system actually measures** (risk).
7. **European comparative weakness + underused existing asset + tractable bottleneck + payoff evidence** (opportunity).
8. **Practice/instrument use predates the doctrine that later names it** (continuity).
9. **Opposing institutional actions acting on the same underlying object** (trend/counter-trend).

The Level-5 dependency grammar is deliberately directional. It only tests plausible dependency chains (for example compute → energy/materials or chips) rather than cross-producting every topic with every other topic. This prevents broad co-occurrence from manufacturing synthetic shocks.

## Slow analytical lifecycle + persistent missing-link and falsifier search

- Analytical candidates accumulate much more slowly than scanner records. One missed detector pass leaves an incumbent unchanged; after three consecutive non-redetections a qualified candidate steps down to watch, and after six it becomes dormant. It remains in hidden analytical memory rather than being deleted.
- New shocks/findings never delete old ones merely because they are newer. The older dynamic-shock registry no longer has a fixed-size crowd-out that could silently discard previous hypotheses.
- Existing watch/dormant candidates contribute a bounded alternating bank of **support** and **falsifier** queries to later scans.
- These queries use the existing finding-context budget and up to four slots in the ordinary trusted-news weak-signal lane. They do not create a new unlimited search lane.
- Candidate-driven searches never bypass normal A/B/C admission. A stronger source discovered through C follow-up must enter separately through the ordinary A gate.
- The scanner explicitly searches both for evidence that closes a missing link and evidence that would break/absorb the proposed mechanism, reducing confirmation bias.

## Trends: evidence tug-of-war, not probability

- The emergent trend grammar operates on an **object** and two opposite directions of institutional action. The counter-force is searched deliberately; it is not decorative.
- The first implemented same-object grammar is the distribution of European R&I capacity/resources/access: physical money/hardware concentration versus distributed access/participation.
- Trend balance counts **distinct institutional actions**, not generic topic mentions or supporting studies. The generic detector requires a formal/institutional action record and rejects journal analyses and loose cooperation/open-language matches. Near-duplicate reports of the same action are collapsed.
- Raw action balance is compared with a repeat-source-adjusted balance. Repeated actions from one source contribute `1.0`, `0.5`, `0.25`, then `0.125` each. The two pulls always sum to **100** and are explicitly an evidence balance, not a forecast probability.
- On the packaged current corpus the stricter generic grammar retains **4 concentrating vs 3 spreading actions** from three source families: 57/43 raw, 48/52 after repeat-source discounting. Its score remains just below the higher-order publication threshold, so it stays hidden rather than being forced onto the page. This is intentional sparse-output behaviour.

## Evidence hierarchy remains strict

- **A remains the primary substantive backbone.** The first **20 broad scholarly query slots per source** are protected for A-oriented discovery when budget allows; B method discovery can use later broad slots but cannot crowd out that protected prefix.
- **B remains permanent and independent.** Method-search allowance rises only modestly: `queries_b_method_per_scan` **32 → 36**, bounded method-author follow-up **8 → 10**. B never enters world-state high-order inference, risks/opportunities or shocks.
- **C remains temporary weak world evidence.** The 60-day retention and **0.30 contextual weight** remain unchanged. Discovery is nudged rather than loosened: weak-signal follow-up **8 → 10** queries/wave, max passes **3 → 4**, direct-news pages/source **12 → 14**, links/source **30 → 34**, bounded C rescue target **2 → 3**, and rescue queries/wave **6 → 8**.
- Up to **4 candidate-driven news queries per scan** may look for missing links or falsifiers, but every result still needs the trusted-source, 60-day, substantive A-anchor and C admission gates.
- History remains contextual only where already allowed; it cannot close a current primary role.

## Reader integration

- Risks & opportunities, external shocks, ongoing phenomena and trends consume only IDs selected in `high_order_inference.publications`; the hidden candidate pool is not dumped onto the site.
- Existing ordinary findings remain. The higher-order layer adds only a sparse set of unusually well-supported findings.
- Trend higher-order cards can show the balance range and action/source counts, while the internal candidate construction, missing links and falsifier machinery stay out of the reader prose.

## Regression coverage

`tests/test_v234_cumulative_adversarial_inference.py` verifies primary-role protection from C, B exclusion, automatic A/C post-scan evaluation, sparse/adversarial publication, directional shock chains, support + falsifier feedback, protected A scheduling, mild B/C expansion, 100-point trend balance and raw-vs-source-adjusted range, reader selection through publication IDs only, same-scan qualification for a complete adversarially-tested Level-5 chain, slow lifecycle/hysteresis, and that production uses generic reasoning grammars rather than worked-example shortcuts.

Validation on the packaged tree:

- `pytest -q`: **68 passed, 33 skipped, 0 failed**.
- `python -m unittest discover -s tests -p 'test_*.py'`: **168 tests, 66 skipped, 0 failures**.
- A single real-corpus higher-order pass runs in roughly **2–3 seconds** locally, far below the six-minute GitHub safety margin and without reducing the 1,440-second scanner budget.
- Fresh-state real-corpus dry run: the hidden pool remains bounded and production selects **1 higher-order shock and 2 continuity findings**; current higher-order risk, opportunity and emergent-trend candidates are allowed to remain hidden/watch rather than being forced into reader slots.

---

# v23.3 — contextual weak signals + historical shock context

This release separates the three evidence roles explicitly: **A is durable substantive evidence about the world; B is a persistent methods library; C is temporary weak-signal evidence about the world.** The change lets C and selected history inform downstream reasoning without letting either substitute for primary current evidence.

## Evidence hierarchy

- **Strand B stays forever and stays independent.** It is no longer fed into strategic risks/opportunities or external-shock inference. Discovery effort for B is increased (`queries_b_method_per_scan` 24 → 32; bounded author follow-up 6 → 8), but its admission gates are unchanged.
- **Strand C remains 60-day evidence.** The configured 1,440-hour window was already two months, but Google News query construction had an internal 30-day cap. That cap is now 60 days, so discovery/backfill actually matches retention.
- **Trusted analytical/commentary C lane.** A small explicit high-trust outlet list can contribute well-formed analysis/opinion as C when it has a substantive R&I/geopolitical bridge, a diagnostic mechanism/reframing, and a substantive Strand-A anchor. Pure advocacy, sponsored material, interviews, letters, book reviews and unanchored opinion still fail.
- Every C/current-media contextual item carries **0.30 analytical weight** and `context_only=true` where it enters strategic pathways. It cannot originate a risk, opportunity or shock by itself.

## Risks & opportunities

- Reader inference now uses A/frontier/primary strategic-pathway evidence as the finding-forming corpus. Strand B is excluded.
- C and recent trusted-media strategic records are attached only to an already-supported risk/opportunity with the same conservative topic/lens match.
- Each contextual item is capped at **0.30**; combined ranking influence is capped at **0.60**. Primary publication/evidence quality remains dominant.
- The evidence disclosure shows which recent weak signals are corroborating the finding instead of silently counting them as full evidence.
- Current-media strategic-pathway context expires after 60 days; it no longer becomes permanent merely because it entered the strategic-pathway registry.

## External shocks

- Dynamic shock inference now uses **A + primary strategic pathways** for all admission gates. Strand B is excluded.
- C/recent trusted media can corroborate an already-supported shock at **0.30 per item**, with only a bounded score bonus. A fresh C item can update an existing shock but **cannot create a NEW shock**; NEW still requires a fresh primary capability × pressure coupling.
- Historical scanner material is loaded transiently from `historical/historical.json`. Only historical **Strand A** records are used, at **0.45 contextual weight**. History can strengthen structural/dependency context but can never be treated as a fresh trigger.
- Counter-evidence/prevention evidence and source-diversity/admission thresholds remain primary-evidence-only.
- The older template-based shock path now follows the same hierarchy, so C cannot fill a missing template role there either.
- Shock evidence details label contextual items and their analytical weight.

## Regression coverage

`tests/test_v233_context_evidence_hierarchy.py` verifies that B is excluded, C/history are correctly weighted, C cannot supply a missing primary shock coupling, C can update but cannot originate a shock, fresh primary coupling can originate one, the two-month query window is real, trusted commentary can enter the C candidate lane, and risks/opportunities attach C only as subordinate context. The same test is bundled into `tests/all_tests.zip`.

---

# v23.2 — primary-evidence + scheduler repair

This repair removes the GitHub regression-gate failure and tightens the scanner contract rather than merely weakening the tests.

## Fixed now

- Primary-evidence regression tests use synthetic fixtures instead of assuming the live cumulative `radar.json` is still missing a document that the scanner may already have found.
- A proposal target is not considered complete merely because an annex, impact assessment or other companion attachment exists. The deep lane keeps revisiting the canonical hub until the requested proposal/report itself is present.
- Once a substantive institutional PDF/download is known behind a landing page, the HTML wrapper is removed as a duplicate evidence item. If the generic institutional crawler rediscovers the wrapper in the same scan, it is suppressed.
- The wrapper's original `first_seen` timestamp is preserved on the deeper primary document and the replacement is not falsely labelled NEW.
- The GitHub cumulative-corpus safety guard recognises a landing-page -> primary-document replacement as continuity, so it does not reject the scanner's intentional upgrade.
- Main scheduling is restored to the repository contract: 00:17, 04:17, 08:17, 12:17, 16:17 and 20:17 UTC. Historical scanning runs exactly two hours later and both scanners share one non-cancelling concurrency queue.
- `tests/all_tests.zip` contains the same repaired primary-evidence regression cases as the visible test file.

## Scanner depth contract

The main scanner is intentionally a bounded deep research scan, not a shallow news poll. Production gives it 1,440 seconds (24 minutes). Normal discovery is incremental with a 14-day overlap, while rotating/deep recovery can look across the configured six-month current window and the primary-evidence lane can revisit canonical targets across a 12-month lookback.

It spends that budget across independent source families: OpenAlex, Crossref/journal depth, more than 200 configured institutional sources, direct current-development sources, exact EU primary-document hubs, citation snowballing, priority researchers, Matrix/frontier gap recovery and low-yield/full-budget continuation. Breadth comes before depth inside large institutional source sets so one fast sitemap cannot monopolise the scan. Deeper pagination and citation adjacency are then used where they improve recall. All routes still face the same A/B admission and evidence-integrity gates.

The scan should therefore keep going until the time budget/reserves are reached, rotate what it could not finish into later runs, and prefer the substantive downloadable primary evidence behind a publication hub over the hub page itself.

---

# v23.0 — calm working Radar

This release fixes the two problems that had become entangled: the Radar must work, and the reader-facing site must stop showing its entire architecture at once.

## Reader experience

- Homepage now gives three decisions only: **Read at least this**, **Search the evidence**, **Go deeper**.
- The live topic view remains source-weighted, but the homepage shows only the strongest readable set; all active topics remain one click away.
- `explore/` is now a plain question-led depth index. The large modal/menu wall is gone.
- Inner pages use a small shared bar: **Briefing / Radar / Go deeper**.
- Surface pages remove repeated process diagrams, dashboards, rounded card chrome and large navigation blocks.
- Risks & opportunities use a single reading stream instead of two competing columns.
- Ongoing phenomena lead with the finding; diagnostics and evidence sit behind disclosure.
- Matrix still collapses to readable mobile blocks.

## Radar

- Radar is isolated from the shared redesign layer.
- Original Radar application script is preserved.
- First usable screen is: title + current counts + search/filter controls + evidence.
- Search, New, Latest 30 days, Clear, More info and source links remain functional.

## Dirty-repository compatibility

Earlier GitHub browser uploads left obsolete standalone tests behind. This release deliberately passes both:

- the maintained bundled suite (`tests/test_all.py`), and
- the old 116-test discovery run if the legacy `test_*.py` files are still present.

That means the scanner is no longer blocked just because GitHub failed to delete obsolete tests.
