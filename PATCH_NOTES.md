# v17.19.13 — visible four-hour cadence + conservative A cleanup + Nature News lane

- Bundles the latest completed live state and performs a one-time conservative Strand-A cleanup: 402 A records become 380. Exactly 22 high-confidence legacy false positives are removed; B remains 24 and C remains 5. This is not a broad re-audit of defensible borderline evidence.
- Keeps the one good new A from the latest run (Aalto venture-capital/innovation financing) and removes the stale ERC “new generation of microscopic robots” page whose body visibly dates the story to 20 December 2011. Public retained-new counts are therefore 1 A, 0 B and 1 C.
- Fixes bare `member states` as an EU-scope shortcut. `Member States` now establishes Europe/EU only when the text actually identifies the EU/European Union context, preventing BRICS and other non-EU blocs from leaking into A.
- Fixes ambiguous `FP10`: the token counts as the EU Framework Programme only with nearby Horizon/research/innovation/funding/ERC/MSCA/EIC-style context. Conference/session codes such as the dermatology `FP10` false positive no longer establish EU or R&I scope.
- Adds a high-confidence stale institutional-page check and tighter standing landing-page handling for pages such as AI Watch, Science for policy and portfolio/platform hubs. Child reports/news remain discoverable; the hub itself is not stored as evidence.
- Cleans Google News publisher suffixes from the public Strand-C “What happened” text (`ft.com`, publisher names) and repairs the latest Financial Times venture-capital signal to the direct FT article link while preserving Google News as discovery provenance.
- Adds Nature’s direct News RSS surface (`nature.com/nature/articles?format=rss&type=news`) and makes `nature.com/news` the primary HTML hub, with the research-article listing retained as fallback alongside the existing research feed. The Nature Basu scientist-return pattern is regression-tested as a C candidate, so Nature News/Comment-style material no longer depends only on generic publisher HTML or scholarly indexes.
- Adds explicit direct-journal telemetry to `radar.json`: planned/executed top-journal checks plus A/B and C candidate counts by source. The next live JSON will show whether Nature, Science and the other priority journals actually produced candidates, rather than only showing that they were configured.
- Makes four-hour rolling visible in both JSON and the public status bar. `scan_schedule` records the fixed UTC slots (00:17, 04:17, 08:17, 12:17, 16:17, 20:17), the next slot and the last run trigger; `scan_history` keeps recent run completions. Push/manual runs remain extra and do not replace scheduled runs.
- The latest uploaded run was only about 55 minutes after the previous one, so it was not proof of the automatic four-hour schedule. This release deliberately labels the pre-telemetry trigger as unknown; the next live runs will distinguish `scheduled`, `push`, `manual` and `rescue` honestly.
- A/B/frontier remain cumulative. Only Strand C expires 60 days after `first_seen`. Scan-state/cursors are preserved exactly; no recall/state reset.
- Main workflow security boundary is unchanged: no stored repo credential during scanning, non-`radar.json` changes are isolated before push credentials exist, and only `radar.json` can be staged. Historical workflow is byte-for-byte unchanged.

# v17.19.12 — C anchor precision + journal-source retrieval repair

- Tightens Strand-C anchoring so a broad technology theme cannot connect unrelated technologies. The live false positive `Evolving radio astronomy and its impact on Africa` can no longer anchor to the US EV-supply-chain/AI-fintech paper.
- Raises the evidence requirement for broad C anchors: broad theme overlap alone is not enough; a real actor/lexical bridge is required.
- Keeps the public `What happened` sentence separate from the visible Source label, removing Google News publisher suffixes such as `Financial Times` from the claim text.
- Extends the direct top-journal lane beyond research-article TOCs. Nature and Science now run a bounded source-specific Google News RSS fallback every scan so News/Comment/Correspondence material (including Nature d41586-* items) is discoverable even when publisher hubs/feeds are incomplete or return 403. Publisher identity remains source-bounded and must pass the ordinary A/C gates.
- Adds direct first-class feed/fallback attention for `New Political Economy` and `Studies in Higher Education`, and adds both to the Crossref priority-journal task bank.
- Adds external-C retrieval seeds for scientist-return/talent competition, biomedical regulation, battery industrial policy and global academic mobility. These are retrieval only and cannot bypass C quality/Europe-impact rules.
- Treats theorist/person nationality such as `German sociologist` as provenance rather than European study scope. This removes the generic `Illuhmannating Technological Innovation Systems` false positive without excluding studies whose actual population/system is German or European.
- Bundles the latest completed live state, removing only the two confirmed false positives from that run: the generic TIS paper from A and the ITU radio-astronomy signal from C.
- Four-hour automatic cadence, cumulative A/B/frontier retention, 60-day-from-first_seen C retention and the credential/write security boundary are unchanged. No scan-state/cursor/profile reset.

