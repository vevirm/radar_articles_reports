# V17.7.4 validation

- Full automated suite: **198 passed**.
- Current bundled state classifier: exactly five empty Frontier cells — Knowledge-C, Knowledge-D, Infrastructure-D, Conversion-D and Rules-C.
- Dynamic matrix reallocation is enabled after every depth wave.
- Stubborn-cell recovery is enabled with a 12-month matrix-only evidence horizon, a bounded 240-second reserve and a maximum 30 recovery queries.
- `frontier_evidence` is consumed by the Frontier classifier/page but is separate from the ordinary Strand-A corpus.
- Knowledge-D contains dedicated Choose Europe / brain-drain / research-talent formulations and targeted institutional sources.
- Direct institutional pages can feed the Strand-C candidate lane, while ordinary C anchoring and quality gates remain mandatory.
- A/B recall profile remains V17.7.2; no general A/B reset is triggered.
- Bundled `radar.json` is byte-for-byte identical to the supplied `radar (15).json`.
