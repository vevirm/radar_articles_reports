# Radar reasoning reform — engineering guardrails

These rules are migration invariants. A reasoning-v2 change is not allowed to relax them.

1. **Scanner remains the discovery/admission core.** `scripts/scan_radar.py` continues to discover and admit A/B/C/frontier evidence under the existing scanner rules. Reasoning v2 does not decide whether a record is admitted.
2. **Deep Scan remains authoritative.** KEEP/REVIEW/DROP/manual-verification decisions and authoritative semantic corrections remain upstream of reasoning. Reasoning consumes the active corpus after those decisions have been applied.
3. **Raw evidence is not rewritten by reasoning.** `radar.json` evidence collections and the historical scanner archive are not mutated to make a reasoning finding work. Reasoning outputs are derived state.
4. **Claims are additive downstream semantics.** Claims describe already-admitted/verified evidence. They do not create evidence and do not bypass source/admission gates.
5. **No reasoning-v2 code enters the scanner during the shadow phase.** Claim backfill, claim validation, graph discovery, grammars, scoring, wow, falsifiers and shelf selection live in separate downstream modules until shadow acceptance is complete.
6. **Legacy reader output stays authoritative during shadow mode.** V2 writes separate shadow state. No reader page consumes it until an explicit cut-over step.
7. **Failure is fail-safe.** A v2 exception may prevent a v2 shadow artifact from being updated; it must not prevent scanning, Deep Scan package/import, active-corpus rebuild, or legacy reader output.
8. **Every published v2 support reference must resolve to active evidence.** Deep Scan DROP/reinterpretation must remove affected v2 findings from the visible shelf on the same rebuild.
9. **Rollback is configuration/state selection, not evidence rollback.** Switching the reader back to legacy reasoning must not restore dropped evidence or an old corpus.
10. **One stage, one acceptance gate.** Do not combine schema, migration, reasoning switch and reader changes in one patch.

## Hard-core boundary

The protected pipeline is:

`scanner -> Deep Scan -> active corpus -> claims -> reasoning -> reader`

The arrow never runs backwards. Claims/reasoning may request future searches through an explicit feedback queue, but those results must still pass the normal scanner and Deep Scan path before they can become evidence.
