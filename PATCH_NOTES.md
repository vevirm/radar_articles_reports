# v21.7 — richer Trends / counter-trends

- Expanded the Trends page from the previous thin set to nine current evidence tug-of-war pairs supported by the present Radar corpus.
- Trend admission is now easy to explain: each side needs at least three current Radar records from at least two sources; the opposite side must pass the same gate.
- Kept the evidence weighting because it makes the balance useful and lively. Stronger and more independent evidence pulls harder; repeated publication from the same source is discounted. The displayed number is explicitly a balance score, not a forecast.
- Historical publications are read only from `historical/historical.json` and only when they are older than the rolling six-month boundary. They can add roots/persistence/reversal context, but they cannot create or qualify a current trend.
- Added more readable and occasionally playful pair framing while keeping WHAT/WHY explanations serious and evidence-grounded.
- Trends evidence remains closed to the repository evidence base: current Radar first, Historical only as optional older context; no outside facts are added by the page.
- Carried forward the v21.6 production workflows: Main every four hours at :17 with 24 minutes; Historical every four hours at :57 with 10 minutes; one shared research slot with Main priority.
- Repository remains below 100 files after removal of cache files and obsolete quarantined test wrappers.

# v21.6 — Historical full-window + visual palette audit

- Historical scanner updated to the v21.5 full ten-minute research-window behavior: item targets no longer stop discovery; only an 8-second final save margin is protected.
- Historical and Main production workflows restored to the required four-hour offset with one shared research lock and Main priority.
- Public pages now share one final white/black/red UI override. Menus use black backgrounds, white labels and red active/hover/focus states.
- Mobile navigation uses a readable horizontal strip rather than compressed labels or a tall wrapped menu.
- Removed Python bytecode caches and obsolete quarantined version tests; active production tests remain.

# v21.4 full-budget scanner repair

This build fixes the early-finish problem seen in live Main scans.

- Main still has a 1,440-second research budget, but that budget is no longer only a ceiling. If ordinary lanes finish early, a full-budget continuation rotates through unused institutions, different Crossref/OpenAlex query slices, deeper scholarly pages and current-development searches until only a small finalisation reserve remains.
- Repeated zero-yield Matrix waves no longer cause the whole scanner to finish early; they only stop that particular Matrix lane.
- OpenAlex/Crossref rate limits now count as unavailable source families for reallocation. The previous code promised this in comments but only reallocated on hard failures.
- An authenticated OpenAlex 429 is now labelled correctly instead of being reported as a keyless limit.
- Extra time changes search breadth and depth only. A/B/C admission rules are unchanged, so a genuinely quiet cycle may still add zero records rather than lowering quality.
- Historical remains a 10-minute cycle and now has a 540-second minimum runtime floor before final save work.
- Production workflow remains Main every four hours at :17 and Historical every four hours at :57, using one shared research slot with Main priority.
- Repository remains below 100 files.

# v21.3 production update

This full-repository build aligns the live code with the current operating and writing rules.

- Main runs every four hours at minute 17 with a 24-minute research budget.
- Historical runs every four hours at minute 57 with a 10-minute research budget.
- Main and Historical share one research concurrency group; Main has priority and may pre-empt Historical.
- The old rescue dispatch and production regression-test gate are not part of the live workflows.
- Easiest reader pages use ordinary language. Difficult abbreviations and technical method/classifier language belong behind Read more, in the Glossary, or in Stuff. Visible shortened sentences do not end in ellipses.
- Shock inference now follows a challenge-first pattern: evidence join → possible shock → required conditions → case against → what could prevent it → what to watch → net assessment.
- The Stuff evidence workbook now includes a Shock audit sheet for the technical shock trail.
- The retired manual shock toy is absent.

The scanner write boundary remains narrow: Main persists `radar.json`; Historical persists `historical/historical.json`. Public pages have no repository write credential.

## GitHub file-count cleanup

- Removed legacy repository-history test wrappers that were already quarantined and permanently skipped for the fresh cumulative baseline.
- Kept the active Main scanner tests, security/state-guard tests, Historical scanner tests, workflows, site, evidence stores, scripts, configuration and Stuff workbooks.
- The repository remains a complete usable repo while staying below 100 files for GitHub upload.
