# V17.13.0 validation

## Focused V17.13 + regression command

```bash
PYTHONPATH=. python -m pytest -q \
  tests/test_v17_13_0_feedback_round.py \
  tests/test_v17_13_reader_scanner.py \
  tests/test_v17_12_5_plain_language.py \
  tests/test_v17_12_6_priority_people_rotation.py \
  tests/test_v17_12_7_integrated_researcher_attention.py \
  tests/test_v17_6_4_true_rotation.py \
  tests/test_v17_9_source_aware_matrix.py
```

Final focused result: **46 passed**.

The V17.13 tests cover: implied strategic context without the word `geopolitics`; rejection of a single vague competitiveness cue; the 15% Strand-C ceiling; search context derived from existing findings; researcher names as fallback attention rather than a separate admission path; the requested plain-language examples; the eight-issue hierarchy; the quick Matrix; and current-state profile/date constraints.

## Static/runtime checks

- `python -m py_compile scripts/scan_radar.py` passes.
- Node syntax checks pass for `briefing/insights.js`, `frontier/frontier.js`, `priorities/priorities.js` and the inline scripts on the main reader pages.
- The shared Matrix classifier builds successfully from the bundled radar: **112 qualifying findings across 14 of 16 cells**.
- Bundled public date floor: **2026-04-28**.
- Bundled counts after pruning: **183 A**, **25 B**, **13 C**, **0 historical frontier_evidence rows**.
- C share is **5.9%** of A+B+C, below the 15% ceiling.
- Matrix classification from current four-month evidence yields **112 qualifying placements** across 14 currently populated cells; two People & knowledge cells remain empty and are left as evidence gaps.
- No external discovery scan was run while building this package. `last_updated` remains **2026-08-28T06:44Z**, the timestamp of the supplied scanner state.

## Repository-wide legacy note

The repository contains older tests and historical reports for previous releases. Those are intentionally retained. A previously documented collection issue in `tests/test_findings.py` concerns removed legacy scanner helpers (`make_finding`, `backfill_finding`, `build_findings_data`) and predates V17.13; it is not used as the release acceptance test.

## Broad legacy V17 suite

Final packaging run:

```bash
PYTHONPATH=. python -m pytest -q tests/test_v17_*.py
```

Result: **224 passed, 14 failed, 4 subtests passed**.

The remaining failures are historical-contract assertions rather than V17.13 release regressions. They expect one or more of: the pre-V17.13 static `Read at least this` briefing; a manual-only scanner instead of the active 12-hour schedule; old Matrix wording/semantics; the older keyless-workflow contract; the V17.7.2 exact recall-profile string and `external-position-evidence` route name; a 12-month stubborn-cell recovery window (which now intentionally conflicts with the user's hard four-month rule); or the older bundled A count of 153. Those tests are retained as historical documentation and were not rewritten to disguise the deliberate V17.13 behavior change.
