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

