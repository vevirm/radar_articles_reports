# V17.13.6 validation

Bundled data: radar (35).json, last updated 2026-08-28T13:43Z. No new discovery scan was run while packaging.

Reader Matrix after the semantic placement correction:

| Row | A | B | C | D |
|---|---:|---:|---:|---:|
| People & knowledge | 3 | 6 | 1 | 1 |
| Tools & infrastructure | 2 | 1 | 7 | 7 |
| Firms & scale | 6 | 5 | 8 | 2 |
| Rules & coordination | 1 | 7 | 2 | 3 |

Qualifying Matrix findings: 62. Minimum cell: 1. Maximum cell: 8. The previous reader classifier produced a 0-versus-22/23 pile-up because generic evidence could skip the cell semantic contract.

The Quick Matrix still renders every finding accepted by the full Matrix. The scanner coverage bridge uses this same classifier, so rotation targets the corrected sparse cells. Admission rules remain unchanged.

Focused tests: 33 passed (9 matrix-depth tests + 24 matrix/reader regression tests).

Presentation smoke: PASS. Matrix builds 62 qualifying signals; Risks & opportunities builds 12 opportunities / 15 risks. No network discovery or scanner run was performed during packaging.
