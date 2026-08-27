# Changelog — V17.12.5

## Reader-first language everywhere

- Added one shared plain-language claim layer for the Main radar, Matrix, Risks & opportunities, Read page live layer, and secondary evidence browser.
- Implemented the four requested regression examples, including the Ireland/China, EU chip-export, Intermarium/Polish-academia, and dual-use/supply-chain rewrites.
- Removed common false list markers and academic/report scaffolding from reader-facing claims, while keeping the source proposition traceable.
- Made the Matrix reuse the same simple claim layer rather than exposing a separate abstract-derived phrase.
- Added a scanner write boundary (`normalize_reader_claims`) across `strand_a`, `strand_b`, `strand_c`, and `frontier_evidence` so newly inserted records inherit the rule automatically.
- Routed manual candidate ingestion and reviewed `display_claim` values through the same plain-language function.
- Kept original titles, abstracts/summaries, authors, sources, dates, links, types, relevance notes and other bibliographic/source detail untouched below the prominent claim.
- Migrated the bundled corpus's reader-facing claim fields without changing source-detail fields.
- Added V17.12.5 regression tests for display reuse, scanner insertion, and source-detail preservation.
