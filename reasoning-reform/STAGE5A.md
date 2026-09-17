# Stage 5A — exact-object shadow guard

This patch tightens the claim-native shadow after the first live shadow artifact exposed over-joining.

It does not change the scanner, Deep Scan decisions, active corpus, legacy reasoning, reader output, or publication selection.

Changes:
- R-31 discovery edges now require exact `object` / `secondary_objects` overlap. Cluster membership is used for distance only, never as a graph edge.
- dependency_pathway coupling claims must themselves contain both a capability-side object and a distinct dependency-side object.
- propagation/exposure/trigger roles bind to the exact dependency object.
- risk pathways respect the two-hop ceiling; shock pathways the three-hop ceiling.
- load-bearing roles use distinct claim IDs and retain the two-roles-per-record guard.
- conflicting_criteria treats a criterion as an action, or a diagnosis of a rule that is adopted/in-force/operating; generic delivered diagnoses no longer masquerade as criteria.
- arbitration-gap and divergence roles use distinct claims.

The publication gate remains locked. This is still shadow-only.
