# Scanner architecture

## Why semantic web research

The radar criteria require judgments such as whether R&I policy and geopolitics are both central, whether foresight work is actually methodology-first, whether EU relevance is explicit, and whether a news item is a real empirical signal relative to caught literature. Keyword scores cannot enforce those distinctions reliably.

The scanner therefore uses three focused OpenAI Responses API calls with the built-in `web_search` tool.

## Strand A pass

Searches from 2026-04-01 through the scan date. The model must inspect actual source pages, verify publication dates, search the requested source tiers, and provide explicit evidence for R&I policy, geopolitics, EU relevance, publication date, and substantive length/type. Pages such as calls, facilities, events and funding opportunities are explicitly excluded.

## Strand B pass

Runs independently so methodology work is not crowded out by the larger Strand A literature. The model must provide concrete methodology evidence: design, evaluation, limits, bias, institutional design, scenario method, horizon scanning, anticipatory governance or integration with strategic intelligence/risk assessment. Pure trend/scenario outputs are rejected.

## Mechanical validation

The Python layer then checks date floor, URL validity, source tier/domain rules, evidence presence, Tier-3 direct EU relevance, summary format, duplicates, and ranking. Preprint/published-version preference is handled during deduplication.

## Strand C pass

Only after A/B are available, the scanner supplies caught publications and recurring themes as explicit anchor IDs. Web search is restricted to the news whitelist and the current scan window. Every signal must select a valid anchor and state a concrete confirm/contradict/accelerate/instantiate relationship.

## Output

A/B are capped at 15 per strand and sorted direct EU relevance first, then source tier, then date descending. C is capped at 5 and sorted by anchor-connection strength. Shortfalls are displayed rather than padded.
