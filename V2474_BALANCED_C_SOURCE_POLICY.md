# v24.7.4 — Balanced Strand C and shared 8:1:3 discovery

This update fixes the over-production of Strand C without returning to the earlier C-starvation failure.

## What changed

- **8:1:3 is treated as a relative discovery balance, never as a publication ceiling.**
  - Main mixed scans use the 8 A : 1 B : 3 C relationship to decide where *extra* search effort goes after every enabled strand has received its baseline search.
  - A valid novel item is not rejected merely because its strand is already above the target share.
  - Strand-specific A/B/C quick scans still focus 100% on the selected strand while using the same underlying strand definitions and admission logic.
- **Historical is explicitly A+B only.**
  - Historical reuses the Main A/B query definitions and shared admission gates.
  - Its A/B query rotation follows the same 8:1 relative order.
  - Historical never searches for, reconstructs, admits, or publishes Strand C.
- **Strand C uses a smaller high-trust public source universe.**
  - Routine C publication is restricted to elite Europe-facing reporting/research-news, EU primary institutions, and authoritative international institutions such as OECD, NATO, ESA, CERN, EPO, EIB, UNESCO and the World Bank.
  - The former 23-source broad national-media C sweep is removed.
  - Think-tank/analysis and broad national media can still contribute elsewhere as context/discovery, but no longer independently become routine public C rows.
- **C event deduplication is stronger.**
  - Same-event cross-publisher financing rewrites are collapsed conservatively using same-day timing plus a distinctive shared actor/name.
  - The strongest allowed source is retained when the cleanup script collapses an existing duplicate cluster.

## Existing-site cleanup already applied

The packaged `radar.json` has already received the narrow v24.7.4 cleanup. You do not need to run a command manually.

- Active Strand C before cleanup: **166**
- Active Strand C after cleanup: **102**
- Archived because the source no longer meets the C public-source policy: **61**
- Archived as duplicate coverage of an already-retained C event: **3**
- Strand A modified: **no**
- Strand B modified: **no**
- Historical evidence modified: **no**

Removed C rows are archived rather than silently deleted, preserving provenance.

## Integrity checks

A downstream retrace/check after the cleanup found:

- stale active evidence references: **0**
- orphan active evidence references: **0**
- downstream objects needing another rebuild: **0**

The regression suite completed all collected tests without a failure marker; the test runner in this environment remained alive after reaching 100%, so the process itself was terminated by the execution timeout after completion.
