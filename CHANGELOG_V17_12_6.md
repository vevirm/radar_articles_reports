# Changelog V17.12.6 — recurring priority-people attention

## What changed

- Added `priority_people.json` with 137 curated people, preserving the supplied field, affiliation, and topic hints.
- Added an additive recurring named-person lane to `scripts/scan_radar.py`.
- The lane selects 16 people per scan using category round-robin rather than scanning the file top-to-bottom by field.
- OpenAlex discovery resolves exact author identity first and then requests works by author ID.
- Crossref discovery uses its author query field and verifies an exact normalized author-name match before classification.
- Priority records still use the normal `candidate_from_openalex()` / `candidate_from_crossref()` admission paths. The watch list never bypasses EU R&I × geopolitics aboutness or evidence rules.
- Added a bounded missing-abstract recovery allowance for otherwise promising exact-author records.
- If both exact-author sources produce no record for a selected person, the scanner creates a bounded context query from affiliation + expertise + field. This may surface relevant work by other researchers and therefore prevents the watch list from becoming a whitelist.
- Added separate persisted state: `priority_people_cursor`, `priority_people_completed_cycles`, and `priority_people_openalex_author_ids`.
- Added scan-result/stat reporting for planned/executed people, exact-author hits, context fallbacks, and completed cycles.
- Corrected stale pause/manual-only documentation so it matches the actual scheduled workflow.

## What did not change

- Existing topic, source, institution, journal, method, Frontier-gap, historical-exploration, and weak-signal rotations remain active and keep their own cursors.
- Strand A/B admission standards are unchanged.
- Reader-first language behavior from V17.12.5 remains unchanged.
- Original bibliographic/source detail remains untouched.
