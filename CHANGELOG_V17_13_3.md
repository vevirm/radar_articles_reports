# Changelog — V17.13.3

## Matrix coverage now changes scan rotation

The scanner no longer treats a fixed count of three as "covered enough" for every Matrix cell.

- The production Matrix classifier measures all 16 cells before each scan.
- The bounded median cell count becomes the moving coverage target: minimum 3, maximum 10.
- Cells below that target receive the reserved Matrix-gap search budget first.
- Empty cells remain the strongest priority, followed by the thinnest non-empty cells.
- Matrix coverage is recomputed during depth waves, so priority can move within the same scan.
- Rich cells still receive ordinary rotation; they simply do not consume the reserved gap budget while thinner cells remain.
- Admission rules are unchanged. Coverage is a discovery-allocation signal, never a reason to admit weak evidence.

On the bundled state, the Matrix has 111 qualifying findings. Cell counts range from 0 to 18 and the median is 6. The first balance targets are therefore knowledge-D, rules-A, knowledge-C, rules-C and infrastructure-A.

No external discovery scan was run while packaging this release.