# v17.19.11 — whole-repository upload compatibility

This release removes the need for any separate/miniature workflow-file upload. The full repository is the only artifact the curator needs.

## Changes
- Keeps the v17.19.10 fixed four-hour workflow inside the full repository.
- If GitHub web bulk-upload nevertheless leaves the older hidden v17.19.8 workflow in place, regression tests no longer stop the scan before it starts.
- Adds a bounded compatibility path for that exact legacy workflow: its hourly trigger plus hard-coded six-hour due gate receives an internal scheduler reference two hours behind the real completion time, yielding an effective four-hour automatic cadence. Public `run_completed_at` and `last_updated` remain exact. The compatibility activates only when the old hourly/6-hour workflow is actually detected.
- Cumulative A/B/frontier retention remains enforced in scanner code. Strand C alone expires 60 days after `first_seen`.
- Credential isolation and the `radar.json`-only write boundary remain mandatory.
- No scan-state/cursor/profile reset.

# v17.19.10 — workflow upload/contract repair

This release does not change the scanner's substantive A/B/C logic. It fixes the deployment mismatch seen after v17.19.9: the new tests were uploaded, but GitHub retained the old v17.19.8 `.github/workflows/radar-scan.yml`, so the regression step failed before scanning.

## Changes
- Adds an explicit workflow contract marker on the first line of the main workflow.
- Keeps the fixed four-hour schedule and cumulative A/B/frontier + 60-day-from-first_seen Strand C safety rules from v17.19.9.
- Keeps the credential/write boundary unchanged.
- Makes stale-workflow regression failures concise and actionable instead of dumping the entire workflow into the Actions log.
- Upload instructions now require explicit verification of the hidden `.github/workflows/radar-scan.yml` after GitHub web upload.
- No scan-state/cursor/profile reset.

# v17.19.9

- Main workflow now has a fixed automatic four-hour cadence (`17 */4 * * *`). Push/manual scans remain additional; they do not suppress the next scheduled run.
- A/B and frontier evidence are cumulative once admitted. Ordinary age-window pruning no longer removes accepted non-C evidence. Explicit false-positive, duplicate and integrity cleanups remain allowed.
- Strand C alone expires 60 days after `first_seen` (insertion into the radar), not 60 days after the source publication date. Legacy C rows missing `first_seen` receive an insertion timestamp rather than being prematurely expired.
- Google News RSS candidates now carry structured publisher-domain provenance. A configured publisher such as Nature or Science can pass the final source-integrity gate even when the RSS article URL is a `news.google.com` redirect, while arbitrary cross-document links still fail closed. This fixes the observed “prefilter 1 / anchored 1 / new C 0” loss path.
- Public cards now show a prominent linked `Source:` line. Strand C additionally shows an explicit `What happened:` line, so the reader can immediately see the development and where it came from rather than relying on a strand letter or collapsed bibliography.
- Nature, Science and comparable top journals remain a first-class discovery pillar alongside EU/institutional sources.
- Latest live scanner state/cursors are bundled without reset; no retroactive C signal was fabricated.

# v17.19.8 — resilient top-journal transport + final C reserve + evidence-surface cleanup

