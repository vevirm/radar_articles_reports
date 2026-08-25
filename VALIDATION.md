# V17.9.0 validation

Validated against the supplied radar state and configuration specification.

- Prominent claim rendering contains the claim itself; it does not add a literal `This says that …` / `It says …` wrapper.
- Abstract-only pass-1 candidates can pass on substantive EU + R&I + geopolitical aboutness without a three-section requirement.
- Metadata-only candidates are marked `insufficient_text` / deferred rather than misreported as irrelevant.
- A paper defining `EU` as `environmental uncertainty` does not satisfy the European Union anchor.
- Admission diagnostics retain the actual rejection reason instead of defaulting to `no direct EU`.
- Core matrix classification reads source-backed summary/relevance evidence rather than only the compressed display point.
- Direction-marker vocabulary supports classification but is not a second pass-1 gate.
- Current bundled state: 69 qualifying matrix evidence items; 16/16 cells populated; distribution is unequal rather than artificially filled.
- Full automated suite: 221 tests passed after code, state, documentation and version cleanup.
