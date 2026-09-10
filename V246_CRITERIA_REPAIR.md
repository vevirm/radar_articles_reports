# v24.6 criteria repair

This change repairs semantic admission for all three radar strands and makes the 8:1:3 new-item mix a publication invariant. The design rule is: **keywords retrieve; relationships admit**.

## Admission contracts

- **A — European R&I system evidence.** A source may qualify through a direct strategic/geopolitical relationship, or through substantive evidence about a European R&I state variable that materially shapes strategic capacity/position. Recognised state variables include funding/governance, capability/performance, talent/workforce, infrastructure/compute, collaboration/knowledge networks, translation/scale-up, technology position/dependency, research security and standard-setting capacity. Generic `Europe + technology/research` co-occurrence is not enough. The source does not have to use geopolitical vocabulary when it establishes a genuinely strategic internal R&I condition whose geopolitical relevance is structural.
- **B — foresight/futures methods themselves.** A real foresight/futures or forward-looking R&I analytical method must first be independently identified. The publication must then develop, adapt, compare, validate, evaluate, review, critique, systematise, measure, or otherwise study the method/construct itself. Mere application or organisational use is not B. Generic words such as `future research`, bare `scenario(s)`, `framework`, `approach`, and `method` cannot manufacture a B method family. Homonym guards prevent engineering weak-signal detection and health technology assessment from becoming foresight methods. Bare `foresight practice(s)` and unrelated later words such as `role` no longer prove a method study.
- **C — current changes capable of changing A.** Direct European R&I developments may qualify. External developments without direct European scope require a real transboundary/materiality channel, such as controls/supply restrictions, science-funding shocks, research-talent/mobility shocks, international R&I arrangements/restrictions, standards/IP shifts, or frontier-capability discontinuities. Event facts remain source-backed; any Europe-impact bridge is explicitly labelled radar inference. Generic foreign technology investment/company expansion, product PR, archive/index pages and event landing pages are not enough. Actor extraction is metadata, not a hard veto: a concrete current change can qualify even when the actor is not in a hard-coded list.

## Publication balance

After substantive quality gates, new publication is capped at **8 A / 1 B / 3 C**. A short lane remains short; the quota never lowers quality or promotes a failed candidate, and no lane steals another lane's unused slots. C may continue quality-preserving discovery/rescue work toward three, but the final cap is applied only after novelty/deduplication.

Historical retained rows are not deleted merely to satisfy the ratio.

## Regression protection

`tests/test_v246_gold_benchmarks.py` encodes the 12 curator-provided YES/NO examples covering A, B and C. `tests/test_v246_criteria_repair.py` adds adversarial and architectural tests for generic B prose, B homonyms/applications, B method-object grammar, null-timestamp migration safety, A structural state variables, C external materiality, C event-page noise, C actor-list independence, migration cleanup, compact C diagnostics, and hard 8:1:3 publication caps. `tests/test_v246_c_gold_set.py` adds an expanded C boundary set spanning positive policy/capacity/research-security changes and negative product, deal, archive, event and procurement noise.

Validation on the current working tree: **209 passed, 33 skipped, 0 failed**. The v24.6 gold layer now includes an expanded A boundary set as well as the B/C regressions.

## Existing-corpus migration

The quality profiles are bumped to v24.6 so the next scanner run performs an auditable one-time migration. The migration is deliberately asymmetric because the saved evidence quality differs by strand.

On the repository's current `radar.json`, the dry migration preview is:

- before: **A 426 / B 133 / C 15**
- after v24.6 surgical A/B cleanup: **A 426 / B 34 / C 15**
- after v24.6 saved-C revalidation: **A 426 / B 34 / C 4**

Strand B is revalidated once in full on the v24.6 profile bump because the repaired rule changes B's defining invariant: every retained B row must still demonstrate that a foresight/futures method or construct is itself the object of inquiry. The current corpus removes **99 of 133** B rows and retains **34**. Within the known v24.5 flood window (`first_seen >= 2026-09-09T23:26Z`), **94 of 105** rows are removed and **11** survive. Five older/null-timestamp rows are also removed; inspection shows they are the same contamination classes (engineering weak-signal homonyms and application-only foresight/Delphi papers), not genuine method studies.

Historical A is also not globally replayed from abbreviated saved summaries. The repaired A gate applies prospectively; migration removes only high-confidence legacy contamination already covered by the existing surgical cleanup machinery. The curator benchmark negatives are rejected by the semantic gate itself; no new exact-title deny-list was added for them.

Saved C is revalidated under the new state-variable-change contract. The current bundled corpus retains four strong signals (Horizon association, FP10 budget movement, European AI compute-capacity investment, and US restrictions on research collaboration with China). Revalidated-out C rows are moved to the private signal archive with `quality_revalidated_out` rather than destroyed.

The packaged `radar.json` itself is not pre-mutated. The migration logic applies on the next scanner run, so deployment remains auditable and the existing file can be compared before/after.

See `V246_MIGRATION_PREVIEW.md` and `V246_SHADOW_REPLAY.md` for the dry-run details.
