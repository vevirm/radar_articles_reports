## 17.20.12 — recall-first discovery across hundreds of quality sources

- Rebalances the scanner toward recall: missing a high-quality, high-relevance paper/report is treated as a larger failure than admitting a marginal source-valid item that reader ranking can push down.
- Expands the configured institutional/source universe from 112 to 199 bodies and the source-first scholarly journal universe from 58 to 171 venues (370 configured source families before query/search lanes).
- Every ordinary scan now attempts a full source census of the configured journals and institutional bodies where transport/time allows, instead of touching only a small rotating subset.
- Institutional parsing is breadth-first: every source with a candidate page gets one parser slot before any source gets a second, so giant sitemaps cannot crowd out smaller academies, funders, ministries or research bodies.
- Broad scholarly query slices are materially larger (36 base queries; up to 100 OpenAlex and 110 Crossref broad queries per scan), while the 24-minute hard scanner budget remains unchanged.
- Adds a conservative missing-abstract recall route for Tier-1/2 scholarly records whose title itself clearly establishes European scope plus substantive R&I. Unlisted/low-tier journals do not get this waiver.
- Expands trusted scholarly publishers and the EU R&I/geopolitics query vocabulary; normal European/EU R&I aboutness remains the topical admission gate and reader priority ranking demotes weaker strategic fit.
- Bumps the source-expansion marker so the next scan backfills the newly added source universe across the normal retained window rather than only checking the latest overlap.

## 17.20.11 — risk/opportunity polarity + plain-language reader

- Fixes the core polarity error on the Risks & opportunities page: a measure that is explicitly addressing or mitigating a problem is no longer presented as though the measure itself were the risk.
- The supplied **Choose Europe for Science** evidence now appears as an opportunity (better career conditions can help Europe retain and attract researchers), not as a risk. Its mention of brain drain remains evidence of the underlying problem, but the programme is treated as the response.
- Adds a mitigation-direction guard both to the repository reader and to scanner source-text classification, including protection against legacy source-filed risk labels that describe a remedial action.
- Keeps genuine analytical risks intact when a paper happens to mention a benefit elsewhere; for example, reducing fossil-fuel dependence does not erase a separate critical-material scarcity risk.
- Broadens opportunity recognition beyond only open calls: an operational programme or pilot can qualify when it is a concrete response to a stated strategic R&I problem and has a credible gain pathway.
- Rewrites Risks & opportunities cards in plain language. Source/document titles are no longer used as the risk/opportunity statement.
- Replaces classifier-facing **Why it qualifies** details with a reader-facing **Read more** expander showing **What the risk/opportunity is**, **What the source says**, and the evidence source.
- Adds regression tests for mitigation polarity, Choose Europe for Science, plain-language presentation, and preservation of unrelated genuine risks.

## 17.20.10 — repair cumulative A/B retention after Strand-C funding tightening

- Fixes the scan failure shown after v17.20.9: the new “generic EU funding is not automatically a weak signal” rule was accidentally applied inside the shared A/B merge path.
- The funding/geopolitical-setting filter is now confined to Strand C, where it belongs. Previously accepted Strand A and B evidence is carried forward cumulatively during normal scans.
- Valid A material such as science-diplomacy partnerships, strategic-dependency funding and research-infrastructure evidence can no longer disappear merely because the title contains an EU funding/programme move.
- Strengthens the workflow safety gate to match the actual cumulative contract: on an ordinary scan, every prior A/B item must survive regardless of publication age; only an explicitly flagged precision/migration cleanup may remove a known hard failure.
- Adds regression coverage so future weak-signal precision changes cannot silently leak into A/B retention.

## 17.20.9 — weak signals require a geopolitical reason, not merely EU funding

- Strand C no longer treats routine EU grant, call, award or programme-funding announcements as weak signals merely because they concern Horizon Europe, researchers or innovation.
- An EU funding move may enter C only when the source itself gives a specific geopolitical/geoeconomic purpose, mechanism or setting — for example research/economic security, strategic autonomy, de-risking, export controls, strategic dependencies, third-country participation, science diplomacy, defence/dual-use, sanctions, or a named external geopolitical actor.
- The rule is applied both to newly discovered candidates and cumulatively retained C rows, without re-auditing or deleting unrelated weak signals.
- The generic ERC Starting Grants 2026 announcement in the supplied corpus is removed from Strand C; the latest productive-scan count is corrected accordingly.
- Adds regression tests so a generic ERC/Horizon funding announcement fails while genuinely geopolitical funding settings remain admissible.

## 17.20.8 — cumulative historical evidence

- Historical evidence is now append-only during normal scans: once accepted, an item is retained even if later gate/taxonomy changes would not admit it as a new discovery.
- New scans may enrich an existing historical row or suppress a newly found duplicate, but they do not silently re-test and delete the retained archive.
- Removes the finite historical `max_items` cap, which would eventually have forced old accepted evidence out as the archive grew.
- Adds explicit cumulative-retention diagnostics to each historical scan result (`normal_scan_deletions: 0`).
- New admission quality remains strict: cumulative retention changes what may stay, not what may enter.

## 17.20.7 — black links on white + browser-upload-safe regression gate

