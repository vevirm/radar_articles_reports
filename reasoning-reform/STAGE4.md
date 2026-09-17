# Stage 4 — future Deep Scan emits validated claims

This stage completes R-101 step 3 without switching reasoning or reader output.

## What changes

- New Deep Scan V2 packages now include `claims_vocabulary.json` and instruct the browsing verifier to return 1–3 structured claim drafts for KEEP/REVIEW results.
- The Deep Scan importer canonicalises system-owned claim fields (`record_key`, stable `claim_id`, repository merit, `origin=deep_scan`, era and provisional flag) and validates every semantic field against the shared claims vocabulary.
- DROP/DROP_UNVERIFIABLE/DEFER results cannot carry claims.
- Strand B claims are forced to `attributes.world_reasoning=false`.
- The authoritative active corpus carries validated claims as additive fields for later shadow reasoning.
- Old in-flight Deep Scan V2 packages that predate the claim marker remain importable, so the migration does not strand existing worker packages.

## What does not change

- `scripts/scan_radar.py` is unchanged.
- Deep Scan still owns verification/admission; claims do not decide KEEP/REVIEW/DROP.
- Raw `radar.json` evidence remains immutable under Deep Scan import.
- `scripts/high_order_inference.py`, `scripts/shock_inference.py`, trends, priorities and public reader pages are unchanged.
- No live reasoning uses claims yet.

## Acceptance gate

- Focused reasoning-reform safety suite: 94 passed.
- New future-Deep-Scan claim tests cover vocabulary failure, system-owned merit/IDs, DROP claim removal, Strand B isolation, backward compatibility for old packages, and active-corpus claim carriage.
- Protected-core hash baseline was intentionally advanced only for `prepare_deep_scan_package.py`, `import_deep_scan_results.py`, and `active_corpus.py`; scanner and other protected files remain unchanged.
