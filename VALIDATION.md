# V17.7.5 validation

- Full automated suite: **204 passed**.
- Current bundled state classifier reproduces the six reported empty Frontier cells: Knowledge-C (Borrowed brains), Knowledge-D (Brain drain), Infrastructure-B (Expensive mirror), Infrastructure-D (Cut supply), Conversion-D (Hollowing out) and Rules-C (Rule-taker).
- Stubborn recovery now persists a separate formulation cursor for every empty cell and rotates beyond the first capped query batch across scheduled runs.
- Recovery cursors advance only for requests that actually execute; queued-but-unexecuted formulations remain next in line.
- V17.7.4 state migrates without restarting at formulation 1: the new recovery cursor is seeded from the saved per-cell scholarly cursor.
- Gap-query provenance is carried internally so the strongest real source sentence that states the targeted cell mechanism is retained in the three-sentence evidence summary. No cell claim is synthesized.
- Matrix-depth cursor advancement is execution-aware, and a final matrix diagnostic is computed against the exact published A/C/frontier-evidence corpus.
- Historical matrix-only recovery remains bounded to the configured 12-month horizon, 240-second reserve and 30-query per-run cap.
- The bundled `radar.json` is the supplied `radar (16).json` state: 90 Strand A, 22 Strand B and 11 Strand C items.
