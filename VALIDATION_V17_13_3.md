# Validation — V17.13.3

## Matrix-balance logic

Bundled Matrix occupancy from the production classifier:

- qualifying Matrix findings: 111
- minimum cell count: 0
- maximum cell count: 18
- median cell count: 6
- moving balance target: 6
- under-covered cells: 5
- current priority cells: knowledge-D, rules-A, knowledge-C, rules-C, infrastructure-A

The target is bounded to 3–10. It therefore reacts to persistent imbalance without trying to force identical cell counts.

## Tests

Focused reader/scanner + Matrix-rotation regression suite:

`74 passed in 11.04s`

Presentation smoke check:

- radar JSON parses: 183 A / 25 B / 13 C
- Matrix builds: 111 qualifying findings
- Risks & opportunities builds: 15 opportunities / 15 risks
- all reader-view JavaScript syntax checks passed

## Packaging note

No network discovery or scanner run was performed. The bundled evidence state is unchanged; V17.13.3 changes how the next and subsequent scans allocate discovery effort.
