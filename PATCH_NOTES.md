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
