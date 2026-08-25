# V17.10.2 changelog

- Added manual candidate ingestion for DOCX, PDF, CSV, JSON, YAML/YML, TXT and Markdown.
- Added conservative DOI/URL/title deduplication, source retrieval, evidence-status handling and same-gate admission.
- Added automated-vs-manual comparison, recall diagnostics and bounded exact-URL scanner recovery.
- Added `automated` / `manual` / `both` provenance and UI display.
- Preserved source-aware full-text/abstract/metadata aboutness and contextual bare-`EU` handling.
- Kept `quadrant_claimed` and `quadrant_implied` separate in matrix classification/display.
- Added high-quality institutional source/query coverage for FP10, technological sovereignty, compute and research-career recall without lowering the substantive gate.
- Updated tests for parsing, dedup/provenance, defer semantics, secondary/forthcoming safety, recovery bounds and claimed-vs-implied matrix behavior.
- Ingested the supplied manual list in comparison/diagnostic mode against the supplied `radar (21).json`; no live scan timestamp was fabricated.

- Added numbered Sovereignty Frontier supplement parsing, including curator-cell hints and weak-signal records.
- Added `--links-validated` to record user-tested URL reachability without treating it as evidence verification.
- Fixed structured CSV/JSON/YAML ISO-date precision so verified manual records are not spuriously deferred.
- Ingested the supplied additions document into the saved state without changing the live-scan timestamp.
