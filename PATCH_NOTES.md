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
