# Trend inference weighting repair

This repair changes only the reasoning/weighting layer. It does not alter Scanner admission, Deep Scan authority, raw evidence collections, Reader Language, or the page layout.

## Meaning of the 0–100 balance

The trend/counter-trend number answers: **given the currently available evidence, how much stronger is the case for movement in one direction than movement in the opposite direction?** It is not a probability and it is not a count of articles.

## Rules added

- Multiple reports of one real-world development are clustered into one development. Extra independent reporting gives only a small corroboration lift.
- Each development is weighted by source merit, whether it is an action/effect/diagnosis/advocacy item, implementation status, recency, geographic scope, and relevance to the exact object being scored.
- EU-wide evidence weighs more strongly in a Europe-wide trend than a single member-state example. National evidence remains a valid futures signal, but does not silently stand for Europe as a whole.
- Additional developments have diminishing marginal pull. Several weak signals therefore do not automatically beat one strong opposing development.
- Trend and counter-trend remain opposite pulls on the same controlled object. Ambiguous records that support both sides do not vote twice.
- One evidence item may inform more than one candidate, but it cannot be the primary anchor of multiple published trend cards. Reserve candidates are used instead, preserving page breadth when alternatives exist.
- The reader-safe 15–85 band remains in place to avoid presenting false certainty. The underlying unbanded strength ratio is retained for audit.

## Safety

The one-time workflow snapshots all evidence collections before recomputation and fails closed if any evidence changes, if the claim-native backend drops out, if the Trends page loses pairs, if old count-oriented scoring survives, or if the same primary evidence anchor is reused across published trend cards.
