# V17.7.3 validation

- 180 unit tests pass.
- `scripts/scan_radar.py` passes Python bytecode compilation.
- The bundled `radar.json` is byte-for-byte identical to the supplied `radar (14).json` (SHA-256 `8104db9095c883dbd9a2990bd2de57a3bc48c7085063ae83d241dc36282f8043`).
- Supplied state: 66 A / 19 B / 5 C; the latest run added 8 A / 2 B / 0 C and finished in 415.7 seconds.
- Supplied Frontier state has 7/16 empty cells. Under V17.7.3, the first 28 scholarly gap slots are exclusively assigned to those seven zero cells (four distinct formulations each).
- The full zero-cell depth bank contains 42 scholarly formulations for the supplied state before the deepening phase falls back to near-empty cells.
- Gap news capacity increases 8 → 14; gap scholarly capacity 14 → 28; gap-specialist institutional sources 6 → 10.
- OpenAlex/Crossref broad per-scan caps increase to 52 so matrix priority does not merely displace all other discovery by an artificial low cap.
- The hard scan budget remains 1200 seconds and the GitHub Actions job remains 30 minutes. A 60-second scanner finalisation reserve prevents a deepening wave from overrunning JSON generation/commit preparation.
- New C tests verify that a strategic EU R&I capacity/investment change can qualify without pilot/draft wording, while a generic consumer AI launch remains excluded.
- External current developments can enter the C prefilter when materially relevant, but `anchor_news()` still rejects them if no Strand-A publication/theme supports the relationship.
- V17.7.2 A/B recall profile is unchanged; V17.7.3 changes only allocation behavior and C discovery semantics. Existing A/B/C items are preserved.
