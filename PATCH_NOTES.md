# v17.19.4 — evidence-worthiness and signal-claim precision

This is a narrow precision release built from the latest uploaded radar run. It keeps the V17.19 recall/centrality model and does not restore the old strategic-language gate.

## Changes
- Routine institutional award/prize announcements no longer qualify as Strand A evidence merely because they mention Horizon Europe, ERC funding or research.
- Narrowly local applied/clinical service studies no longer qualify as core European R&I evidence unless they contain an explicit R&I-system mechanism (for example research infrastructure, governance, collaboration, data/open-science, workforce or legal/regulatory framework) or a strategic-technology mechanism.
- A study does not gain European scope merely because its conceptual framework originated in European contexts; this blocks the Zhongguancun/European-framework false-positive pattern.
- Strand-C claim extraction now rejects grammatical fragments and falls back to a factual headline-derived sentence when needed. The EU–Taiwan semiconductor dialogue is therefore stored as “The EU and Taiwan held their second semiconductor industry dialogue.” rather than “as European industries scale up AI adoption.”
- `scan_results.new_ab_unique` now counts genuinely new retained A/B identities, not pre-dedupe/pre-retention gate candidates.
- Whole-repository Git-history merge has a surgical precision guard so these fixed A/B false positives cannot be resurrected from a larger pre-upload radar snapshot. This is not a full historical re-audit.
- The bundled radar is based on the latest uploaded run: 15 new A items are retained, 4 high-confidence false positives are removed, and the one relevant C signal is retained with repaired claim text.
- `recall_profile_version`, incremental state version, source rotations/cursors and both GitHub security workflows are unchanged.
- Added regression tests for award announcements, local clinical-service studies, conceptual-Europe background, C fragment fallback, retained-new count consistency and bundle-history resurrection protection.

# v17.19.3 — content-type, weak-signal relation and JRC date repair

This is a narrow precision release on top of v17.19.2. It keeps the broader R&I-first recall model and the European-R&I centrality gate unchanged.

