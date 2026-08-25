# V17.9.0 — source-aware aboutness + evidence-led matrix

## 1. Claim rendering

The earlier UI hard-coded `This says that` before every concise point and tests enforced that behavior. V17.9.0 removes the wrapper. The prominent line is now the actual source-backed claim; bibliography/source metadata carries attribution.

## 2. Scan starvation and misleading diagnostics

The old pass-1 path applied admission logic without distinguishing full documents from abstract/metadata records and could classify an unavailable-text case as a failed scope case. It also discarded the evaluated EU relevance on a failed A gate, causing rejection diagnostics to over-report `no direct EU`.

V17.9.0 adds source-length-aware aboutness modes and explicit failure reasons. Metadata-only records defer; abstracts are evaluated within the available abstract; full text can use recurrence/spread checks.

## 3. Ambiguous `EU`

Bare `EU` is no longer accepted blindly. Explicit non-European definitions such as `environmental uncertainty (EU)` block the acronym from establishing European Union relevance.

## 4. Matrix sparsity

The previous Frontier classifier relied too heavily on a compressed display point and then reapplied movement/materiality/direction keyword gates. V17.9.0 carries the source-backed evidence into row and direction classification. For vetted core evidence, source evidence determines the matrix rubric; weak signals retain the stricter event/mechanism test.

The supplied latest state moves from a sparse matrix to 16/16 populated cells with 69 qualifying items, without imposing quotas or equal cell counts.
