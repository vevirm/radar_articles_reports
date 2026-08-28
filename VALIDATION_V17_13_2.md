# Validation — V17.13.2

## Reader-point contract

The focused reader/scanner suite checks that every current A/B/C point is non-empty, complete and at most 120 characters.
It rejects ellipses and vague or dependent sentence openings.
It also checks Strand C `what` and `why_it_matters` points.

The user-supplied AI Act example is covered by a regression test and resolves to an explicit-subject sentence.

## Test results

Focused V17.13.2 and related regression suite:

```text
56 passed
```

The suite covers the V17.13.2 subject/language rules, reader scanner, plain-language layer, researcher rotation and Matrix source handling.

A narrower reader-facing suite also completed with:

```text
30 passed
```

## Presentation smoke test

```text
PASS: radar.json parses (183 A / 25 B / 13 C)
PASS: briefing/insights.js syntax
PASS: frontier/frontier.js syntax
PASS: priorities/priorities.js syntax
PASS: Evidence browser builds 14 research groups
PASS: Evidence browser builds 13 weak signals
PASS: Matrix builds 114 qualifying signals
PASS: Risks & opportunities builds 15 opportunities / 15 risks
PASS: index.html inline JavaScript syntax
PASS: read/index.html inline JavaScript syntax
PASS: briefing/index.html inline JavaScript syntax
PASS: frontier/index.html inline JavaScript syntax
PASS: priorities/index.html inline JavaScript syntax
PASS: frontier claimText() is self-contained
```

The smoke test performs no network discovery and does not advance scanner state.

## Scan-state integrity

No fresh external scan was run while implementing V17.13.2.
The source `last_updated` value remains the scanner timestamp rather than a packaging timestamp.

## Package count

The final ZIP is built from files only, without test caches, bytecode or directory entries.
The package contains exactly 100 files.

## Reader-shell patch validation
- Presentation smoke: PASS.
- 221 reader records checked: no empty claims, leading conjunctions/pronouns, question-only findings, generic “broader implications”, or >120-character points.
- Literature list resolves 217 unique source records from the current radar state.
- Archive regular-file count: 100.
