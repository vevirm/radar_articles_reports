# Validation — V17.13.1

Validation was run against the packaged repository on 28 August 2026.

## Focused V17.13.1 + regression suite

Command:

```bash
PYTHONPATH=. pytest -q \
  tests/test_v17_13_1_subject_language_easy_view.py \
  tests/test_v17_13_0_feedback_round.py \
  tests/test_v17_13_reader_scanner.py \
  tests/test_v17_12_5_plain_language.py \
  tests/test_v17_12_6_priority_people_rotation.py \
  tests/test_v17_12_7_integrated_researcher_attention.py \
  tests/test_v17_6_4_true_rotation.py \
  tests/test_v17_9_source_aware_matrix.py
```

Result: **53 passed**.

The V17.13.1-specific checks cover:

- generic non-EU technology material does not enter merely because it is strategically interesting;
- a major China/US-style capability shock can enter through the exceptional route only with a same-domain current EU anchor and a specific Europe-impact bridge;
- generic foreign product launches fail that exception;
- a non-English publication with substantive English abstract/summary evidence can pass;
- a foreign-language title with only a tiny English stub fails;
- the easy radar exposes **All record details** and a global **Show all details** control;
- the configuration contains the explicit subject, language-evidence and external-shock contracts.

## Manual-ingest regression

Command:

```bash
PYTHONPATH=. pytest -q tests/test_v17_10_manual_ingest.py
```

Result: **32 passed**.

This verifies that manual/recovery candidates continue to use the scanner admission logic after the EU-context anchor was made available to the external-shock route.

## Presentation / integration smoke

Command:

```bash
node scripts/presentation_smoke.js
```

Result: **PASS**.

Observed smoke outputs:

- `radar.json` parses: **183 A / 25 B / 13 C**;
- Evidence browser: **15 research groups / 13 weak signals**;
- Matrix: **112 qualifying signals**;
- Risks & opportunities: **15 opportunities / 15 risks**;
- JavaScript syntax passes for the main radar, Read page, Briefing, Matrix and Priorities pages.

The smoke script explicitly performs **no network discovery or scanner run**.

## Full historical suite status

A full `PYTHONPATH=. pytest -q` run stops during collection because `tests/test_findings.py` imports a historical `make_finding` helper that is not present in `scripts/scan_radar.py`:

```text
ImportError: cannot import name 'make_finding' from 'scripts.scan_radar'
```

This collection defect predates V17.13.1 and is outside this feedback change. It is recorded rather than masked by inventing an unrelated compatibility shim.

## Release assertions

- Hard evidence window remains **four calendar months**.
- Strand C remains capped at **15%** of public findings.
- EU/European R&I in geopolitical context remains the normal Strand-A subject.
- External non-EU shocks are exceptional and require an explicit, specific Europe-impact bridge backed by a current same-domain EU context anchor.
- English is required for the evidence used to verify a claim, not necessarily for the entire publication.
- No fresh external scan was run as part of V17.13.1 packaging.
