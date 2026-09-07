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
