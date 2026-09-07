# Reader design contract — v22

This repository keeps the research/scanner machinery and replaces the reader-facing hierarchy.

## What must stay true

- `radar.json`, `historical/historical.json`, scanner scripts, admission logic and GitHub Actions remain data/automation concerns, not presentation concerns.
- Existing public routes remain valid: `/radar/`, `/read/`, `/frontier/quick/`, `/trends/`, `/phenomena/`, `/priorities/`, `/shocks/`, `/historical/`, `/literature/`, `/glossary/`, `/stuff/`.
- Radar query links keep using `?q=` so the homepage topic map can open a pre-filtered Radar.
- Existing page-specific JavaScript continues to generate the evidence, Matrix, trends, phenomena, priorities and shocks.

## Reader hierarchy

Every main inner page uses the same black header, red rule, page name, one-sentence purpose and full navigation grid. `Read at least this` is always first and always red.

The homepage is intentionally different: it occupies one viewport and contains the project name, live evidence/source count, the complete menu and the live topic map.

## Topic map rules

- Vocabulary is handwritten in `topic_vocabulary.json`.
- Reader labels are plain language; matching patterns stay hidden.
- Matches inspect evidence text, not source names.
- A topic appears only when at least two different sources match.
- Topic size is based on number of different sources, not number of records.
- A moving topic needs at least five matching sources and more than half of those sources to have a matching item in the latest 90 days.
- At most six moving topics are red.
- Wide screens show up to the full active set; smaller screens progressively show fewer, never smaller text just to squeeze in another topic.
- Omitted topics remain available in the `See all … topics` dialog.
- Every topic links to `/radar/?q=...`.

## Type scale

Five roles only:

1. page name
2. section heading / navigation block
3. claim
4. reading text
5. labels / dates / counts

Step 5 never goes below 14px. Mobile reduces the large roles but keeps reading text readable.

## Mobile rules

- Navigation wraps as a grid; it never becomes a hidden horizontal strip.
- Matrix column headers collapse into labels repeated above each cell.
- Long pages receive a `Top` control; pages with a filter toolbar also receive a `Filters` control.
- Publication cards and technical material may wrap but must not force the whole page wider than the viewport.

## Colour

Black, white and `#c40018` red. Opacity of black/white is allowed for hierarchy. No fourth semantic colour.