## Changes
- Event/training pages such as summer schools are blocked from Strand A unless they are a separate substantive evidence product.
- Contract-style acquisition/delivery/installation/maintenance notices are treated as procurement, not Strand-A evidence.
- JRC Publications Repository handles are always treated as completed publication records for routing purposes: they may be assessed for A/B, but never demoted into weak-signal Strand C simply because the title lacks the word report/study.
- JRC repository parsing now prefers the standalone bibliographic publication date visibly printed on the record over later CMS/index metadata dates.
- Day-level institutional publication dates remain day-level; the scanner no longer invents a 12:00Z timestamp for Strand-C institutional candidates.
- Weak-signal anchoring now requires the selected A↔C watch theme to be supported by the actual extracted signal claim, not merely by unrelated text elsewhere on a long page. This blocks spurious links such as radio astronomy → EU–China de-risking.
- JRC navigation boilerplate (for example “Access to Joint Research Centre's publications”) cannot be used as a weak-signal claim.
- The bundled radar state is based on the latest uploaded run and removes only six bad additions from that run: two A content-type false positives and four C false/incorrectly-routed records. Five new A items remain.
- No `recall_profile_version`, `incremental_state_version`, quality profile, source rotation, or GitHub security workflow was changed. Existing source cursors continue from the latest saved state.
- Added regression tests for summer-school pages, procurement-style notices, JRC publication routing/date extraction, and claim-supported weak-signal anchoring.

# v17.19.2 — EU R&I centrality precision repair

This release keeps the v17.19 recall expansion but adds a narrow centrality guard so Strand A is not filled by papers where Europe or R&I is merely incidental. Strategic/geopolitical wording remains optional.

## Changes
- European/EU scope must be part of the study, policy or evidence subject — not only a historical comparison, literature-background sentence, benchmark/comparator, citation, publisher metadata or single dataset location.
- R&I must be a real topic or mechanism. Generic AI applications, generic academic wording, and stray programme mentions no longer create R&I centrality.
- Europe and the R&I finding may still occur in different sentences. Multi-member-state studies and adjacent EU-framework/R&I evidence remain eligible.
- Institutional event recaps are not Strand A evidence unless the item is itself a report, study, statement, strategy or comparable substantive product.
- Obvious related-content/navigation contamination is deferred instead of admitted on the strength of a good title.
- The bundled live radar state was cleaned narrowly: 18 of the prior run's 38 new A items are retained; 20 incidental/non-substantive additions are removed.
- No recall-profile or incremental-state version was bumped, so OpenAlex/Crossref/institution cursors continue from the saved live state rather than restarting.
- The GitHub repository write-security boundary is unchanged.
- Added regression tests for Chile/background-Europe, Africa–China/historical-Europe, Portugal dataset-only scope, EU programme-list noise, event recaps, cross-sentence European R&I, brain-data sharing and quantum R&I policy.

# v17.19.1 — full-repository safety/state guard release

This is the full repository build of the v17.19 recall change. The GitHub write-security boundary is intentionally unchanged: scanning runs without a stored repository credential; after scanning, all tracked/untracked changes except `radar.json` are restored/removed; the workflow hard-fails if any other repository change remains; and `git add -- radar.json` is the only scanner-output staging command.

To avoid the previous “redo everything” failure mode, this release intentionally does **not** bump `recall_profile_version` or `incremental_state_version`. Existing OpenAlex, Crossref and institutional cursors therefore continue from their saved positions instead of resetting to zero. The new elite-journal and direct-news lanes are bounded additions, not a full corpus replay.

Added regression tests that fail if the scanner gains a pre-scan Git credential, if the radar-only commit boundary is removed, or if this release unexpectedly triggers a full recall-state reset.

# v17.19.0 — recall model: find R&I first, assess strategic impact second

This release changes the radar from a hard strategic-wording admission model to a higher-recall foresight model.

## Why
Relevant research can have important long-run strategic consequences even when the authors do not explicitly use geopolitical, economic-security or strategic-autonomy language. The previous scanner also required Europe/R&I/strategic evidence in overly tight textual proximity, relied too heavily on Google News for core news sources, did not continuously watch broad elite journals, and could miss a late OpenAlex 429 when deciding whether to reallocate search time.

## Changes
- Strand A now requires European/EU scope plus substantive R&I evidence; explicit or triangulated strategic context is no longer a hard admission gate.
- European scope and R&I substance may be established across different abstract sentences or different parts of a longer document.
- Items without explicit strategic evidence are marked for longer-run strategic-significance assessment rather than rejected.
- Added an always-checked source-first elite-journal lane: Nature, Science, PNAS, Nature Communications, Science Advances, Nature Human Behaviour, Nature Machine Intelligence and Nature Biotechnology. These journals never bypass the substantive EU/R&I gate.
- Added bounded direct-source discovery for Science|Business and Research Professional News alongside Google News RSS, making Google News supplementary rather than the sole transport for those core sources.
- Re-check OpenAlex/Crossref health after later scholarly stages so a late HTTP 429 can activate source-failure reallocation.
- Admission diagnostics now state that the strategic-context gate is inactive; historical strategic-rejection counters remain readable for old runs.
- Added regression tests for cross-sentence EU/R&I relevance, the elite-journal lane and direct core-news discovery.

# v17.18.4 — institutional hub/container integrity fix

This release fixes a discovery-container false positive without changing the substantive A/B/C relevance thresholds.

## Why
A Commission hub page titled **“All research and innovation news”** was admitted as Strand A. The page itself is only a listing; the scanner then borrowed the first child story's snippet/date and treated the container as evidence.

## Changes
- Institutional listing/index/archive/search pages are now discovery surfaces only; they can never become A/B/C evidence records.
- The rule uses exact generic titles and exact hub paths, so individual stories underneath a news hub remain eligible.
- Container pages are rejected before date extraction, weak-signal consideration, or the EU-official-news exception can run.
- Saved-corpus sanitation and Git-history restoration apply the same rule, so a previously admitted container page is removed automatically on the next scan after upload.
- Source adapters still crawl those hubs and follow individual publication/story links; recall is not reduced by discarding the hub itself.
- No change to source rotation, four-hour cadence, evidence-quality ranking, Matrix/Read-at-least-this/Risks & opportunities update logic, or the A/B/C substantive gates.

# v17.18.3 — recall allocation repair

This release increases discovery depth without weakening any admission gate.

## Why
The live diagnostics showed OpenAlex HTTP 429 stopping the public endpoint while later recall lanes still treated OpenAlex as available. That wasted part of the scan on an endpoint that had already asked the scanner to stop, while the run still ended below the search-depth target.

## Changes
- HTTP 429 / explicit endpoint-stop warnings now mark a source family unavailable for the remainder of that run.
- A bounded source-failure reallocation stage immediately transfers that time to unused EU/institutional publication sources and the surviving scholarly source family.
- If OpenAlex stops, the replacement scholarly slice prioritises rotating trusted journals in Crossref plus a fresh mixed A/B query slice.
- If Crossref stops, the replacement slice uses OpenAlex plus unused institutional sources.
- Institutional rotation per normal scan increases from 24 to 30 sources, with 12 protected official-EU slots and 10 source-adapter slots.
- Trusted journal source-first rotation increases from 10 to 12 journals per scan.
- Dedicated futures-method queries increase from 12 to 16 per scan; foresight-author follow-up increases from 4 to 6.
- Main runtime budget increases modestly from 20 to 22 minutes; GitHub's 30-minute hard timeout remains unchanged.
- The substantive A/B/C gates, source-quality rules, deduplication, source-link integrity checks, and Matrix qualification rules are unchanged.

The bundled radar.json is marked as a repository bundle seed. On the first scan after a whole-repository upload, the scanner merges the larger pre-upload live corpus and its persisted rotation cursors from Git history after integrity filtering, so newer live evidence is not intentionally erased by the ZIP.
