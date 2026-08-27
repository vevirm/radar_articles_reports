# Validation V17.12.7

## Integrated researcher attention

Command:

```bash
PYTHONPATH=. python -m pytest -q tests/test_v17_12_6_priority_people_rotation.py tests/test_v17_12_7_integrated_researcher_attention.py tests/test_v17_12_5_plain_language.py tests/test_v17_6_4_true_rotation.py
```

Result: **22 passed**.

The regression checks confirm that:

- the 137-name backend input still rotates with field diversity;
- ordinary OpenAlex/Crossref/institution rotation state is not reset;
- watched researchers still receive exact-author attention plus bounded affiliation/topic fallback;
- admitted records expose no `priority_watch_*`, `priority_context_fallback`, or private `_priority_*` fields;
- no HTML or JavaScript page references the researcher watch input;
- the global reader-first wording rule remains intact.

## Wider suite

Command:

```bash
PYTHONPATH=. python -m pytest -q --ignore=tests/test_findings.py
```

Result: **271 passed, 10 failed, 4 subtests passed**. The ten failures are the same older expectation mismatches already documented in V17.12.6 (legacy navigation/version strings, an old manual-only/zero-secret workflow expectation, older bundled corpus counts, and similar historical assumptions). `tests/test_findings.py` remains the pre-existing collection blocker because it imports scanner functions no longer exposed by the current implementation.

## Packaging

The V17.12.7 repository remains below GitHub's 100-file web-upload limit.
