# Validation V17.12.6 — priority-people rotation

Validation targets the new recurring priority-watch lane plus regression-sensitive existing rotation and reader-first behavior.

## Targeted checks

- curated watch file loads exactly 137 unique people;
- a 16-person scan slice is category-balanced across the supplied fields;
- old scan state gains priority-person state without resetting ordinary cursors;
- fallback queries use affiliation/topic substance rather than only repeating a person's name;
- OpenAlex exact-author work requests use a resolved author ID;
- Crossref uses the author query field and exact normalized author matching;
- zero exact-author hits create a bounded contextual query;
- existing true-rotation and plain-language regression tests still pass.

Run:

```bash
PYTHONPATH=. python -m pytest -q tests/test_v17_12_6_priority_people_rotation.py tests/test_v17_6_4_true_rotation.py tests/test_v17_12_5_plain_language.py
```

Result: **18 passed**.

## Broader repository check

The broader suite was also run with the already-stale `tests/test_findings.py` collection blocker excluded:

```bash
PYTHONPATH=. python -m pytest -q --ignore=tests/test_findings.py
```

Result: **267 passed, 10 failed, 4 subtests passed**. The ten failures are older repository expectation mismatches rather than failures in the new priority-person lane. They concern legacy assumptions such as a manual-only workflow, zero-secret workflow text, older site navigation/version strings, and an older bundled corpus count.

`tests/test_findings.py` remains an older collection blocker because it imports `make_finding`, `backfill_finding`, and `build_findings_data`, which the current scanner no longer exposes. This mismatch predates V17.12.6 and was not altered to make the new feature appear green.

## Packaging check

The lean V17.12.6 repository contains **91 files total**, including the active workflows, scanner, data, site, priority-person profile, and tests. It remains below GitHub's 100-file web-upload limit.