- Reader links on white surfaces now render black (including visited links); red is retained for borders, underlines, active states and emphasis. Dark headers keep white link text.
- `Read at least this` supporting links and External Shock variant links follow the same black-on-white rule.
- The v17.20.6 workflow regression test now tolerates the older hidden `.github` workflow that GitHub's browser bulk uploader can leave in place, while still enforcing the 24-minute scanner budget in visible configuration.

v17.20.0

- Restores the main Radar to its three original strands: A quality papers/reports, B foresight methods, C weak signals.
- Removes the temporary News/Watchlist framing and removes external-shock summaries from above the Radar results.
- Restores Read at least this as exactly eight visual topic trees (main topic -> subtopic -> sub-subtopic), with no prose digest on that page.
- Adds realised external shocks plus six cross-evidence shock scenarios with explicit reasoning, second-order effects, why the seam is easy to miss, and the exact evidence rows/fields used.
- Keeps the roomier 100-character Matrix and simple conceptual line icons.
- Gives the scanner 24 minutes and the publish/update job 6 minutes.

## 17.20.1 — web-upload workflow compatibility
- Keeps the scanner's actual 24-minute runtime budget (`scan_budget_seconds: 1440`).
- Stops reader/scanner regression tests from failing merely because GitHub's web "upload over the top" retained the previous `.github/workflows/radar-scan.yml` (30-minute job / 5-minute publish trigger).
- The shipped workflow still uses the newer 36-minute scan envelope and 6-minute publish trigger when `.github` is replaced successfully.


## 17.20.2 — legibility, lighter pages, direct external shocks
- Read at least this remains exactly eight charts, but the chart field is now white rather than black; main nodes use red and the hierarchy uses only black/red/white.
- Quick and full Matrix are wider, less tight and use materially larger labels, cell headings and evidence text.
- Risks & opportunities use larger typography and a little more breathing room.
- A site-wide legibility pass raises the smallest reader-facing type without changing the black/red/white visual identity.
- External shocks now keeps realised shocks and the cross-evidence “aha” scenarios, and adds a separate direct-shock layer for obvious, evidence-supported disruptions.

## 17.20.3 — visible additions on the Radar
- Adds a compact live count strip to the main Radar: papers/reports, weak signals, records checked, items added in the latest scan, items added in the previous 24 hours, and scanner runtime.
- Adds pressable `Added last scan` and `Added 24h` filters. Recent additions are sorted by insertion time and visibly tagged.
- Uses `first_seen` plus the scanner's run timestamps, so the filter shows what entered the Radar rather than merely what has a recent publication date.
- Keeps `Added 24h` separately because a rescue scan can legitimately add zero items even when earlier scans in the same day added material.
- Gives the Read-at-least-this topic trees slightly more finished branch connectors while staying strictly black/red/white.


## 17.20.4 — shock variants and counter-evidence
- Every supported direct or reasoned external-shock scenario now has a `Variants & evidence` button leading to a dedicated second-level page.
- Each shock gets three forms: contained, core shock, and compound, written for that specific mechanism rather than as generic severity labels.
- The second-level page shows the exact Radar material that speaks for the shock and the strongest material that pushes against it through substitution, resilience, diversification, redundancy or policy capacity.
- Realised shocks link into the closest supported variant family when the mechanism can be mapped safely (for example export-control shocks to the materials/chips family).
- Counter-evidence is deliberately not treated as a vote count: the page exposes it so shock reasoning can be challenged instead of merely illustrated.

## 17.20.5 — only Items + New on the Radar
- The Radar count strip now shows only the total number of retained items and the number of New items.
- Removes reader-facing records-checked, runtime, 24-hour-addition and per-strand summary counters from the strip. Strand counts remain where they belong: inside Strand A, B and C.
- Replaces the two addition filters with one pressable `New` filter.
- `New` follows the latest productive scan (the most recent run that actually inserted A, B or C material), so a zero-yield rotation does not erase the latest additions from view.
- The scanner records `latest_productive_scan` explicitly, while keeping all normal quality/admission gates unchanged; it never lowers the quality bar just to manufacture a non-zero number.

## 17.20.7 — broader evidence rotation and always-fresh analytical products
- Broadens Strand A discovery across EU institutions, national science bodies, research organisations, journals and working-paper routes, and expands the EU R&I/geopolitics vocabulary without weakening admission gates.
- Broadens Strand B method discovery for horizon scanning, scenario discovery, robust decision-making, stress testing, red teaming, futures literacy, anticipatory governance, text mining and related foresight methods.
- Gives strategic risk, opportunity and external-shock searches a protected lane in every scan; the Matrix, Risks & opportunities, External shocks and Read at least this rebuild from the newly published radar.json.
- Adds four further cross-evidence shock families while preserving dynamically filed realised shocks and the existing direct/reasoned shock logic.
- Adds a compact Shock index at the top of External shocks.
- Makes Read at least this more compact and editorial: exactly eight hierarchy maps remain, but phrases link to the strongest supporting source and each node can jump to matching Radar evidence.
- Uses a fixed four-hour scheduled rotation, with a 24-minute scanner budget inside a 36-minute workflow envelope and a 6-minute publish job.
