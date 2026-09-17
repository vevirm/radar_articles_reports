# Stage 3 — offline claim backfill plumbing

Stage 3 implements migration step R-101(2) without changing reasoning or the public site.

## What is new

- `scripts/backfill_claims.py`
  - packages already-stored authoritative Deep Scan text for claim extraction;
  - never browses the web;
  - uses the repository's existing 0–100 Stuff merit score;
  - excludes Deep Scan drop/drop_unverifiable/duplicate records;
  - excludes old main-Radar sidecar entries no longer present in `radar_active.json`;
  - validates returned claims against `claims_vocabulary.json` and the claim schema;
  - rejects stale/altered jobs through source, identity and deterministic job hashes;
  - writes accepted claims only into the matching `reader_text.json` record;
  - removes claims if a record is now dropped/duplicate.
- `claim_backfill_inbox/.gitkeep` — safe inbox for returned result files.
- GitHub Actions workflows to prepare and import claim batches from the web UI.
- `tests/test_reasoning_reform_claim_backfill.py` — atomicity, stale-result, merit,
  qualification, drop-removal and offline-package tests.

## Safety boundary

This stage does **not** modify:

- `scripts/scan_radar.py`;
- `scripts/prepare_deep_scan_package.py`;
- `scripts/import_deep_scan_results.py`;
- `scripts/active_corpus.py`;
- legacy high-order/shock reasoning;
- any reader HTML/JS or published product.

The scanner and Deep Scan remain the hard core. Claims are additive stored semantics
and nothing consumes them yet.

## Backfill population

The package builder uses authoritative Deep Scan V2 entries with a stored main
finding and a non-drop decision. For main Radar records, the record must also still
exist in the authoritative active corpus. Historical records use their namespaced
Deep Scan entries. This means old sidecar material cannot silently re-enter current
reasoning after rolling-window retention.
