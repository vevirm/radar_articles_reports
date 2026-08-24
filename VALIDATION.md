# V17.8.3 validation

Regression checks cover the V17.8.2 balanced frontier plus the English-only and display repairs.

Key assertions:

- Explicit French/German/Dutch/Ukrainian material is rejected.
- An English title cannot rescue a non-English body, and an English body cannot rescue a non-English title.
- Saved A/B/C records are subject to the same final English publication gate.
- `core_message` is concrete and no longer than 80 characters.
- Main radar and matrix render `This says that …` before bibliography.
- Existing precision, rotation, recovery and frontier behavior remains intact.
- Full regression suite: 215 tests pass.
