# Changelog V17.12.7 — researcher attention embedded in normal discovery

## What changed

- Kept the 137-person curated researcher input as backend discovery guidance.
- Removed public `priority_watch_*` labels from researcher-derived records.
- Removed the separate researcher-attention diagnostics block and counters from published `radar.json`.
- Researcher-derived OpenAlex/Crossref works now rejoin the same ordinary scholarly candidate pools immediately after discovery.
- Affiliation/topic fallback results are also unlabelled and processed exactly like ordinary scholarly discoveries.
- Added a defensive publication-boundary scrub so older `priority_watch_*` fields cannot leak into future public corpus records.
- Updated wording throughout the repository to make clear that this is a process, not a page or separate content stream.

## What did not change

- The curated names still receive extra search attention in rotation.
- The scanner may still discover relevant work by researchers not on the list.
- Normal EU R&I × geopolitics admission, evidence, ranking, matrix placement, and reader-first language rules are unchanged.
- Existing topic, source, institution, journal, method, Frontier-gap, historical-exploration, and weak-signal rotations remain active.
