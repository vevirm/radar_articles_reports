# Validation — V17.13.16

## User JSON integrity

- Supplied `radar (36).json` SHA-256: `687fecf91f33253e6a654f712e39f57aafc55657066637a6d4bc74966c2acae6`.
- Packaged `radar.json` must have the same SHA-256.
- Counts: A=214, B=25, C=13, frontier_evidence=0.

## Fast-reader wording

- `Read at least this`, `Matrix · short`, and `Risks & opportunities` use direct plain-language wording rather than contextual glossary annotations.
- Full source titles and evidence remain unchanged.
- Shared display helper covers the existing 50-term glossary vocabulary plus recurring reader jargon such as interoperability, procurement, fragmentation, resilience and competitiveness.

## Scan cadence

- Scheduled workflow cron is `17 */6 * * *` (every 6 hours).
- Push-triggered and manual scans remain available.

## Presentation smoke

Run `node scripts/presentation_smoke.js`. No network discovery is required for this check.
