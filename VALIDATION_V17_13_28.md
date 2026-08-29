# Validation — V17.13.28

## Corpus / migration

- `radar.json` parses successfully.
- Packaged counts: **182 A / 24 B / 14 C**.
- Matrix continues to produce **38 qualifying findings** under the V17.13.26 semantic contract.
- V17.13.28 migrated **50** legacy reusable/generic stored claims to source-specific claims where saved evidence supported a concrete proposition.
- The specificity audit removed **4** further high-confidence legacy Strand-A contaminants. See `QUALITY_CLEANUP_V17_13_28.json`.
- No network discovery scan was run while packaging this release.

## Main Radar claim checks

`node scripts/presentation_smoke.js` passes. In addition to the existing page/language checks it now verifies that the main Radar does not emit:

- reusable topic slogans such as “Geopolitical competition is pushing Europe…”;
- the generic “This may affect European access…” weak-signal filler; or
- scanner/review metadata such as “Consult the linked publication” or “Its EU relevance is classified…”.

The main Radar remains policy-technical and may use a longer complete sentence (roughly up to 300 characters) when needed to state actor + mechanism + consequence. Read and Matrix language boundaries are unchanged.

## Matrix

`node scripts/test_matrix_semantic_contract.js` passes **31/31** fixtures. No Matrix thresholds or semantic cell contracts were loosened in V17.13.28.

## Excel technical evidence workbook

`stuff/source_merit_ranking.xlsx` was rebuilt with `artifact_tool` and verified after export.

Sheets:

1. **What sources say** — source-by-source bullet summaries plus the Radar relevance claim.
2. **Ranked sources** — source-merit ranking plus source-summary bullets.
3. **Technical evidence** — full technical audit fields plus bullets and the stored source summary.
4. **Matrix criteria** — 16-cell semantic contract.
5. **Method** — scoring, window, language and evidence notes.

The workbook contains **212 deduplicated publication/report/signal records**. Every row has a populated `What the source says` field. When the saved radar state contains only metadata and no substantive finding, the workbook says so explicitly instead of inventing a conclusion. A workbook formula/error scan found no `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?` or `#N/A` errors.

## Python / generated briefing

- `python -m py_compile scripts/scan_radar.py scripts/manual_ingest.py scripts/build_briefing.py` passes.
- `python scripts/build_briefing.py` rebuilds the topic digest from the packaged state.
- The topic digest retains the shared source layer and does not modify `radar.json`.

## Integrity

Packaged `radar.json` SHA-256: `e70564500ce49c7b32983079caea7e5e27349a5f5b97be575208831962c546f6`.
