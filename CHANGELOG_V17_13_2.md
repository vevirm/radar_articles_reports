# V17.13.2 — explicit subjects, 120-character reader points, 100-file package

## Reader-point rule

- Reader-facing findings now use one complete sentence of at most 120 characters.
- A point cannot begin with vague anaphora such as “this”, “these”, “it”, “they”, “the study” or “the developments”.
- Context-dependent openers such as “based on”, “with”, “because” and “while” are also rejected at the claim boundary.
- Long source prose is reduced only at a sentence or clause boundary. The system does not hard-cut a claim or add an ellipsis.
- The same rule is applied by the scanner write boundary and the main radar, Read page, Briefing, Matrix and Priorities views.

## Existing corpus normalization

- Existing `core_message` fields were rewritten through the shared reader-point layer.
- Strand C `what` and `why_it_matters` fields were normalized through the same rule.
- Hand-written fallbacks were added where a title or stored sentence could not safely stand alone.
- The user example beginning “These developments…” now becomes: “The EU AI Act creates a risk-based governance framework for AI systems.”
- Bibliographic titles, source excerpts and full evidence fields remain available in expanded detail and are not misrepresented as concise claims.

## Scope unchanged

- EU/European R&I in geopolitical context remains the normal subject gate.
- The narrow major-external-shock exception from V17.13.1 remains unchanged.
- English evidence rules remain unchanged.
- The public evidence window remains four calendar months.
- No fresh external scan was run for this packaging change.

## Package budget

- The release package is capped at 100 files.
- Historical V17.12.5 and V17.12.6 changelog/validation documents were removed from the distributable package to stay within the cap.
- Scanner code, tests, current documentation, current data and active pages remain included.

## Reader-shell patch
- Reader claims cannot begin with conjunctions, pronouns, generic document labels, or open questions.
- Generic prompts such as “broader implications” are not valid findings.
- Added `literature/`: alphabetical name · year · title · publication/channel list, deduplicated by source.
- Simplified the shared page shell and made related views explicit: Radar main ↔ browser; Matrix short ↔ full.
- Kept the Read-at-least-this issue maps in main issue → branches → subissues form.
- Package remains capped at 100 regular files.
