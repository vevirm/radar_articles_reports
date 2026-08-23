# V17.6.0 validation

Validated against the uploaded `radar (8).json` state.

- Model: A = EU R&I in geopolitical context; B = methods suitable to understand the future of A; C = weak signals that may change how A is interpreted.
- Cleaned bundled corpus: 28 A, 0 B, 5 C (from 90 A, 1 B, 20 C).
- The rejected B record was the sub-Saharan Africa musculoskeletal-injury Delphi application; using Delphi is not itself a futures-method contribution.
- Re-running the current A/B and C revalidation gates on the bundled state removes 0 additional records.
- The complete persisted `scan_state` is preserved from the uploaded state, including all top-level and nested rotation/depth cursors.
- Dedicated B-method rotation remains enabled and advances independently of the main scholarly query rotation.
- C can anchor only to Strand A; B cannot fill Frontier matrix cells.

Test results in the packaged repository:

- `python -m pytest -q`: 143 passed.
- `python -m unittest discover -s tests -v`: 139 passed.
