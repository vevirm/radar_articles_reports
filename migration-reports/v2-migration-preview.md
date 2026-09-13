# Radar V2 migration preview

This report is non-destructive. It identifies the starting state before authoritative Deep Scan V2 verification.

- Raw records: **675** occurrences / **668** stable record keys.
- Legacy Deep Scan interpretations retained: **300**.
- Authoritative Deep Scan V2 completed: **0**.
- Unique records still needing V2: **668**.
- Current active counts: A **412**, B **133**, C **129**.
- Same-record-key variant groups requiring V2 canonical treatment: **6**.
- High-confidence distinct-key duplicate candidates for inspection: **1**.
- Existing metadata corrections: **1**.

## Safety

No raw record is deleted by this preview. DROP/REVIEW/KEEP decisions enter the active corpus only through explicit sidecar state, normally after validated Deep Scan V2 results.

## Legacy Deep Scan relevance concerns

- `link:https://www.eurekanetwork.org/wp-content/uploads/2026/08/Switzerland-2025-2026-Eureka-Chair-year-in-review.pdf` — Concerns how intergovernmental innovation cooperation outside the EU framework relates to the next EU budget period.
- `link:https://doi.org/10.1007/s11192-026-05690-2` — Relevant to ongoing research assessment reform debates, though the study is not Europe-specific and makes no claim about European systems.
- `link:https://doi.org/10.55186/25876740_2026_69_3_373` — Uses EU bioeconomy policy as a reference model, but the subject is regional policy design outside the EU.
