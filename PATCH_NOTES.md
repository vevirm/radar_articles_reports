# Radar v17.17.0 — relational weak signals + upload-ready full repository

## What this changes

This release keeps the strict A/B admission rules and the v17.16.0 high-yield retrieval repair, but corrects the definition of Strand C:

> A weak signal is any current fact, evidence or development that can put a substantive Strand-A issue in a new light. The topic itself does not have to be new.

Prior coverage is therefore not a reason to reject a C item. A C item is collapsed only when it is substantially the same event, claim and implication as an existing signal.

## Curator phrase workbook integrated

The supplied `eu_ri_radar_phrases_by_strand.xlsx` is included under `stuff/` and exported to `radar_phrase_rules.json` for the scanner.

- Strand A phrases support conservative topic linkage/discovery. They do not bypass the existing substantive A gate.
- Strand B phrases remain method-oriented and separate from A.
- Strand C phrases are **retrieval and re-ranking aids only**. A phrase such as `RISC-V`, `neuromorphic`, `biomanufacturing`, `open-weight model`, `quantum error correction` or `photonic interconnect` can make the scanner look at a candidate, but can never admit it to C by itself.
- The workbook's opposition/guard information is preserved in the JSON ontology for auditability.

## New Strand-C relationship rule

A candidate still has to be factual, strategic R&I material and must anchor to a concrete Strand-A publication. The scanner now records ways in which the new item changes the A picture, including:

- new evidence;
- new actor move;
- new magnitude;
- new mechanism;
- new timing;
- new direction; and
- new consequence.

A story about a familiar topic is therefore eligible when its point is materially different. For example, an existing A theme about an EU AI-compute gap does not make later evidence about electricity constraints, a new investment scale, a change in access rules, or a different actor move a duplicate.

## Duplicate handling repaired

Earlier C deduplication could collapse different stories simply because their headlines shared the same topic vocabulary. v17.17.0 is deliberately more conservative:

- exact same URL collapses;
- near-identical syndicated coverage collapses;
- same broad topic with a different substantive point does **not** collapse.

## Discovery additions

Distinctive C-ontology terms now contribute a small number of guarded Google News retrieval queries. This is a discovery mechanism only; the ordinary source, factual-news, strategic-R&I and Strand-A relationship gates still apply.

## Historical radar consistency fix

v17.16.0 changed historical discovery to target roughly 8 new strict items instead of burning a fixed 10-minute continuation window, but the GitHub Actions workflow still exported `HISTORICAL_MIN_RUNTIME_SECONDS=600`. That old override is removed here (`0`). The historical scanner is now actually target-driven in GitHub Actions as well as in its config/code.

## Yield targets remain search-depth targets, not quotas

- Main A/B radar: search toward **20** genuinely new high-quality items.
- Historical radar: search toward **8** genuinely new high-quality items.
- Strand C: no padding; retain up to the configured cap only when the relationship to A passes.

Nothing in this release instructs the scanner to manufacture low-quality results to hit a number.

## Validation

- Main scanner: 24 regression tests pass.
- Historical scanner: 20 regression tests pass.
- Python scanner files compile successfully.
