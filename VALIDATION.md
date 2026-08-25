# V17.10.2 validation

Validated against the supplied `radar (21).json`, the supplied curated DOCX, and the repository configuration.

- Manual parser covers DOCX/PDF/CSV/JSON/YAML/YML/TXT/Markdown paths.
- Original manual list: 53 parsed records = 38 current candidates, 6 forthcoming/unpublished, 9 context-only; 1 existing corpus match, 1 exact URL previously seen but not admitted, 36 absent among current candidates.
- Additions supplement: 31 parsed records = 27 current candidates and 4 context-only; 24 substantive records and 7 weak signals overall. Across all 31, 1 context item matched the corpus, 1 exact URL was previously seen but not admitted, and 29 were not found in the saved ledger.
- All 31 supplement URLs are stored as user-validated/reachable; that status never bypasses source-text, date, primary-source, or substantive-gate checks.
- Existing corpus matches deduplicate and become `both` provenance.
- Metadata-only manual candidates defer; they are not called irrelevant and do not enter the matrix.
- Secondary references, forthcoming/unpublished records and context-only records cannot auto-admit.
- Verified primary manual sources use the same substantive `gate_scope` as normal candidates.
- Exact-URL recovery is bounded and does not bypass the substantive gate.
- Manual ingest preserves `last_updated`, scan results, cursors and scan-cycle history.
- Bare `EU` remains contextual rather than an unconditional European Union anchor.
- Abstract-only and full-text source-aware aboutness behavior remains covered by regression tests.
- `quadrant_claimed` and `quadrant_implied` remain separate; implied evidence controls matrix placement when present.
- Prominent claims remain informative source claims without mechanical `This says that` / `It says` prefixes.
- Full automated suite: **233 tests passed** (`python -m pytest -q`).

Packaging-time manual ingestion was run with `--no-fetch` because this execution container did not provide working outbound DNS. Therefore no unmatched item was falsely upgraded to verified, no live scan was claimed, and 48 substantive exact URLs plus 4 weak-signal URLs remain in bounded recovery queues for a later network-enabled scanner run.
