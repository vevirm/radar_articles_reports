# V17.6.1 validation

Validated against the uploaded `radar (8).json` state.

- Model: A = EU R&I in geopolitical context; B = newly developed/adapted/extended/refined futures methods reusable for understanding the future of A; C = weak signals that may change how A is interpreted.
- Cleaned bundled corpus: 28 A, 0 B, 5 C (from 90 A, 1 B, 20 C).
- The rejected B record was the sub-Saharan Africa musculoskeletal-injury Delphi application; using Delphi is not itself a futures-method contribution.
- Re-running the current A/B and C revalidation gates on the bundled state removes 0 additional records.
- The complete persisted `scan_state` is preserved from the uploaded state, including all top-level and nested rotation/depth cursors.
- Dedicated B-method rotation remains enabled and advances independently of the main scholarly query rotation; its query bank now targets new/novel/developed/adapted method contributions.
- C can anchor only to Strand A; B cannot fill Frontier matrix cells.

Test results in the packaged repository:

- `PYTHONPATH=. pytest -q`: 146 passed.
- `python -m unittest discover -s tests -p 'test_*.py' -q`: 142 passed.

- V17.6.1 deliberately bumps only the quality/admission profile. `incremental_state_version` and `source_expansion_version` are unchanged, so scan rotation is preserved while the first live run re-audits saved B items under the stricter gate.