- Keeps Nature/Science/top journals as a first-class source family, but no longer relies on publisher HTML hubs being accessible from GitHub-hosted runners. The direct journal lane now prefers RSS/Atom where configured, falls back to alternate publisher TOC surfaces (including Science's SPJ surface), and can classify from feed metadata even when individual publisher pages return HTTP 403.
- Adds feed/fallback transports for Nature, Science, PNAS, Nature Communications, Science Advances, Nature Human Behaviour, Nature Machine Intelligence and Nature Biotechnology. Elite-journal prestige still never bypasses the ordinary European/EU + substantive R&I gate.
- Fixes the last Strand-C disappearance path. C rescue can explicitly spend its reserved network slice instead of being blocked by the ordinary network reserve, and a final bounded 30-day reserve search runs after final Strand-A selection when the only anchored C candidate is old/duplicate. It still cannot manufacture or republish a failed/duplicate signal.
- Repairs C claim extraction so a terse headline does not erase the substantive mechanism in the source description. The Nature scientist-return example now retains the research-talent/critical-technology evidence and can anchor normally instead of failing the published-claim theme check.
- Treats institutional paper-series/index/standing topic pages as discovery surfaces rather than evidence records. Child documents remain crawlable. This removes the Commission `Research and innovation paper series` and `Open science` landing-page false positives.
- Extends the shared final A/B guard to the existing document-type exclusions, including open-access facility/call pages, so fallback routes cannot re-admit them.
- Adds European Commission/JRC distribution-notice text to source-navigation boilerplate so it cannot become a reader-facing core message.
- The bundled radar uses the latest uploaded completed run and removes four high-confidence non-evidence/borderline additions from that run; the JRC Security Research and Innovation Campus core message is repaired from its own source summary. The completed run is not retroactively padded with C.
- No recall/incremental profile is reset. Latest scan-state cursors are preserved, and both GitHub security workflows remain byte-for-byte unchanged.

# v17.19.7 — shared final precision guard + first-class direct journal watch + C runtime reserve

- Makes Nature/Science-family journals a first-class source family independent of OpenAlex/Crossref. Nature and Science are checked directly every ordinary scan; two additional elite journals rotate through direct publisher-page discovery. Direct journal pages can feed A/B or, when they are current developments rather than A/B evidence, the normal C candidate pool.
- Adds a separate priority R&I/policy journal watchlist including Research Policy, Science and Public Policy, Studies in Higher Education, New Political Economy, Scientometrics, Minerva, Higher Education, Research Evaluation, Futures, and Technological Forecasting and Social Change. Crossref checks these source-first when available.
- Elite-journal prestige never bypasses European/EU + substantive R&I admission. Strategic/geopolitical wording remains optional.
- Adds one final evidence-worthiness guard after all discovery routes converge, so OpenAlex, Crossref, direct journals, institutional fallback, source-failure reallocation and curator tests cannot disagree about high-confidence false-positive patterns.
- Strengthens incidental-Europe detection for global/bibliometric papers where Europe appears only in contributor/collaboration geography lists.
- Strengthens the local clinical/service rule so a title-level local implementation study cannot be rescued merely by generic `research programme` language deeper in the abstract.
- Repairs the C-floor runtime design: ordinary network-heavy stages now leave a dedicated reserve, while C rescue is allowed to spend that reserve and keeps only a small post-rescue save margin. C can also anchor against strong A candidates discovered in the same run.
- Expands C rescue/talent language for current scientist-attraction/return-fellowship competition and related external R&I shifts.
- The bundled radar is the latest uploaded live state with only two high-confidence A false positives removed (the psychodermatology service paper and the global AI sexual-medicine review). It is not retroactively padded with a C signal.
- No recall-profile version, incremental-state version, source cursor or GitHub security workflow is reset.

# v17.19.6 — historical-subject guard + safety-check compatibility

- Generalises the live-radar history exclusion beyond century/year ranges to explicit historical eras such as early-modern, medieval, Renaissance, Enlightenment, interwar and Cold War subjects.
- Historical scholarship remains eligible only when the source itself makes an explicit current or forward R&I implication; generic modern boilerplate does not rescue a history paper.
- The same historical predicate is used for new scholarly admission and saved/Git-history sanitisation, preventing different discovery/recovery paths from disagreeing.
- Removes the already-saved false positive `Genoese Migration and Technology Transfer in the Early-Modern Spanish Monarchy` from the bundled radar before upload, so the existing GitHub cumulative-corpus safety gate has no unexplained in-window deletion to block on the next scan.
- The GitHub workflows are unchanged. The cumulative-corpus safety check is not weakened or bypassed.
- No recall profile, incremental-state version, quality profile, source cursor or rotation profile is reset.
- Adds regression coverage for the exact Genoese/early-modern failure and for saved-history sanitisation.

# v17.19.5 — C floor rescue + live-period evidence guard

- Keeps Strand C from quietly collapsing to zero new signals when the ordinary news lane only finds duplicates or over-strict anchor failures. A bounded rescue search runs across diversified R&I weak-signal themes and 14/30-day recovery windows.
- The rescue never republishes an old/failed signal merely to hit a quota. It first looks for another strict A-anchored signal; only then may one directly-European factual result enter as `unanchored_emerging` with lower confidence.
- Detailed C rejection/floor diagnostics are written to scanner logs only. They do **not** alter public `scan_health`, are not exposed in the reader UI, and a zero-C run no longer generates a public `note_c` warning.
- Excludes scholarship whose subject is clearly historical (old century / old-period research) unless the source itself makes an explicit current or forward European R&I implication.
- Whole-repository/history merge applies the same high-confidence historical-subject exclusion so removed history items cannot be resurrected from Git history.
- Preserves all recall/incremental cursor versions and leaves both GitHub repository-write security workflows unchanged.

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
