# V17.6.4 validation — true rotation

This release repairs the practical rotation problem: after backfill, the normal scholarly lane was limited to the recent overlap window, so deeper pages were still only deeper pages inside that recent window.

V17.6.4 keeps the fresh lane and adds an independent persisted historical exploration lane. Every run rotates to a different diversified query slice and searches from the retained corpus floor. Historical depth uses separate `explore::` page cursors. If the first rotated slice yields zero admissible A/B items and runtime remains, a second smaller next-slice rescue is attempted.

Validation performed in the packaged repository:

- `pytest`: 158 passed.
- workflow-style `python -m unittest discover -s tests -v`: 154 passed.
- Existing source cursors in the bundled state remain unchanged: OpenAlex 60; Crossref broad 0; Crossref priority 360; institutions 18; Frontier gap 15; Strand-B method 18.
- New exploration cursors are additive and are initialized from the live state without changing those existing cursors.
- Consecutive exploration plans use non-overlapping OpenAlex and Crossref topic slices.
- Exploration requests use the full retained corpus floor and separate historical depth keys.
- Quiet-scan rescue advances to the next slice instead of repeating the first one.

The scanner cannot truthfully guarantee that every run contains a new admissible publication; the external literature may not contain one. It does guarantee that a quiet run has moved to a different persisted topic/depth slice, and `scan_results.rotation_note` / `scan_results.historical_exploration` record what was searched.
