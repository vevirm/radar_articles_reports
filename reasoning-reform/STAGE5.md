# Stage 5 — claim-native shadow foundation

Stage 5 starts R-101 steps 4–5 without switching any live detector.

## What it adds

- a read-only claim-native shadow runner (`scripts/claim_reasoning_shadow.py`);
- R-10 cluster co-occurrence/lift distance table using the canonical distant bonus **1.20**;
- R-09 primary/context enforcement: A/frontier primary; C KEEP action/effect event content primary; C interpretation/review context; historical context; Strand B/world-disabled claims excluded;
- Level 2 corroborated-claim discovery;
- deterministic Level 3 stalled-proposal and goal-without-measure checks;
- Level 4 opposing-movement discovery over structured objects/directions;
- first claim-native `dependency_pathway` and `conflicting_criteria` shadow grammars with R-21/R-22-style link strengths, floor, distance bonus and counter penalty;
- a legacy snapshot in the report for operator comparison;
- a manual GitHub Action that produces an artifact only. It does **not** commit or publish anything.

## Deliberate safety gate

No Stage-5 shadow candidate can pass the publication gate. Falsifier execution is not yet attached to a candidate fingerprint in the live scanner, so `publication_gate_passes` is forced false. This prevents accidental use of the shadow as public reasoning before R-36 is implemented.

## Not yet implemented

The remaining A-3 grammars (`latent_channel`, `anchor_demand`, `split_recurrence`, `era_conjunction`, `clock_before_rule`, `practice_before_doctrine`, `success_metric_gap`) are added and calibrated in shadow before any detector switch. Trend hostile-witness/action-dedup metadata are used only when explicit, so its Stage-5 pull is diagnostic rather than the future published band.

## Protected core

Stage 5 does not modify `scan_radar.py`, Deep Scan preparation/import, the active-corpus boundary, legacy `high_order_inference.py`, `shock_inference.py`, trends, priorities, or reader pages.
