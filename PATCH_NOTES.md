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
